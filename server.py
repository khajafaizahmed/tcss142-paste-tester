import os, tempfile, subprocess, shutil, re
from flask import Flask, request, Response

app = Flask(__name__)

# Your internal tester file
TESTER_FILE = "SurgeTester.java"

# Give the tester enough time even on 0.1 CPU
RUN_TIMEOUT = 30  # seconds

# --- Enable simple CORS (so your GitHub Page front-end can call it) ---
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS, GET"
    return resp

# --- Main API endpoint ---
@app.route("/run", methods=["POST", "OPTIONS"])
def run_tests():
    if request.method == "OPTIONS":
        return Response(status=204)

    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    # Safety: ensure correct class
    if "class SurgeSimulator" not in code:
        return Response("Error: Must contain 'class SurgeSimulator'.", 400)

    # Remove 'package ...;' lines to avoid compilation path errors
    code = re.sub(r'^\s*package\s+.*?;\s*', '', code, flags=re.MULTILINE)

    tmp = tempfile.mkdtemp(prefix="p2_")
    try:
        # Write student code
        sim_path = os.path.join(tmp, "SurgeSimulator.java")
        with open(sim_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Copy the internal tester
        shutil.copy(TESTER_FILE, os.path.join(tmp, "SurgeTester.java"))

        # Compile
        compile_proc = subprocess.run(
            ["javac", "SurgeTester.java", "SurgeSimulator.java"],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT
        )

        if compile_proc.returncode != 0:
            msg = "Compilation failed.\n\n"
            if compile_proc.stderr:
                msg += "STDERR:\n" + compile_proc.stderr + "\n\n"
            if compile_proc.stdout:
                msg += "STDOUT:\n" + compile_proc.stdout + "\n"
            return Response(msg, 200, mimetype="text/plain")

        # Run the tester
        run_proc = subprocess.run(
            ["java", "SurgeTester"],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT
        )

        output = run_proc.stdout.strip()
        errors = run_proc.stderr.strip()
        combined = output + ("\n" + errors if errors else "")
        return Response(combined, 200, mimetype="text/plain")

    except subprocess.TimeoutExpired:
        return Response("⏱️ Execution timed out after 30 seconds.", 200, mimetype="text/plain")
    except Exception as e:
        return Response(f"Unexpected error: {e}", 200, mimetype="text/plain")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- Basic Health Check for Render ---
@app.get("/healthz")
def healthz():
    return "ok", 200


# --- Landing Page ---
@app.get("/")
def index():
    return "Backend OK — SurgeTester ready 🧩"


if __name__ == "__main__":
    # Run locally for debugging; Render overrides this with gunicorn.
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
