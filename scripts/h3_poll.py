# Quick poll: check ComfyUI queue/history state. Short exec, exits in seconds.
# Prints one STATUS line: idle|running|done:<name>|error:<msg>
import json
import os
import urllib.request

SERVER = "127.0.0.1:8188"
pid = open("/content/current_prompt_id.txt").read().strip()

q = json.loads(urllib.request.urlopen(f"http://{SERVER}/queue", timeout=10).read())
if q["queue_running"] or q["queue_pending"]:
    print("STATUS running")
else:
    h = json.loads(urllib.request.urlopen(f"http://{SERVER}/history/{pid}", timeout=10).read())
    e = h.get(pid)
    if not e:
        print("STATUS idle:no-history-yet")
    else:
        st = e["status"]
        if st.get("status_str") == "error":
            msgs = [m[1].get("exception_message", "")[:150] for m in st.get("messages", []) if m[0] == "execution_error"]
            print("STATUS error:" + (msgs[0] if msgs else json.dumps(st)[:150]))
        else:
            outs = []
            for nid, out in e.get("outputs", {}).items():
                for media in out.get("images", []) + out.get("videos", []):
                    outs.append(media["filename"])
            print("STATUS done:" + (",".join(outs) or "no-files"))
