#!/usr/bin/env python3
"""ComfyUI API runner: queue H3 (or any) workflows without touching the UI.

Why this exists: the browser-UI route works but every shot costs manual
node clicks and prompt pastes. ComfyUI is headless by design -- the web UI
is just one client over its HTTP API. This script POSTs the API-format
workflow JSON to /prompt, polls /history, and downloads outputs via /view.

Verified facts (2026-11-07, web sources + ComfyUI docs):
- POST /prompt  body {"prompt": <api_json>, "client_id": "<uuid>"}
  -> {"prompt_id": ..., "number": ..., "node_errors": {...}}
- GET /history/{prompt_id} -> outputs with filenames under
  result["outputs"][<node_id>]["images"|"videos"] (each: filename, subfolder, type)
- GET /view?filename=...&subfolder=...&type=output -> the file bytes
- WS /ws?clientId=... streams progress; this script polls REST instead
  (no websocket dependency, simpler in a Colab cell).
- The API accepts ONLY the API-format JSON (Dev Mode -> "Save (API Format)"),
  NOT the editor .json (which carries node positions / colours).
- comfy-cli only installs/manages ComfyUI and nodes; it cannot run a workflow.

Usage (run inside the Colab runtime, where ComfyUI listens on 127.0.0.1:8188):
  1. Export the workflow once from the UI: Settings -> Enable Dev mode ->
     "Save (API Format)" -> workflow_api.json. Put it next to this script
     or pass --workflow.
  2. Fill node-id mapping in shots.json (see shots.example.json):
     each shot lists overrides as "<node_id>.inputs.<key>": value.
     Find node ids by opening workflow_api.json and matching class_type
     (e.g. the text prompt node, the seed input, SaveVideo filename_prefix).
  3. python3 comfyui_api_run.py --workflow workflow_api.json \
        --shots shots.json --out /content/drive/MyDrive/h3-output

  Single shot, no shots file:
  python3 comfyui_api_run.py --workflow workflow_api.json \
        --set 12.inputs.text="A cozy astronaut cat..." \
        --set 3.inputs.noise_seed=424242 --out ./out

A100 timing reference (2026-11-07, H3 1376x768 5s, int8): ~317-351 s/shot.
The API does NOT make sampling faster; it removes the UI overhead and lets
you queue all shots from one cell, then walk away.
"""

import argparse
import copy
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid

DEFAULT_SERVER = os.environ.get("COMFYUI_SERVER", "127.0.0.1:8188")
POLL_INTERVAL = 10  # seconds between /history polls
POLL_TIMEOUT = 3600  # 1 hour per shot; H3 5s/shot is ~6 min on A100


def http_json(method, url, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {body}") from e


def http_bytes(url, timeout=120):
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"GET {url} -> HTTP {e.code}: {body}") from e


def apply_overrides(workflow, overrides):
    """overrides: {"<node_id>.inputs.<key>": value}"""
    wf = copy.deepcopy(workflow)
    for path, value in overrides.items():
        parts = path.split(".")
        if len(parts) != 3 or parts[1] != "inputs":
            raise ValueError(f"bad override path (want <node_id>.inputs.<key>): {path}")
        node_id, key = parts[0], parts[2]
        if node_id not in wf:
            raise ValueError(f"node {node_id} not in workflow (check workflow_api.json)")
        wf[node_id]["inputs"][key] = value
    return wf


def queue_prompt(server, workflow, client_id):
    url = f"http://{server}/prompt"
    res = http_json("POST", url, {"prompt": workflow, "client_id": client_id})
    if res.get("node_errors"):
        raise RuntimeError(f"node_errors: {json.dumps(res['node_errors'], indent=2)}")
    return res["prompt_id"]


def wait_for_outputs(server, prompt_id, timeout=POLL_TIMEOUT):
    url = f"http://{server}/history/{prompt_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = http_json("GET", url)
        entry = hist.get(prompt_id)
        if entry and entry.get("status", {}).get("completed"):
            if entry["status"].get("status_str") == "error":
                raise RuntimeError(f"prompt {prompt_id} failed: {entry['status']}")
            return entry.get("outputs", {})
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"prompt {prompt_id} did not finish within {timeout}s")


def download_outputs(server, outputs, out_dir):
    """Download every file listed in /history outputs. Returns local paths."""
    paths = []
    for node_id, node_out in outputs.items():
        for media in node_out.get("images", []) + node_out.get("videos", []):
            fname = media["filename"]
            subfolder = media.get("subfolder", "")
            mtype = media.get("type", "output")
            url = (f"http://{server}/view?filename={urllib.request.quote(fname)}"
                   f"&subfolder={urllib.request.quote(subfolder)}&type={mtype}")
            data = http_bytes(url)
            local = os.path.join(out_dir, fname)
            with open(local, "wb") as f:
                f.write(data)
            paths.append(local)
            print(f"  saved {local} ({len(data)} bytes)")
    return paths


def run_shot(server, workflow, client_id, out_dir, name, overrides):
    print(f"[{name}] queueing...")
    wf = apply_overrides(workflow, overrides)
    t0 = time.time()
    prompt_id = queue_prompt(server, wf, client_id)
    print(f"[{name}] prompt_id={prompt_id}, waiting...")
    outputs = wait_for_outputs(server, prompt_id)
    elapsed = time.time() - t0
    print(f"[{name}] done in {elapsed:.0f}s, downloading...")
    return download_outputs(server, outputs, out_dir)


def main():
    ap = argparse.ArgumentParser(description="Queue ComfyUI workflows via API (no UI).")
    ap.add_argument("--server", default=DEFAULT_SERVER, help="ComfyUI host:port")
    ap.add_argument("--workflow", required=True, help="API-format workflow JSON file")
    ap.add_argument("--shots", help='shots JSON: [{"name":..., "overrides":{...}}]')
    ap.add_argument("--set", action="append", default=[],
                    help="single-shot override <node_id>.inputs.<key>=<json value>, repeatable")
    ap.add_argument("--out", required=True, help="output directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate overrides and print the prompt JSON without queueing")
    args = ap.parse_args()

    with open(args.workflow) as f:
        workflow = json.load(f)
    os.makedirs(args.out, exist_ok=True)
    client_id = str(uuid.uuid4())

    shots = []
    if args.shots:
        with open(args.shots) as f:
            shots = json.load(f)
    if args.set:
        overrides = {}
        for item in args.set:
            path, _, raw = item.partition("=")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw
            overrides[path] = value
        shots.append({"name": "single", "overrides": overrides})
    if not shots:
        ap.error("give --shots and/or --set")

    for shot in shots:
        name = shot.get("name", "shot")
        overrides = shot.get("overrides", {})
        if args.dry_run:
            wf = apply_overrides(workflow, overrides)
            print(f"[{name}] dry-run prompt JSON:")
            print(json.dumps(wf, indent=2))
            continue
        try:
            run_shot(args.server, workflow, client_id, args.out, name, overrides)
        except Exception as e:
            print(f"[{name}] FAILED: {e}", file=sys.stderr)
            print("  Not retrying automatically; fix the error and re-run this shot.",
                  file=sys.stderr)
            sys.exit(1)
    print("All shots done.")


if __name__ == "__main__":
    main()
