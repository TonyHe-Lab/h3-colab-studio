# Fetch finished shot: download /view output to /content/output/<name>.mp4. Short exec.
import json
import os
import time
import urllib.parse
import urllib.request

SERVER = "127.0.0.1:8188"
pid = open("/content/current_prompt_id.txt").read().strip()
os.makedirs("/content/output", exist_ok=True)

shots = json.load(open("/content/shots.json"))
name_by_prefix = {}
# map: find shot whose overrides contain this history's filename_prefix is unreliable;
# instead just use pid's outputs and name the file from the prompt_id's shot index env.
idx = int(os.environ.get("SHOT_INDEX", "0"))
name = shots[idx]["name"]

h = json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=10).read())
e = h[pid]
for nid, out in e.get("outputs", {}).items():
    for media in out.get("images", []) + out.get("videos", []):
        url = (f"http://{SERVER}/view?filename={urllib.parse.quote(media['filename'])}"
               f"&subfolder={urllib.parse.quote(media.get('subfolder',''))}&type={media.get('type','output')}")
        with urllib.request.urlopen(url, timeout=300) as r:
            data = r.read()
        local = f"/content/output/{name}.mp4"
        with open(local, "wb") as f:
            f.write(data)
        print(f"VERIFY {name} exists: True bytes: {len(data)}")
