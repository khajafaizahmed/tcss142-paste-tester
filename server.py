import os, tempfile, subprocess, shutil, re
from flask import Flask, request, Response

app = Flask(__name__)
TESTER_FILE = "SurgeTester.java"
RUN_TIMEOUT = 30  # seconds

# Simple CORS so GitHub Pages (or any static host) can call this API
@app.after_request
def add_cors(resp):
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

    # Strip package lines to avoid path issues
    code = re.sub(r'^\s*package\s+.*?;\s*', '', code, flags=re.MULTILINE)

    tmp = tempfile.mkdtemp(prefix="p2_")
    try:
        with open(os.path.join(tmp, "SurgeSimulator.java"), "w", encoding="utf-8") as f:
            f.write(code)

        shutil.copy(TESTER_FILE, os.path.join(tmp, "SurgeTester.java"))

        # Compile
        comp = subprocess.run(
            ["javac", "SurgeTester.java", "SurgeSimulator.java"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        if comp.returncode != 0:
            out = comp.stdout.strip()
            err = comp.stderr.strip()
            msg = "Compilation failed\n\n"
            if err: msg += f"STDERR:\n{err}\n\n"
            if out: msg += f"STDOUT:\n{out}\n"
            return Response(msg, 200, mimetype="text/plain")

        # Run
        run = subprocess.run(
            ["java", "SurgeTester"],
            cwd=tmp, capture_output=True, text=True, timeout=RUN_TIMEOUT
        )
        out = run.stdout or ""
        err = run.stderr or ""
        return Response(out + (("\n" + err) if err else ""), 200, mimetype="text/plain")

    except subprocess.TimeoutExpired:
        return Response("Execution timed out", 200, mimetype="text/plain")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

@app.get("/")
def index():
    return """
<!doctype html>
<title>TCSS 142 – Project 2 Paste Tester</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body{font-family:Arial, sans-serif; max-width:900px; margin:24px auto; padding:0 16px;}
  textarea{width:100%; height:320px; font-family:monospace; font-size:14px; padding:10px}
  button{margin-top:10px; padding:10px 16px; border:0; border-radius:8px; background:#4a67d6; color:#fff; cursor:pointer}
  button:hover{background:#3451b3}
  pre{background:#111;color:#eee;padding:12px;white-space:pre-wrap;border-radius:8px;margin-top:14px}
</style>
<h1>Project 2 – Paste Tester</h1>
<p>Paste your <b>SurgeSimulator.java</b> and click Run.</p>
<textarea id="code" placeholder="Paste your code here..."></textarea><br>
<button onclick="runTests()">Run Tests</button>
<pre id="out"></pre>
<script>
async function runTests(){
  const out=document.getElementById('out');
  out.textContent='Running...';
  const code=document.getElementById('code').value;
  const res=await fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});
  out.textContent=await res.text();
}
</script>
"""


if __name__ == "__main__":
    # Respect $PORT for local/dev; Render uses gunicorn with $PORT from Dockerfile
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
