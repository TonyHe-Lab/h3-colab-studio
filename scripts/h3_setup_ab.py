"""H3 Colab headless setup: env check -> install ComfyUI -> download models -> launch.

Run on the Colab runtime via `colab exec -f h3_setup.py` right after
`colab new -s h3 --gpu G4` (fallback A100). Adapted from the verified cells of
dseditor/minimax-h3-colab H3_Basic_ComfyUI.ipynb (Nov 2026), with these changes:
- Model set follows the OFFICIAL native workflow docs
  (docs.comfy.org/tutorials/video/minimax/minimax-h3-native):
  official Comfy-Org int8_convrot diffusion model instead of the community
  PRISM merge; same text encoder / VAEs; official turbo LoRA repo.
- Headless: no UI proxy fixes, no --enable-manager (not needed for /prompt API).
- Prints machine-readable PROBE lines for the orchestrator (GPU, VRAM, disk).

Everything is idempotent; safe to re-run after an idle reconnect.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

COMFY = Path("/content/ComfyUI")
MODELS = Path("/content/models-manifest.json")

# (repo_id, filename, comfy_models_subdir)
FILES = [
    ("Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "diffusion_models"),
    ("Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors", "diffusion_models"),
    ("Comfy-Org/MiniMax-H3", "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "text_encoders"),
    ("Comfy-Org/MiniMax-H3", "vae/minimax_h3_video_vae_int8_convrot.safetensors", "vae"),
    ("Comfy-Org/MiniMax-H3", "vae/minimax_h3_audio_vae_fp32.safetensors", "vae"),
    ("Comfy-Org/MiniMax-H3", "loras/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "loras"),
]

EXPECTED_GB = {  # nominal sizes, GiB, from HF file listing 2026-11-10
    "minimax_h3_fl2va_pruned_int8_convrot.safetensors": 19.5,
    "minimax_h3_ref2va_pruned_int8_convrot.safetensors": 19.5,
    "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors": 14.6,
    "minimax_h3_video_vae_int8_convrot.safetensors": 1.9,
    "minimax_h3_audio_vae_fp32.safetensors": 0.55,
    "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors": 1.8,
}


def probe():
    import torch
    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    props = torch.cuda.get_device_properties(0)
    drv = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    disk = shutil.disk_usage("/content")
    info = {
        "gpu": name, "capability": list(cap),
        "vram_gb": round(props.total_memory / 2**30, 1),
        "driver": drv, "torch_cuda": torch.version.cuda,
        "disk_free_gb": round(disk.free / 2**30, 1),
    }
    print("PROBE " + json.dumps(info))
    if cap < (8, 0):
        raise RuntimeError(f"GPU capability {cap} too low for int8 model; need sm80+ (A100/L4/G4).")
    if int(drv.split(".")[0]) < 580 and (torch.version.cuda or "").startswith("13") is False:
        pass  # driver check only blocks the cu13 reinstall path below
    return info


def install_comfy():
    if not COMFY.exists():
        subprocess.run(["git", "clone", "--depth", "1",
                        "https://github.com/Comfy-Org/ComfyUI.git", str(COMFY)], check=True)
    req = ["-r", str(COMFY / "requirements.txt"), "comfy-aimdo"]
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *req], check=True)
    import torch
    if not (torch.version.cuda or "").startswith("13"):
        print("reinstalling PyTorch for CUDA 13 ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "torch", "torchvision",
                        "--index-url", "https://download.pytorch.org/whl/cu13"], check=True)


def download_models():
    from huggingface_hub import hf_hub_download
    manifest = []
    for repo, fname, folder in FILES:
        target = COMFY / "models" / folder / Path(fname).name
        if not target.is_file():
            got = Path(hf_hub_download(repo_id=repo, filename=fname, local_dir="/content/hf"))
            got.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(got), str(target))
        size_gib = target.stat().st_size / 2**30
        nominal = EXPECTED_GB.get(Path(fname).name)
        ok = nominal is None or size_gib >= nominal * 0.95
        manifest.append({"file": target.name, "dir": folder,
                         "gib": round(size_gib, 2), "size_ok": bool(ok)})
        print(f"MODEL {manifest[-1]}")
    MODELS.write_text(json.dumps(manifest))
    bad = [m for m in manifest if not m["size_ok"]]
    if bad:
        raise RuntimeError(f"model size check failed: {bad}")


def launch():
    # No --cpu-vae: A100 80GB fits full decode; --cpu-vae caused a sage-attention
    # q/k/v device mismatch (comfy_kitchen) that crashed the first shot.
    log = open("/content/comfyui.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd=str(COMFY), stdout=log, stderr=subprocess.STDOUT)
    for _ in range(240):
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/system_stats", timeout=2)
            print("READY ComfyUI http://127.0.0.1:8188")
            return
        except Exception:
            time.sleep(2)
    print(open("/content/comfyui.log").read()[-3000:])
    raise RuntimeError("ComfyUI failed to start")


if __name__ == "__main__":
    probe()
    install_comfy()
    download_models()
    launch()
