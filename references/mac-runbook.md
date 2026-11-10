# H3 headless runbook — Mac mini orchestrator (planned 2026-11-10, execute after colab login)

原则：启动就跑，验证完就关。所有能在本地完成的都在本地完成；runtime 里只做
必须用 GPU 磁盘的事（装环境、下模型、采样）。每一步都有明确的 PASS 判据。

## 0. 本地预置（已在 Mac 完成 / 待完成）

| 件 | 位置 | 状态 |
|---|---|---|
| colab CLI 0.7.5 + 411 补丁 | ~/.local/bin/colab | 已装已打补丁 |
| API 脚本 comfyui_api_run.py | 本仓 scripts/ | 本仓 scripts/ |
| 工作流 API JSON | scripts/workflow_api_t2v_local.json | **已生成并验证**（2026-11-10）：本地 ComfyUI（scratch/comfy-local + comfyui-local，已用完清理）前端 graphToPrompt 导出官方本地模板；已过服务器级校验（排队 node_errors={}，仅在占位空模型文件处按预期失败）。22 节点，官方 int8_convrot 全套 |
| shots.json | scripts/shots.json | **已生成**：3 镜真实 node id（prompt=140:131 / seed=140:129 / SaveVideo=92 / 分辨率=115 / 时长=140:133），seed 424242，megapixels 1.0（1376x768），5s/镜；dry-run 通过 |
| h3_setup.py | scripts/h3_setup.py | 已写好（probe→装→下模型→后台启动） |
| stitch.sh | scripts/stitch.sh | 已有 |

注意：`api_minimax_h3_t2v.json` 是 MiniMax **付费 API** 节点（按秒扣美元），绝不能用。
本地原生模板 = `video_minimax_h3_t2v.json`（带子图，需前端导出 API 格式）。

## 1. 会话内执行序列（一条 GPU 会话跑完三镜）

预算：启动约 8-10 分钟（装 ComfyUI + cu13 torch + 下模型 ~41GB），三镜采样
约 6 分钟/镜（A100 实测 317-351s/镜，G4 参考约 3 分钟/镜），全程 ~35-40 分钟，
约 5-6 单元（按 8.94/hr 折算，A100 8.88/hr）。跑前以 colab usage 实时为准。

1. `colab usage` → 记录余额（<5 就停）
2. `colab new -s h3 --gpu G4`；分不到 G4 时 Colab 会报不可用 → 改 A100，不硬等
3. `colab status -s h3` → PASS：READY，记录实际分到的卡和显存
4. `colab upload -s h3 -f scripts/workflow_api_t2v_local.json` + shots.json + comfyui_api_run.py
5. `colab exec -s h3 -f h3_setup.py`（timeout 调大）→ PASS：READY 行 + 5 个 MODEL 行 size_ok=true
6. Drive 挂载（首跑一次性，见 §3）
7. `colab exec -s h3 -f comfyui_api_run.py --workflow ... --shots shots.json --out <Drive路径>`
   → PASS：每个 shot 有 saved 行 + 字节数 >1MB；单镜失败立即停，报错原文
8. stitch + ffprobe（会话内或拉回本地做）→ PASS：分辨率/时长/音轨符合预期
9. `colab stop -s h3`
10. `colab sessions` → PASS：No active sessions；`colab usage` → 使用率 0.00/hr，报余额

## 2. 失败守则

- 任何 411：先查补丁 marker，重打，不换账号/认证/卡。
- 单镜失败：不自动重试整批，报错原文如实记录上报。
- 采样中断连：`colab ssh`/`exec` 重连同一会话再试，不重启。
- 5 分钟无响应：断开止损（内容先存 Drive 的原则同样适用于中间产物——每镜完成立即落 Drive）。

## 3. 产出落 Drive 的两条路（两条都已验证可用）

| 路线 | 做法 | 取舍 |
|---|---|---|
| A. drive.mount | 会话内挂载，用户浏览器授权一次（每条新 runtime 都要重授权一次，~15s） | 简单直接；但要人在线点一次 |
| B. Mac 侧 Drive API | colab CLI 的 OAuth token（scope 含 drive.file）在 Mac 上调 Drive API 上传，session 文件先 `colab download` 回本地 | 全自动零点击；代码多一层，token 只在程序内用、绝不打印 |

默认按 B 实现，A 作兜底。

## 4. 产出命名（沿用 11-10 已定的 `用途-对象-日期` 规范）

Drive：`Colab/Video/` 下
`h3-astronaut-cat-2026-11-10/shot1-wide-1376x768-5s-seed424242.mp4`（+_stitched）
