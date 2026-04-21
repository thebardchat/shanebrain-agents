"""
OPS AGENT — Infrastructure & Cluster Management

The engineer. Manages Docker, systemd, 4-node Ollama cluster,
disk usage, backups, temperatures, and keeps everything running.
Health checks before any action — no blind restarts.
"""

import subprocess
import logging
import httpx

from shared.base_agent import BaseAgent
from shared.config import (
    WEAVIATE_URL, OLLAMA_URL, OLLAMA_LOCAL, MCP_URL,
    CLUSTER_NODES, RAID_ROOT,
)

logger = logging.getLogger("shanebrain.ops")


class OpsAgent(BaseAgent):
    name = "ops"
    role = "infrastructure"
    description = (
        "Infrastructure and cluster management specialist. Manages Docker containers, "
        "systemd services, 4-node Ollama cluster, disk usage, backups, CPU temps, "
        "and network connectivity. Always health-checks before acting."
    )
    tools = ["Bash", "Read", "Grep", "Glob"]

    def agent_instructions(self) -> str:
        return """
## What You Do
1. **Service Management** — Monitor and restart systemd services and Docker containers
2. **Cluster Operations** — SSH into all 4 nodes, verify Ollama, check connectivity
3. **Disk Monitoring** — RAID health, SD card usage, 8TB external status
4. **Temperature Monitoring** — CPU temps (safe under 176°F), Pico 2 sensors
5. **Backup Verification** — Restic (3AM), Weaviate (3:15AM), auto-ingest (4AM)
6. **Network** — Tailscale VPN, Funnel status, port accessibility

## Services (18 systemd + 7 Docker)
Systemd: ollama, ollama-proxy, shanebrain-discord, shanebrain-social, shanebrain-arcade,
         angel-cloud-gateway, voice-dump, srm-dispatch, mega-dashboard, pico-listener,
         shanebrain-alerter, pulsar-ai, pulsar-sentinel, shanebrain-ready, drive-agent,
         workflow-agent, media-blitz-gallery, mini-shanebrain
Docker: shanebrain-mcp, shanebrain-weaviate, open-webui, portainer, docker-n8n-1,
        docker-redis-1, docker-postgres-1

## Cluster Nodes
- Node1: ssh user@100.x.x.x (priority 1, fastest)
- Pi 5: localhost (priority 2, controller)
- Node2: ssh user@100.x.x.x (priority 3)
- Node3: ssh user@100.x.x.x (priority 4)

## Rules
- ALWAYS health check before restart (check service status, not just restart blindly)
- NEVER modify RAID/mdadm configuration
- NEVER disable pironman5 (CPU fan control)
- Temperatures in Fahrenheit (CPU safe < 176°F)
- Docker containers use 172.17.0.1 to reach Pi services
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "health" in action.lower() or "status" in action.lower():
            return self._full_health_check()
        if "disk" in action.lower():
            return self._disk_status()
        if "temp" in action.lower():
            return self._temperatures()
        if "cluster" in action.lower():
            return self._cluster_status()
        if "docker" in action.lower():
            return self._docker_status()
        return {"message": f"Ops received: {action}"}

    def _full_health_check(self) -> dict:
        """Comprehensive health check of all systems."""
        health = {}

        # Weaviate
        try:
            r = httpx.get(f"{WEAVIATE_URL}/v1/.well-known/ready", timeout=5)
            health["weaviate"] = "ok" if r.status_code == 200 else "down"
        except Exception:
            health["weaviate"] = "unreachable"

        # Ollama (local)
        try:
            r = httpx.get(f"{OLLAMA_LOCAL}/api/tags", timeout=5)
            health["ollama_local"] = "ok" if r.status_code == 200 else "down"
        except Exception:
            health["ollama_local"] = "unreachable"

        # Ollama (cluster proxy)
        try:
            r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            health["ollama_proxy"] = "ok" if r.status_code == 200 else "down"
        except Exception:
            health["ollama_proxy"] = "unreachable"

        # MCP
        try:
            r = httpx.get(f"{MCP_URL}/health", timeout=5)
            health["mcp"] = "ok" if r.status_code == 200 else "down"
        except Exception:
            health["mcp"] = "unreachable"

        # CPU temp
        try:
            result = subprocess.run(
                ["cat", "/sys/class/thermal/thermal_zone0/temp"],
                capture_output=True, text=True, timeout=5,
            )
            temp_c = int(result.stdout.strip()) / 1000
            temp_f = round(temp_c * 9 / 5 + 32, 1)
            health["cpu_temp_f"] = temp_f
            health["cpu_temp_status"] = "ok" if temp_f < 176 else "HOT"
        except Exception:
            health["cpu_temp"] = "unknown"

        # Systemd services (quick check of key ones)
        key_services = ["ollama", "mega-dashboard", "shanebrain-discord", "pulsar-ai"]
        for svc in key_services:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", svc],
                    capture_output=True, text=True, timeout=5,
                )
                health[f"svc_{svc}"] = result.stdout.strip()
            except Exception:
                health[f"svc_{svc}"] = "unknown"

        return health

    def _disk_status(self) -> dict:
        """Check disk usage across all mount points."""
        try:
            result = subprocess.run(
                ["df", "-h", "/", "/mnt/shanebrain-raid"],
                capture_output=True, text=True, timeout=10,
            )
            lines = result.stdout.strip().split("\n")
            return {"disk_usage": lines}
        except Exception as e:
            return {"error": str(e)}

    def _temperatures(self) -> dict:
        """Read CPU and sensor temperatures."""
        temps = {}
        try:
            result = subprocess.run(
                ["cat", "/sys/class/thermal/thermal_zone0/temp"],
                capture_output=True, text=True, timeout=5,
            )
            temp_c = int(result.stdout.strip()) / 1000
            temps["cpu_fahrenheit"] = round(temp_c * 9 / 5 + 32, 1)
        except Exception:
            temps["cpu"] = "unknown"
        return temps

    def _cluster_status(self) -> dict:
        """Check cluster node connectivity."""
        status = {}
        for name, info in CLUSTER_NODES.items():
            if info["ssh"] == "localhost":
                status[name] = {"status": "local", "priority": info["priority"]}
                continue
            try:
                result = subprocess.run(
                    ["ssh", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no",
                     info["ssh"], "echo ok"],
                    capture_output=True, text=True, timeout=8,
                )
                status[name] = {
                    "status": "ok" if "ok" in result.stdout else "unreachable",
                    "priority": info["priority"],
                }
            except Exception:
                status[name] = {"status": "timeout", "priority": info["priority"]}
        return {"cluster": status}

    def _docker_status(self) -> dict:
        """Check Docker container status."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True, text=True, timeout=10,
            )
            containers = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    containers.append({
                        "name": parts[0] if len(parts) > 0 else "",
                        "status": parts[1] if len(parts) > 1 else "",
                        "ports": parts[2] if len(parts) > 2 else "",
                    })
            return {"containers": containers, "count": len(containers)}
        except Exception as e:
            return {"error": str(e)}
