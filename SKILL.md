---
name: h3-colab-studio
description: >-
  Build and operate a prompt-to-video workspace for MiniMax H3 with an agent
  execution bridge to Google Colab G4 running ComfyUI. Use when the user wants
  to generate single-shot or multi-shot MiniMax H3 videos on Colab, optimize
  story ideas into official H3 structured prompts, build a job-queue control
  app for H3 video production, or stitch and verify multi-shot H3 clips.
---

# H3 Colab Studio — Prompt-to-Video Workspace with an Agent Bridge

Upstream: `Rea1Felix/H3-colab-studio` (commit `9164b8b`, 2026-11-06, MIT).
References and `scripts/stitch.sh`
are upstream verbatim; this file adds field-tested gates below (2026-11).

## Field-tested gates — read before any run

- **G4 gate — VERIFIED 2026-11-07 21:56, with an allocation caveat.** A Google AI subscription (Colab Pro / AI Pro) account
  CAN select the Colab **G4** runtime in the dropdown (verified by opening
  Runtime → Change runtime type in Untitled0.ipynb, selecting G4, then
  cancelling without saving; no session started, no units spent). The dropdown
  lists CPU, G4, A100, L4, T4, H100 (greyed out / unavailable), v6e-1 TPU,
  v5e-1 TPU.
  **Caveat (2026-11-07 22:04): listing G4 does not guarantee allocation —
  on real connect Colab said G4 was unavailable and allocated
  A100-SXM4-80GB (79.3 GiB) instead. A100 80GB satisfies the int8 H3
  requirements and the full download verified on it. Do not re-litigate
  the gate: it passed. Re-check only if the account or plan changes.
- **Execution is browser-driven or CLI-driven.** Colab has no public
  automation API for allocation; drive it through the browser (open the
  notebook from `dseditor/minimax-h3-colab`, `H3_Basic_ComfyUI.ipynb`) or
  through `google-colab-cli` (see `scripts/patch-411.py` for a required
  fix). Sign-in / verification steps are always the user's own.
- **API route (added 2026-11-07, preferred for repeat runs).** ComfyUI is
  headless by design: the web UI is just one client over its HTTP API, so
  generation itself needs no browser clicks. `scripts/comfyui_api_run.py`
  (stdlib-only, `urllib`) queues the API-format workflow JSON via
  `POST /prompt`, polls `GET /history/{prompt_id}`, downloads finished
  clips via `GET /view`. One-time setup: export the workflow once from
  the UI (Settings → Enable Dev mode → "Save (API Format)"), then fill
  the real node ids into `scripts/shots.example.json` (the ids in the
  example are placeholders — match `class_type` in the exported JSON).
  Run the script from a notebook cell against `127.0.0.1:8188`; the
  browser is then needed only to start the notebook and export the JSON.
  This removes UI clicking/pasting overhead; it does NOT make sampling
  faster. `comfy-cli` only installs/manages ComfyUI and nodes — it
  cannot run a workflow.
- **Cost control.** Record the compute-unit balance before and after every
  session, delete the runtime at the end so billing stops. Measured G4 burn
  is ~8.94 units/hour (panel shows ~10.05). A 3-shot 15 s video at
  1376x768 costs ~4.8 units including setup; a single 15 s clip at
  1920x1088 costs ~17.6 units and samples ~69 minutes.
- **Drive cache (measured 2026-11-07).** The 5 model files are cached at
  `MyDrive/h3-models/` (40G total, verified name + size). Upload from the
  runtime disk took 131.2 s — about the same as re-downloading from
  HuggingFace (~117 s) — so the cache saves HF dependence, not time.
  Copy-back speed (Drive → runtime disk) is still unmeasured; time it on
  the next session before claiming the cache wins. Mount note: the first
  `drive.mount()` call times out after ~120 s waiting for authorization;
  if the user authorizes after that, re-run the cell — with authorization
  already done it succeeds in ~15 s with no new popup.
- **When to use H3 vs Flow/Omni.** Flow with Omni 1.2 Flash is already
  verified on this account (8 s 720p = 24 Flow credits, ~1 minute, 1,026
  credits left 2026-11-07). Use Flow for one-off instant clips. Use H3
  only for real multi-shot pieces or a repeatable series where per-shot
  control, native resolution, audio track and no watermark matter — and
  only if the G4 gate passes.

## What this builds

- Build three cooperating parts: a job-queue app the user drives, a prompt optimizer that rewrites ideas into the official MiniMax H3 prompt structure, and yourself as the execution bridge to Google Colab.

- Treat the app as the control surface only. GPU generation happens on Colab, never inside the app, and the app must say so plainly instead of faking a live generate button.

- Expect the payoff to be repeatable multi-shot videos. A single H3 generation is one continuous take with no cuts, so story structure comes from generating one clip per shot and stitching, which this workflow makes routine.

## Set up Colab and H3

- Confirm the user has a Google account with Colab compute units available, for example through Google AI Ultra or a Colab paid plan, and warn them that granted unit pools can expire (the Ultra grant lasts about 90 days).

- Read [the Colab runbook](references/colab-runbook.md) before the first run and follow it exactly. It carries the verified notebook choice, the model files, and the two failure fixes that cost real time when missed.

