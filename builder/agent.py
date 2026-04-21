"""
BUILDER AGENT — Code & Repository Maintenance

The craftsman. Writes real code, maintains repos, runs tests,
and ensures every line committed is production quality.
No fakes. No placeholders. No half-measures.
"""

import subprocess
import logging
from pathlib import Path

from shared.base_agent import BaseAgent
from shared.config import SHANEBRAIN_ROOT

logger = logging.getLogger("shanebrain.builder")

# All active repos
REPOS = {
    "shanebrain-core": SHANEBRAIN_ROOT,
    "angel-cloud": SHANEBRAIN_ROOT / "angel-cloud-repo",
    "mega-dashboard": Path("/mnt/shanebrain-raid/mega-dashboard"),
    "mcp-server": SHANEBRAIN_ROOT / "mcp-server",
    "pulsar-ai": SHANEBRAIN_ROOT / "pulsar-ai",
    "srm-dispatch": SHANEBRAIN_ROOT / "srm-dispatch",
}

# Files Builder must NEVER touch (creative work)
PROTECTED_PATTERNS = [
    "*/book/*", "*/vignette*", "*/track-*", "*/noir*",
    "*/voice-dump*", "*/audiobook*",
]


class BuilderAgent(BaseAgent):
    name = "builder"
    role = "developer"
    description = (
        "Code generation and repository maintenance specialist. Writes Python, "
        "JavaScript, HTML. Manages git operations, runs tests, checks syntax, "
        "and ensures code quality across all 16+ repos."
    )
    tools = ["Read", "Edit", "Write", "Bash", "Grep", "Glob"]

    def agent_instructions(self) -> str:
        return f"""
## What You Do
1. **Code Writing** — Python, JS, HTML, CSS, Lua — production quality only
2. **Repo Health** — Check all repos for issues, stale branches, failing tests
3. **Syntax Checking** — Validate Python with py_compile, JS with node --check
4. **Git Operations** — Commit, branch, push (NEVER force push, ALWAYS review diff first)
5. **Dependency Audit** — Check for outdated or vulnerable packages

## Active Repos
{chr(10).join(f'- {name}: {path}' for name, path in REPOS.items())}

## Protected Files (NEVER modify)
{chr(10).join(f'- {p}' for p in PROTECTED_PATTERNS)}

## Rules
- Python 3.13 on Pi — no `cgi` module, use `--break-system-packages` for pip
- Always `python -m py_compile` after writing Python files
- Prefer editing existing files over creating new ones
- No placeholder code — if you write it, it must work
- Show diff before any git push
"""

    def _execute(self, action: str, context: dict) -> dict:
        if "health" in action.lower():
            return self._repo_health()
        if "syntax" in action.lower():
            path = context.get("path")
            return self._syntax_check(path)
        return {"message": f"Builder received: {action}"}

    def _repo_health(self) -> dict:
        """Check health of all repos."""
        results = {}
        for name, path in REPOS.items():
            if not path.exists():
                results[name] = {"status": "missing", "path": str(path)}
                continue

            status = {"path": str(path), "status": "ok"}

            # Check git status
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=path, capture_output=True, text=True, timeout=10,
                )
                dirty_count = len([l for l in result.stdout.strip().split("\n") if l])
                status["dirty_files"] = dirty_count
                if dirty_count > 0:
                    status["status"] = "dirty"
            except Exception as e:
                status["git_error"] = str(e)

            # Check for Python syntax errors
            py_files = list(path.rglob("*.py"))
            syntax_errors = []
            for f in py_files[:50]:  # Cap at 50 to avoid long scans
                try:
                    subprocess.run(
                        ["python3", "-m", "py_compile", str(f)],
                        capture_output=True, text=True, timeout=5,
                    )
                except subprocess.CalledProcessError:
                    syntax_errors.append(str(f.relative_to(path)))

            status["python_files"] = len(py_files)
            status["syntax_errors"] = syntax_errors

            results[name] = status

        return {"repos": results}

    def _syntax_check(self, path: str | None) -> dict:
        """Check Python syntax for a file or directory."""
        if not path:
            return {"error": "No path provided"}

        target = Path(path)
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = list(target.rglob("*.py"))
        else:
            return {"error": f"Path not found: {path}"}

        results = {"checked": 0, "passed": 0, "failed": []}
        for f in files:
            results["checked"] += 1
            try:
                subprocess.run(
                    ["python3", "-m", "py_compile", str(f)],
                    capture_output=True, text=True, timeout=5, check=True,
                )
                results["passed"] += 1
            except subprocess.CalledProcessError as e:
                results["failed"].append({"file": str(f), "error": e.stderr})

        return results
