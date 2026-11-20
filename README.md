# tcss142-paste-tester

> **Status: offline.** This tester was used for a past TCSS 142 offering and is switched off.
> The page still loads, but `/run` returns *503 – tester offline* until it is turned back on.

## Turning it back on

The tester only runs code when the environment variable `TESTER_ENABLED=true` is set.

1. In the hosting dashboard (Render → this service → **Environment**), add `TESTER_ENABLED` = `true`.
2. Save and redeploy (or **Resume** the service if it was suspended).
3. To switch it off again, delete the variable (or set it to `false`) and redeploy.

Running locally: `TESTER_ENABLED=true python server.py`

Optional: `JAVA_MAX_HEAP` (default `256m`) caps memory for submitted code.

**Before you turn it on, keep in mind:** this service compiles and runs whatever Java is posted to `/run`.
The limits here (30 s timeout, memory cap, 200 KB request cap, non-root container user) reduce the damage,
but submitted code can still read the container's environment variables and make network requests.
Don't put secrets in this service's environment, and switch it off again when the class ends.

A simple web page 
Students paste Java code 
It runs it using your private SurgeTester.java 
All free, no signup or cost
