# One H3 shot runner (stdlib only). Reads SHOT_INDEX from env via colab exec --env.
# Uses the verified API flow: POST /prompt -> poll /history -> GET /view.
# Output goes to /content/output/<name>.mp4 for later download + Drive upload.
import json
import os
import time
import urllib.parse
import urllib.request
import uuid

SHOT_INDEX = int(os.environ.get("SHOT_INDEX", "0"))
SERVER = "127.0.0.1:8188"
OUT_DIR = "/content/output"

os.makedirs(OUT_DIR, exist_ok=True)
workflow = json.load(open("/content/workflow_api_t2v_local.json"))
shots = json.load(open("/content/shots.json"))
overrides = shots[SHOT_INDEX]["overrides"]
name = shots[SHOT_INDEX]["name"]

wf = json.loads(json.dumps(workflow))  # deepcopy
for path, value in overrides.items():
    nid, _, key = path.split(".", 2)
    wf[nid]["inputs"][key] = value


def http_json(method, url, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


client_id = str(uuid.uuid4())
t0 = time.time()
res = http_json("POST", f"http://{SERVER}/prompt", {"prompt": wf, "client_id": client_id})
assert not res.get("node_errors"), f"node_errors: {res['node_errors']}"
pid = res["prompt_id"]
print(f"[{name}] queued prompt_id={pid}", flush=True)

deadline = time.time() + 3600
while time.time() < deadline:
    hist = http_json("GET", f"http://{SERVER}/history/{pid}")
    entry = hist.get(pid)
    if entry and entry.get("status", {}).get("completed"):
        break
    time.sleep(10)
else:
    raise TimeoutError(f"{name} not finished in 3600s")

status = entry["status"]
if status.get("status_str") == "error":
    raise RuntimeError(f"{name} failed: {status}")

for nid, out in entry.get("outputs", {}).items():
    for media in out.get("images", []) + out.get("videos", []):
        fname = media["filename"]
        sub = media.get("subfolder", "")
        url = (f"http://{SERVER}/view?filename={urllib.parse.quote(fname)}"
               f"&subfolder={urllib.parse.quote(sub)}&type={media.get('type','output')}")
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        local = os.path.join(OUT_DIR, f"{name}.mp4")
        with open(local, "wb") as f:
            f.write(data)
        print(f"VERIFY {name} exists: True bytes: {len(data)} elapsed: {time.time()-t0:.0f}s", flush=True)
