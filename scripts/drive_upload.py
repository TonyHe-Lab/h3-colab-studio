#!/usr/bin/env python3
"""Drive upload for colab outputs (route B, headless).

Uses the colab CLI's stored OAuth token (scope drive.file) to create
(app-visible) files in the target account's Drive. Token values are read
programmatically and NEVER printed.

Usage:
  python3 drive_upload.py --file <local file> \
      --drive-path "Colab/Images/sdxl-astronaut-cat-1024.png"

Prints: DRIVE_OK <fileId> <size> <drivePath>   (size verified via files.get)
"""
import argparse
import json
import pathlib
import sys
import urllib.parse
import urllib.request

TOKEN_FILE = pathlib.Path.home() / ".config/colab-cli/token.json"
# Google public OAuth clients require a quota project with Drive API enabled.
# Create your own GCP project, enable the Drive API on it, and put its ID here.
QUOTA_PROJECT = "your-gcp-quota-project"


def get_access_token():
    d = json.loads(TOKEN_FILE.read_text())
    body = urllib.parse.urlencode({
        "client_id": d["client_id"],
        "client_secret": d["client_secret"],
        "refresh_token": d["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(d["token_uri"], data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read())
    return tok["access_token"]


def api(method, url, token, body=None, ctype="application/json"):
    data = body.encode() if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": ctype,
                                          "x-goog-user-project": QUOTA_PROJECT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read() or b"{}")


def find_or_create_folder(token, path):
    """path like 'Colab/Images' -> folder id (created if missing)."""
    parts = [p for p in path.split("/") if p][:-1]
    parent = None
    for part in parts:
        q = urllib.parse.quote(
            f"name='{part}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            + (f" and '{parent}' in parents" if parent else ""))
        res = api("GET", f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id,name)", token)
        files = res.get("files", [])
        if files:
            parent = files[0]["id"]
        else:
            meta = {"name": part, "mimeType": "application/vnd.google-apps.folder"}
            if parent:
                meta["parents"] = [parent]
            parent = api("POST", "https://www.googleapis.com/drive/v3/files", token,
                         json.dumps(meta))["id"]
    return parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--drive-path", required=True, help="e.g. Colab/Images/foo.png")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    local = pathlib.Path(args.file)
    if not local.is_file():
        sys.exit(f"not a file: {local}")
    token = get_access_token()
    name = args.drive_path.rstrip("/").split("/")[-1]
    parent = find_or_create_folder(token, args.drive_path)

    if args.overwrite:
        q = urllib.parse.quote(f"name='{name}' and trashed=false"
                               + (f" and '{parent}' in parents" if parent else ""))
        for f in api("GET", f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id)", token).get("files", []):
            api("DELETE", f"https://www.googleapis.com/drive/v3/files/{f['id']}", token)

    boundary = "==colab-upload=="
    meta = json.dumps({"name": name, **({"parents": [parent]} if parent else {})})
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{meta}\r\n"
            f"--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n").encode() \
        + local.read_bytes() + f"\r\n--{boundary}--".encode()
    res = api("POST",
              "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size",
              token, body, f"multipart/related; boundary={boundary}")
    size = int(res.get("size", 0))
    if size != local.stat().st_size:
        sys.exit(f"SIZE MISMATCH drive={size} local={local.stat().st_size}")
    print(f"DRIVE_OK {res['id']} {size} {args.drive_path}")


if __name__ == "__main__":
    main()
