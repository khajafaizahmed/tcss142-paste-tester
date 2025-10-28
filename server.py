import os, tempfile, subprocess, shutil, re
from flask import Flask, request, Response

app = Flask(__name__)
TESTER_FILE = "SurgeTester.java"

@app.post("/run")
def run_tests():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    if "class SurgeSimulator" not in code:
        return Response("Error: Must contain 'class SurgeSimulator'.", 400)

    code = re.sub(r'^\s*package\s+.*?;\s*', '', code, flags=re.MULTILINE)

    tmp = tempfile.mkdtemp()
    try:
        open(os.path.join(tmp, "SurgeSimulator.java"), "w").write(code)
        shutil.copy(TESTER_FILE, os.path.join(tmp, "SurgeTester.java"))

        rc, out, err = subprocess.run(["javac", "SurgeTester.java", "SurgeSimulator.java"],
                                      cwd=tmp, capture_output=True, text=True).returncode, "", ""
        if rc != 0:
            return f"Compilation failed.\n\n{err or out}"

        rc, out, err = subprocess.run(["java", "SurgeTester"],
                                      cwd=tmp, capture_output=True, text=True).returncode, "", ""
        return out + ("\n" + err if err else "")
    except subprocess.TimeoutExpired:
        return "Timed out."
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@app.get("/")
def index():
    return "Backend OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
