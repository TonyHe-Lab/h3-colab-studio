# SDXL astronaut cat, verified 2026-11-07 on T4.
# Headless variant: saves to /content only; Mac orchestrator downloads then
# uploads to job Drive via Drive API (route B, drive_upload.py) before stopping the runtime.
from diffusers import DiffusionPipeline
import torch
from PIL import Image
import os

MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
PROMPT = "A cozy astronaut cat floating in a colorful nebula, detailed, cinematic lighting"
NAME = "sdxl-astronaut-cat-1024.png"

os.makedirs("/content/output", exist_ok=True)
pipe = DiffusionPipeline.from_pretrained(MODEL, torch_dtype=torch.float16,
                                         variant="fp16", use_safetensors=True)
pipe.to("cuda")
image = pipe(prompt=PROMPT, num_inference_steps=30, height=1024, width=1024).images[0]
path = f"/content/output/{NAME}"
image.save(path)
im = Image.open(path)
print("VERIFY exists:", os.path.exists(path),
      "bytes:", os.path.getsize(path), "size:", im.size)
