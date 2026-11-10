#!/usr/bin/env python3
"""Idempotent patch for google-colab-cli 411 Length Required bug.

Google frontend rejects POST with Content-Length: 0 from colab-cli 0.7.5.
This patch makes _issue_request send a 2-byte body b"{}" on bodyless POSTs.
Run after every `colab update` / reinstall.

Usage: python3 patch-411.py [path-to-client.py]
If no path given, tries common uv tool locations.
"""
import glob
import os
import shutil
import sys

MARKER = "411 workaround"
PATCH = (
    '        # 411 workaround (local patch 2026-11-09): Google frontend '
    'rejects POST with Content-Length: 0\n'
    '        if method == "POST" and "data" not in kwargs and "json" not in kwargs:\n'
    '            kwargs["data"] = b"{}"\n'
    '            request_headers.setdefault("Content-Type", "application/json")\n'
)
ANCHOR = 'self.logger.debug(f"Request: {method} {endpoint}")'

CANDIDATES = [
    os.path.expanduser(
        "~/.local/share/uv/tools/google-colab-cli/lib/*/site-packages/colab_cli/client.py"),
    os.path.expanduser(
        "~/Library/Application Support/uv/tools/google-colab-cli/lib/*/site-packages/colab_cli/client.py"),
]


def find_client(explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for pattern in CANDIDATES:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]  # newest python version
    return None


def main():
    path = find_client(sys.argv[1] if len(sys.argv) > 1 else None)
    if not path:
        print("client.py not found; pass its path as arg 1")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        src = f.read()

    if MARKER in src:
        print(f"already patched: {path}")
        return
    if ANCHOR not in src:
        print(f"anchor line not found in {path}; CLI may have changed, patch manually")
        sys.exit(1)

    shutil.copy2(path, path + ".orig")
    patched = src.replace(ANCHOR + "\n", ANCHOR + "\n" + PATCH, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)

    pycache = os.path.join(os.path.dirname(path), "__pycache__")
    if os.path.isdir(pycache):
        shutil.rmtree(pycache)
    print(f"patched: {path}\nbackup: {path}.orig")


if __name__ == "__main__":
    main()
