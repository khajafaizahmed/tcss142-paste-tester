from flask import Flask, request, Response, send_from_directory
import os, tempfile, subprocess, shutil, re

app = Flask(__name__)

# ================= ON/OFF SWITCH =================
# The tester is OFF unless the host sets TESTER_ENABLED=true.
# To bring it back: set TESTER_ENABLED=true in the service's environment
# (Render -> Environment) and redeploy. To turn it off again, remove it.
TESTER_ENABLED = os.environ.get("TESTER_ENABLED", "").strip().lower() in ("1", "true", "yes")
OFFLINE_MSG = (
    "This tester is currently offline.\n\n"
    "It was run for a past TCSS 142 offering and has been switched off. "
    "If you need it, contact Faiz."
)

# Limits that apply while the tester is on
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024        # one .java file, not an upload service
JAVA_HEAP = os.environ.get("JAVA_MAX_HEAP", "256m")   # cap memory for student code
MAX_OUTPUT_CHARS = 200_000                             # don't stream megabytes back

TESTER_FILE = "SurgeTester.java"
RUN_TIMEOUT = 30  # seconds


def _cap(text):
    return text if len(text) <= MAX_OUTPUT_CHARS else text[:MAX_OUTPUT_CHARS] + "\n\n[output truncated]"


@app.route("/run", methods=["POST"])
def run_tests():
    if not TESTER_ENABLED:
        return Response(OFFLINE_MSG, 503, mimetype="text/plain")

    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    if "class SurgeSimulator" not in code:
        return Response("Error: Must contain 'class SurgeSimulator'.", 400)

    code = re.sub(r'^\s*package\s+.*?;\s*', '', code, flags=re.MULTILINE)

    tmp = tempfile.mkdtemp(prefix="p2_")
    try:
        with open(os.path.join(tmp, "SurgeSimulator.java"), "w", encoding="utf-8") as f:
            f.write(code)

        shutil.copy(TESTER_FILE, os.path.join(tmp, "SurgeTester.java"))

        comp = subprocess.run(
            ["javac", f"-J-Xmx{JAVA_HEAP}", "SurgeTester.java", "SurgeSimulator.java"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        if comp.returncode != 0:
            msg = "Compilation failed.\n\n"
            if comp.stderr: msg += "STDERR:\n" + comp.stderr + "\n\n"
            if comp.stdout: msg += "STDOUT:\n" + comp.stdout + "\n"
            return Response(msg, 200, mimetype="text/plain")

        run = subprocess.run(
            ["java", f"-Xmx{JAVA_HEAP}", "SurgeTester"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        return Response(_cap((run.stdout or "") + (( "\n" + run.stderr) if run.stderr else "")), 200, mimetype="text/plain")

    except subprocess.TimeoutExpired:
        return Response("⏱️ Execution timed out after 30 seconds.", 200, mimetype="text/plain")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@app.get("/healthz")
def healthz():
    return "ok", 200

@app.get("/")
def index():
    # serve the UI from the repo root
    return send_from_directory(".", "index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
