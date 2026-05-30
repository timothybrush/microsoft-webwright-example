import subprocess
import os
import textwrap

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "workspace")


def ensure_workspace():
    os.makedirs(WORKSPACE_DIR, exist_ok=True)


def execute_command(command: str) -> dict:
    """Execute a shell command inside the workspace and return output.

    WebWright paradigm: browser sessions are launched as disposable subprocesses.
    Each call spawns a fresh process — no persistent browser state is kept.
    """
    ensure_workspace()
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"ERROR: Command timed out after 120 seconds: {command}",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"ERROR: Failed to execute command: {e}",
            "returncode": -1,
        }


def write_browser_script(filename: str, url: str, extraction_code: str) -> str:
    """Write a self-contained Playwright script to workspace/ that opens a
    disposable browser session, runs extraction_code, saves output, then exits.

    WebWright paradigm: code composes actions (loops, filtering, comparison)
    rather than long chains of primitive browser actions.
    Returns the filename written.
    """
    ensure_workspace()
    script = textwrap.dedent(f"""
        from playwright.sync_api import sync_playwright
        import json, os

        def run():
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("{url}", wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2000)

                {textwrap.indent(extraction_code.strip(), "                ")}

                browser.close()

        if __name__ == "__main__":
            run()
    """).strip()
    write_workspace_file(filename, script)
    return filename


def take_screenshot(script_name: str, url: str) -> dict:
    """Spawn a disposable browser session that navigates to url, takes a
    screenshot saved to workspace/screenshot_<script_name>.png, then exits.

    WebWright paradigm: disposable browsers — spawn, inspect, discard.
    """
    screenshot_file = f"screenshot_{script_name.replace('.py', '')}.png"
    screenshot_path = os.path.join(WORKSPACE_DIR, screenshot_file).replace("\\", "/")
    script = textwrap.dedent(f"""
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("{url}", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(2000)
            page.screenshot(path=r"{screenshot_path}", full_page=True)
            browser.close()
            print("Screenshot saved: {screenshot_file}")
    """).strip()
    tmp = "_screenshot_runner.py"
    write_workspace_file(tmp, script)
    result = execute_command(f"python {tmp}")
    return result


def read_workspace_file(filename: str) -> str:
    """Read a file from the workspace directory."""
    path = os.path.join(WORKSPACE_DIR, filename)
    if not os.path.exists(path):
        return f"[File not found: {filename}]"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_workspace_file(filename: str, content: str):
    """Write content to a file in the workspace directory.

    WebWright paradigm: artifacts survive — scripts, logs, and outputs
    persist in the local workspace after the browser session is discarded.
    """
    ensure_workspace()
    path = os.path.join(WORKSPACE_DIR, filename)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise OSError(f"Failed to write workspace file '{filename}': {e}") from e


def list_workspace_files() -> list:
    """List all files currently in the workspace directory."""
    ensure_workspace()
    return os.listdir(WORKSPACE_DIR)

  
def capture_observation(cmd_result: dict) -> str:
        """Format command result as an observation string for the agent loop."""
        parts = []
        if cmd_result["stdout"].strip():
            parts.append(f"STDOUT:\n{cmd_result['stdout'].strip()}")
        if cmd_result["stderr"].strip():
            parts.append(f"STDERR:\n{cmd_result['stderr'].strip()}")
        parts.append(f"Return code: {cmd_result['returncode']}")
        files = list_workspace_files()
        if files:
            parts.append(f"Workspace files: {', '.join(files)}")
        return "\n".join(parts)
