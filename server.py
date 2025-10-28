from flask import Flask, request, Response, send_from_directory
import os, tempfile, subprocess, shutil, re

app = Flask(__name__)

TESTER_FILE = "SurgeTester.java"
RUN_TIMEOUT = 30  # seconds

@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    return resp

@app.route("/run", methods=["POST", "OPTIONS"])
def run_tests():
    if request.method == "OPTIONS":
        return Response(status=204)

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
            ["javac", "SurgeTester.java", "SurgeSimulator.java"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        if comp.returncode != 0:
            msg = "Compilation failed.\n\n"
            if comp.stderr: msg += "STDERR:\n" + comp.stderr + "\n\n"
            if comp.stdout: msg += "STDOUT:\n" + comp.stdout + "\n"
            return Response(msg, 200, mimetype="text/plain")

        run = subprocess.run(
            ["java", "SurgeTester"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        return Response((run.stdout or "") + (( "\n" + run.stderr) if run.stderr else ""), 200, mimetype="text/plain")

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