- Pick the G4 runtime (RTX PRO 6000 Blackwell, about 96 GB VRAM). Budget with the measured burn of about 8.9 units per hour rather than the roughly 10 units per hour the panel displays.

- Record the compute-unit balance before and after every session, and delete the runtime at the end of the session so billing stops.

- Keep all shots of one video inside a single session. Model downloads dominate setup time, so a fresh runtime per shot wastes units and minutes. Total model download is about 58 GiB plus a ~1.96 GB Turbo LoRA.

## Build the workspace app

- Build the app lightweight (a queue app is optional — a plain `shots.json` plus the scripts is enough):
  - **Local coding environments (Antigravity, Claude Code, Cursor, etc.)**: Build a lightweight persistent web app (for example, Vite or Next.js backed by local JSON or SQLite storage) with clean API routes or CLI helpers so job records persist on disk and you can read and update them directly.
  - **Hosted agent workspaces**: Use the host platform's persistent full-stack web app capability so job records survive across sessions and can be updated programmatically.

- Give the form these fields: idea text, mode (T2V first, I2V and FL2VA and Ref2VA marked as coming later), per-shot duration of 5, 8, 10 or 15 seconds, resolution tier (standard 864x480, high 1120x640, max 1376x768), aspect ratio, shot count (auto, 1, 3 or 5), seed (random or fixed), turbo toggle, and style.

- Show a live optimized-prompt preview beside the form, built from the structure in [the prompt spec](references/prompt-spec.md), and let the user edit the draft before submitting.

- Save every submission as a job with a status of queued, optimizing, running, done or failed, and expose an update interface (API route, CLI helper, or workspace action) that you use to backfill status, output specs, units consumed and a result note after execution.

- Seed the history with one real completed job once you have run one, so the queue never looks like a demo.

- Put a small bridge-status panel in the app naming the backend (Colab G4), the last measured unit balance with its date, and the three steps: submit here, ask the agent in chat to run job number N, agent generates and backfills the result.

## Write the H3 prompts

- Read [the prompt spec](references/prompt-spec.md) for the official H3 structure and the multi-shot method before writing any prompt.

- Structure every T2V prompt as a subject and scene definition, one block per shot with a shot-type label, an overall soundscape line, and a non-diegetic music line.

- Repeat the main character description word for word in every shot block, repeat the palette and style words in every block, and use one shared fixed seed for all shots of a video. Verbatim repetition plus a shared seed is what makes separately generated clips look like one film.

- Write shot blocks in English even when the user idea arrives in another language. H3 follows detailed English camera language more reliably.

- Keep each shot to one location and one main action. H3 renders a single continuous take per generation, so anything that needs a cut belongs in the next shot block.

## Execute a job and finish it

- Mark the job running in the app before opening Colab, then run the whole shot list in one session following [the Colab runbook](references/colab-runbook.md).

- Download each finished clip before queueing the next shot, and name files in shot order so stitching cannot scramble the sequence.

- Stitch the clips locally with [scripts/stitch.sh](scripts/stitch.sh) and verify the result with `ffprobe` (resolution, duration, fps, audio track) before calling it done.

- Backfill the job in the app with the final specs, the measured units consumed and an honest note, then deliver the video file to the user in chat with a per-shot quality read.

- Report failures with the exact error text and the state you left behind, including the balance after cleanup and whether the runtime was deleted.

## Measured reference points

- Treat these as single-run measurements from November 2026 on a G4, useful for planning rather than promises: 15 seconds at 864x480 sampled in about 4 to 5 minutes, 5 seconds at 1376x768 in about 3 minutes per shot, and 15 seconds at 1920x1088 in about 69 minutes.

- A100-SXM4-80GB measured 2026-11-07 (first real H3 run, 1376x768, 5 s/shot, int8): 351 s for shot 1 (includes first model load), ~317 s each for shots 2 and 3; 3 shots took 33 minutes wall-clock. G4's ~3 min/shot reference does NOT transfer to A100. Output duration is 5.17 s per shot (124 frames @ 24 fps, template frame-grid alignment), not 5.0 s.

- Expect a three-shot 15-second video at 1376x768 to consume roughly 5 compute units including setup when the session runs clean.

## Pitfalls

- Avoid the `keboqi/minimax-h3` Prism Studio notebook UI for H3. Its job binding code threw an `IndexError` before generation on every attempt in testing, while the direct ComfyUI route worked.

- Download the Turbo LoRA before the first queue. The working notebook omits it and the ComfyUI template blocks with a missing-model error until it exists.

- Check the `SaveVideo` node format field shows `mp4` before every queue. A blank field silently discards a finished generation after the full sampling time.

- Watch for Colab idle disconnects on long sampling runs. Reconnecting to the same runtime usually preserves the session, so reconnect before restarting anything.

## Websites

- [Google Colab](https://colab.research.google.com/) for the GPU runtime. Carry the account that owns the compute units and the exact notebook from the runbook, and verify the balance and GPU model in the session panel.

- [dseditor/minimax-h3-colab on GitHub](https://github.com/dseditor/minimax-h3-colab) for the working direct-ComfyUI notebook this workflow is built on.

- [MiniMax H3](https://www.minimax.io/) for the model and its official prompt-writing material. Prefer the official prompt structure over community folklore when they disagree.
