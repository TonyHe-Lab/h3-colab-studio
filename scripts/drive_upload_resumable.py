#!/usr/bin/env python3
"""Resumable Drive upload for >10MB files (multipart write-times out per 2026-11-11 lesson).
Same token/quota-project rules as drive_upload.py. Verifies byte count after upload.
Usage: python3 drive_upload_resumable.py --file <local> --drive-path 'Colab/Video/dir/name.mp4' [--overwrite]
"""
import argparse, json, pathlib, sys, urllib.request, urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from drive_upload import get_access_token, find_or_create_folder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--drive-path", required=True)
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
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files?q={q}&fields=files(id)",
            headers={"Authorization": f"Bearer {token}",
                     "x-goog-user-project": __import__("drive_upload").QUOTA_PROJECT})
        for f in json.load(urllib.request.urlopen(req)).get("files", []):
            d = urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files/{f['id']}", method="DELETE",
                headers={"Authorization": f"Bearer {token}",
                         "x-goog-user-project": __import__("drive_upload").QUOTA_PROJECT})
            urllib.request.urlopen(d)

    meta = json.dumps({"name": name, **({"parents": [parent]} if parent else {})}).encode()
    hdr = {"Authorization": f"Bearer {token}",
           "x-goog-user-project": __import__("drive_upload").QUOTA_PROJECT,
           "X-Upload-Content-Type": "video/mp4",
           "X-Upload-Content-Length": str(local.stat().st_size),
           "Content-Type": "application/json; charset=UTF-8"}
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
        data=meta, headers=hdr, method="POST")
    session_uri = urllib.request.urlopen(req).headers["Location"]

    size = local.stat().st_size
    put = urllib.request.Request(session_uri, data=local.read_bytes(),
                                 headers={"Content-Type": "video/mp4",
                                          "Content-Length": str(size)}, method="PUT")
    res = json.load(urllib.request.urlopen(put))
    # resumable PUT response omits "size" by default — verify via files.get
    chk = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files/{res['id']}?fields=id,size",
        headers={"Authorization": f"Bearer {token}",
                 "x-goog-user-project": __import__("drive_upload").QUOTA_PROJECT})
    real = int(json.load(urllib.request.urlopen(chk))["size"])
    if real != size:
        sys.exit(f"SIZE MISMATCH drive={real} local={size}")
    print(f"DRIVE_OK {res['id']} {size} {args.drive_path}")


if __name__ == "__main__":
    main()
