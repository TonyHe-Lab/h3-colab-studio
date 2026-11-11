#!/usr/bin/env python3
"""VoxCPM2 配音 stage — H3 管线附属步骤（同 runtime 内跑，勿单独开 runtime）。

用法（Colab 无头约定，exec 无法传参，全部走固定路径）：
  1. colab upload dub.json /content/dub.json   # 角色表 + 台词行
  2. colab upload voxcpm_dub.py /content/voxcpm_dub.py
  3. nohup python3 /content/voxcpm_dub.py > /content/dub.log 2>&1 &   # 轮询 dub.log
  4. 产物 /content/dub/：每行 <shot>-<idx>-<role>.wav（干音）+ .room.wav（加混响）+ manifest.json
  5. colab download 拉回 + 按铁律存 Drive 后再关机

dub.json 格式：
{
  "roles": { "S1": "(三十岁成熟女性，温婉磁性)描述里不要写括号外的内容", ... },
  "lines": [ {"shot": "shot1", "role": "S1", "text": "台词……"}, ... ]
}
角色描述格式：描述文字本身放括号前缀（VoxCPM2 Voice Design 语法），脚本自动拼接。
注意：PyPI 版 generate() 无 seed 参数，复现靠固定文本 + 锁 voxcpm 版本。
"""
import json, os, subprocess, sys, time

IN_JSON = "/content/dub.json"
OUT_DIR = "/content/dub"
AECHO = "aecho=0.85:0.82:22|48:0.14|0.07"  # 早期反射混响，干音→场景内声音

import torch
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU", flush=True)

from voxcpm import VoxCPM
import soundfile as sf

cfg = json.load(open(IN_JSON, encoding="utf-8"))
os.makedirs(OUT_DIR, exist_ok=True)

t0 = time.time()
model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
print(f"model loaded {time.time()-t0:.0f}s sr={model.tts_model.sample_rate}", flush=True)

def prep_text(text: str, role_desc: str) -> str:
    """防吞尾音：非感叹/问句结尾统一补 ……；角色描述用括号前缀。"""
    text = text.strip()
    if not text.endswith(("……", "！", "？", "!", "?")):
        text = text.rstrip("。，,.") + "……"
    return f"({role_desc}){text}"

manifest = []
for i, line in enumerate(cfg["lines"]):
    role = line["role"]
    desc = cfg["roles"][role]
    full = prep_text(line["text"], desc)
    t = time.time()
    wav = model.generate(text=full, cfg_value=2.0, inference_timesteps=10)
    sr = model.tts_model.sample_rate
    base = f"{line.get('shot', 'x')}-{i:02d}-{role}"
    raw = os.path.join(OUT_DIR, base + ".wav")
    sf.write(raw, wav, sr)
    # 早期反射混响版（贴画面用）；干音保留便于重混
    room = os.path.join(OUT_DIR, base + ".room.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
                    "-af", AECHO, "-c:a", "pcm_s16le", room], check=True)
    entry = {"idx": i, "shot": line.get("shot"), "role": role,
             "text": line["text"], "raw": raw, "room": room,
             "duration_s": round(len(wav) / sr, 2), "gen_s": round(time.time() - t, 1)}
    manifest.append(entry)
    print("OK", base, entry["duration_s"], "s", flush=True)

with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)
print("DUB_DONE", len(manifest), "lines", flush=True)
