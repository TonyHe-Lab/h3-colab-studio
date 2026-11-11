# H3 Colab Studio — 手机发起、Colab 免费算力跑 MiniMax H3 短剧

用 Google Colab 的订阅算力（A100/G4）跑 MiniMax H3 音视频联合模型，一条会话出多镜头短剧：本地写好分镜和 prompt → 一条 GPU 会话排队生成 → 本地硬切拼接 → 传回 Drive 归档。全程可无人值守，不碰 MiniMax 付费 API。

已实测产出：

| 作品 | 规格 | 消耗 |
|---|---|---|
| 宇航猫（3 镜横屏） | 1376x768，15.5s | ~10.5 单元（A100-80GB，含环境 ~90 分钟） |
| 白熬了（3 镜竖屏） | 768x1376，30.4s（10s/镜） | 8.32 单元（A100-40GB） |
| 我重生成公司打印机（3 镜竖屏，T2V） | 768x1376，30.4s | 9.18 单元 + 单镜重拍 3.12 |
| 东北大姨整治AI客服（3 镜竖屏，R2V/I2V 混合） | 768x1344，30.4s | ~14 单元（含 A/B 对比测试 5.22） |

2026-11-11 新增能力（详见 `references/drama-workflow.md` 末节）：

- **R2V 角色锁定路线**：参考图（定妆照/全身/场景卡）直接驱动生成，20 步 ~17min/镜；`workflow_api_r2v_local.json`（3 参考）与 `workflow_api_r2v_4ref.json`（4 参考，双角色同框）均实测一次入队成功。
- **I2V 首帧锚定路线**：细节最强、体积大一倍；选型规则——有首帧用 I2V，多角色同框或无首帧用 R2V。
- **双角色防串脸**：第二角色放进画面内的屏幕（手机屏里出镜），物理隔离 + Subject-Picture 显式绑定，实测零串脸。
- **两条硬教训**：①一条 prompt 只给一个主导动作，多动作链必时间线滞后漏拍；②H3 生成画面内文字不可靠，改用单个印刷图标并显式禁写文字。

上游：[Rea1Felix/H3-colab-studio](https://github.com/Rea1Felix/H3-colab-studio)（MIT）+ [dseditor/minimax-h3-colab](https://github.com/dseditor/minimax-h3-colab) 笔记本。References 与 `scripts/stitch.sh` 来自上游，本仓补充了 2026-11 实跑验证的规程与坑。

## 目录

- `SKILL.md` — agent 可直接用的技能文件：工作区搭建、prompt 写法、执行与收尾
- `references/drama-workflow.md` — **短剧生产唯一规程**（三段式 prompt、一致性三件套、费用红线、长任务拆分）
- `references/colab-runbook.md` — Colab 会话与模型下载 runbook（浏览器路线）
- `references/mac-runbook.md` — colab CLI 无 UI 路线（手机/终端发起）
- `references/prompt-spec.md` — H3 官方 prompt 结构
- `scripts/` — 全套脚本（排队/轮询/下载/拼接/Drive 上传/411 补丁；`workflow_api_r2v*.json` / `workflow_api_i2v_local.json` 为参考图与首帧路线工作流，`shots.dayi.*.json` / `shots.printer*.json` 为实测分镜样例）

## 核心方法（为什么能省钱出片）

1. **H3 一次生成 = 一个连续镜头**。导演工作在模型外：写分镜 → 每镜一次生成 → 硬切拼接。
2. **一致性三件套**：角色描述逐字复用 + 调色词逐镜复用 + 全片单 seed。
3. **台词原生生成**：台词写进 prompt 由 H3 自己念，嘴型音画同源；外部 TTS 后期替换嘴型对不上。
4. **消灭盲盒抽卡**：错误挡在花钱之前——prompt 层自查、试拍 1 镜过关再批量。
5. **长任务拆短脚本**：queue（即返）/ poll（几秒）/ fetch（下载），断连不影响服务端采样。

## 快速开始

前置：Google AI 订阅（Colab 有单元余额）、本地 ffmpeg。

1. 看懂 `references/drama-workflow.md` 的流程表和 prompt 规范，本地写好 `shots.<剧名>.json`（格式参考 `scripts/shots.example.json`）。
2. 选一条路线：
   - **浏览器路线**：按 `references/colab-runbook.md` 打开 `H3_Basic_ComfyUI.ipynb`，UI 里跑。
   - **CLI 路线（无 UI，推荐）**：装 `google-colab-cli`，先跑 `python3 scripts/patch-411.py`（0.7.5 版有空 POST 411 bug，补丁必打），再按 `references/mac-runbook.md` 执行。
3. 一条会话：装环境下模型 → 试拍 shot1 → 过关后拍完剩余镜头 → `stitch.sh` 拼接 → `ffprobe` 验证 → `drive_upload.py` 归档 → 删 runtime。
4. 费用铁律：**余额 0 即停，绝不购买/按量付费；跑完必删 runtime**（空闲会话也在烧单元）。

## 免责声明

- 消耗的是你自己订阅的 Colab 算力单元，请遵守 Google ToS，量力而行。
- 模型文件（约 58 GiB + 1.96 GB Turbo LoRA）从 HuggingFace 下载，遵守对应模型许可。
- `scripts/drive_upload.py` 需要你自己的 GCP quota project（启用 Drive API），把项目 ID 填进脚本。

## License

MIT（沿用上游许可）。
