# Queue one H3 shot and return immediately (short exec, no long-lived connection).
# SHOT_INDEX via --env. Prints PROMPT_ID line for the orchestrator.
import json
import os
import urllib.request
import uuid

SHOT_INDEX = int(os.environ.get("SHOT_INDEX", "0"))
SERVER = "127.0.0.1:8188"

workflow = json.load(open("/content/workflow_api_t2v_local.json"))
shots = json.load(open("/content/shots.json"))
overrides = shots[SHOT_INDEX]["overrides"]
name = shots[SHOT_INDEX]["name"]

wf = json.loads(json.dumps(workflow))
for path, value in overrides.items():
    nid, _, key = path.split(".", 2)
    wf[nid]["inputs"][key] = value

data = json.dumps({"prompt": wf, "client_id": str(uuid.uuid4())}).encode()
req = urllib.request.Request(f"http://{SERVER}/prompt", data=data, method="POST",
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as r:
    res = json.loads(r.read())
assert not res.get("node_errors"), f"node_errors: {res['node_errors']}"
open("/content/current_prompt_id.txt", "w").write(res["prompt_id"])
print(f"QUEUED {name} prompt_id={res['prompt_id']}")
