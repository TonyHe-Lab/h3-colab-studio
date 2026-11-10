# Colab runbook for MiniMax H3 (verified November 2026)

Follow this in order. Every step marked VERIFIED was executed end to end on a
Google AI Ultra account in November 2026.

## 0. Prerequisites

- A Google account signed in, with Colab compute units available. The Ultra
  subscription grant observed was 2,500 units with a 90-day validity window.
- Nothing to install locally except ffmpeg for stitching and verification.

## 1. Open the session

1. Record the compute-unit balance before starting (Colab shows it in the
   top-right resource panel). You need the before and after numbers for the
   job record.
2. Open the notebook from the GitHub repo `dseditor/minimax-h3-colab`, file
   `H3_Basic_ComfyUI.ipynb`.
3. Set the runtime to G4 (Runtime, Change runtime type). VERIFIED specs from
   `nvidia-smi`: NVIDIA RTX PRO 6000 Blackwell Server Edition, 97,887 MiB
   VRAM, about 176.9 GB system RAM, about 235 GB disk.
4. Run the notebook cells in order until ComfyUI is up. Setup takes about
   2 to 3 minutes.

VERIFIED billing: the panel displays roughly 10.05 units per hour, but the
measured deduction was 1.49 units per 10 minutes, about 8.94 units per hour.
Budget with the measured number.

## 2. Get the models

Download the model components through the notebook Hugging Face cells when
the in-ComfyUI download stalls. The combination that worked:

- Diffusion model: `Minimax-h3_Singularity_x_10Eros-Max_PRISM_int8.safetensors`
  (int8 build with acceleration fused in)
- Text encoder: `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`
- Video VAE and audio VAE: the official MiniMax files offered by the notebook

Total download is about 58 GiB and took about 3 minutes on Colab networking.

### Fix 1 (do this before the first queue): the missing Turbo LoRA

The notebook download cell ships only four files and omits the Turbo LoRA the
ComfyUI template references. The first queue blocks with a missing-model
error naming `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`,
and the in-ComfyUI download button stalled in testing. Download it directly
in an added notebook cell:

```python
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="lightx2v/Minimax-h3-Turbo",
    filename="minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
    local_dir="/content/ComfyUI/models/loras",
)
```

The file is about 1.96 GB. Refresh ComfyUI afterwards and confirm the
missing-model count is zero. This applies even when turbo mode is off,
because the template graph contains the LoRA loader node regardless.

## 3. Configure the workflow

Load the template from Template Library, Video, MiniMax H3 text-to-video
(workflow id `video_minimax_h3_t2v`).

Set per shot:

- Prompt text (one shot block per generation)
- Duration in seconds (5.0 for a standard shot)
- Resolution through the megapixels parameter at 16:9:
  - 0.41 MP gives 864×480
  - 1.0 MP gives 1376×768 actual output (the selector computes 1344 wide,
    the graph rounds to 1376)
  - 2.0 MP gives 1920×1088
- `noise_seed`: one fixed seed shared by every shot of the same video
- Filename prefix that encodes shot order, for example `video/shot1_wide`

### Fix 2 (check before every queue): the SaveVideo format field

Confirm the SaveVideo node has format `mp4` and codec `auto`, and that the
format field is not empty. In testing, a parameter reset emptied this field
and a completed 69-minute generation failed at the save step with
`TypeError: SaveVideo.execute() missing 1 required positional argument:
'format'`. The frames survived in cache that time and re-saved in seconds,
but do not rely on the cache.

## 4. Generate

Queue one shot at a time. VERIFIED generation times on G4:

- 864×480, 15 s: about 4 to 5 minutes
- 1376×768, 5 s: about 2 minutes 53 seconds to 2 minutes 59 seconds per shot
- 1920×1088, 15 s: 1 hour 9 minutes 4 seconds of sampling

Download each MP4 to the local machine as soon as it finishes, before
queueing the next shot. If Colab idle-disconnects during a long run,
reconnect promptly: the same VM and its state came back in testing and the
run continued.

## 5. Shut down and account for cost

1. Read the balance again and compute the session consumption.
2. Disconnect and delete the runtime. Billing stops only after deletion.
3. Report balance before, balance after, units consumed, and per-shot times.

VERIFIED session totals: a 24-minute session with one 15-second 864×480
clip cost 2.51 units including model downloads. A 35-minute session with
three 5-second 1376×768 clips cost 4.80 units. A 1920×1088 session cost
17.59 units, dominated by the 69-minute sampling.

## What not to use

- Do NOT use the `keboqi/minimax-h3` notebook Prism Studio UI. Both attempts
  (15 s and 5 s) failed during input preparation with
  `IndexError: tuple index out of range` at `h3_ui/job_bindings.py` line 119,
  before any generation started. The models were present. It is a UI bug,
  and the direct ComfyUI route in this runbook is the workaround.
