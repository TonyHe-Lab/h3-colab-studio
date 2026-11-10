# H3 短剧工作流 v1（2026-11-11，源自 X 调研 + 本地已验证管线）

来源：X 调研（@Delroy715 / @gaoyy9 / @0xKevin00 / ComfyUI-H3-Continuity-Studio）+ 本仓
2026-11-10 实跑记录（宇航猫 3 镜，A100，10.4 单元）。本文档是短剧生产的唯一操作规程。

## 核心认知（X 共识，已验证或高置信）

1. **H3 一次生成 = 一个连续镜头**。导演工作在模型外：写分镜 → 每镜一次生成 → 硬切拼接。
2. **消灭盲盒抽卡是最大省钱**。不要砍分辨率/步数换速度——抽 20 次废片比一次 3 分钟无损采样贵得多。
3. **一致性三件套**：角色描述逐字复用 + 调色词复用 + 全片单 seed。这是跨片段"像一部片"的全部秘密。
4. **台词原生生成**：H3 是音视频联合模型，台词写进 prompt 由 H3 自己念，嘴型音画同源；
   外部 TTS 后期替换=嘴型对不上（不可用），TTS 干声回喂=朗读腔重。拒绝外部 TTS。
5. **错误挡在花钱之前**：文字里能发现的错不留到图上，图上能发现的错不留到视频上。
   每镜提交前自查 prompt；新开"审核视角"重读一遍再排队。

## Prompt 规范（三段式，英写中台）

每镜 prompt = `integrated_multimodal_description` 正文 + `overall_soundscape` + `non_diegetic_music` 三段，
作为整段文本填入 prompt 节点：

- **正文**：`Wide establishing shot:` / `Close-up shot:` / `Two-shot:` 等景别标签开头；
  角色锚点（外貌+服装）逐字复用；调色词（warm amber / cool blue night / rain / steam / photorealistic, cinematic）逐镜复用；
  运镜写"方式+幅度+速度"；单镜单场景单动作；结尾 `single continuous take, no cuts`。
- **台词**：写 `says warmly in Mandarin Chinese (S1): "…"`，说话人标 (S1)/(S2)，中文台词直接写。
  情绪爆发 = 台词前加副语言前缀（slams his palm and shouts furiously）+ soundscape 写 0.x 秒物理重音锚点。
- **soundscape**：环境音 + 拟音逐项写，有台词的镜把台词环境交代清楚。
- **music**：非剧情音乐一行，注明音量层次（low in the mix）。

## 生产流程（本地备料 → 一条会话跑完 → 验完即关）

| 阶段 | 动作 | PASS 判据 |
|---|---|---|
| 0 备料（本地，0 单元） | 剧本→3-5 镜分镜表；写 shots.<剧名>.json（复用 shot 覆盖结构：prompt/seed/前缀/分辨率/时长）；本地重读一遍 prompt 自查 | 分镜齐、seed 单一、锚点逐字一致 |
| 1 会话 | `colab new -s <名> --gpu G4`，分不到→A100 不硬等 | status READY，记录实际卡型 |
| 2 环境 | upload 3 件套（workflow_api_t2v_local.json / shots.json / h3_*.py）→ `colab exec -f h3_setup.py`（background 跑） | READY + 5 个 MODEL size_ok=true |
| 3 试拍（最小案例） | 只拍 shot1：queue→poll→fetch→本地看片 | 质量过关才继续；卡住停在瓶颈报卡点 |
| 4 批量 | 同会话拍余下镜，每镜完成立即 download 落本地 | 每镜 saved + 字节 >1MB |
| 5 后期 | stitch.sh 硬切拼接 → ffprobe 验证（分辨率/时长/音轨） | 全部符合预期 |
| 6 归档 | drive_upload.py 传 Drive 核对字节 → `colab stop` → sessions 空 + usage 0 | DRIVE_OK + 余额入账 |

## 费用红线（违反即停）

- 只用自己 Google AI 订阅赠送的单元；**余额 0 即停**，绝不购买/按量付费。
- 单次运行后必断会话删 runtime；空闲会话也在烧单元，报错卡住先 stop 止损。
- 参考：A100 8.88 单元/小时；3 镜 15s 含环境 ~10 单元；G4 ~8.9/小时。

## 长任务与坑（全部实测，勿再踩）

- exec 长连接 >10 分钟必断：拆 queue（即返）/ poll（几秒）/ fetch（下载）三短脚本，服务端跑不受断连影响。
- 长安装用 `terminal(background=true)` 跑 colab exec，不轮询 >3 分钟。
- 本地模板用 `video_minimax_h3_t2v.json` 导出的 API JSON；`api_minimax_h3_t2v.json` 是付费 API 节点，**禁用**。
- 环境：comfy-aimdo 必须随 requirements 一起装；A100 全 GPU 解码，**不要加 --cpu-vae**。
- SaveVideo 的 format 必须是 mp4，空值=白跑一镜。
- 411=补丁丢失，重打；G4 无货报 Service Unavailable，直接换 A100。
- HF 体积是十进制 GB，校验阈值 0.9 或按字节比。
- 片长注意：124 帧 @24fps = 5.17s/镜（模板帧栅格对齐），拼 3 镜 ≈ 15.5s。

## 2026-11-11 练手短剧《白熬了》新验证事实

- **10s/镜 + 9:16 已跑通**：`140:133.inputs.value: 10.0` + `115.inputs.aspect_ratio: "9:16 (Portrait Widescreen)"`（枚举值经 /object_info 实测，不是 "9:16 (Portrait)"），megapixels 1.0 → 768x1376，输出 10.125s/镜，3 镜成片 30.4s。
- **A100-40GB 可用**（gpu-a100-s 档，39.5GiB）：int8 全套跑通无 OOM，未加 --cpu-vae。10s 竖屏采样 ~19-23 分钟/镜（比 80GB 慢）。
- **3 镜 30s 竖屏总消耗 8.32 单元**（含环境装 ~15min + 孤儿会话误烧），采样占约 5.5 单元。
- **孤儿会话清理**：CLI 重试超时会在服务端留下无本地记录的 assignment（`colab sessions` 显示 `[?]`，stop 找不到）。解法：用 CLI 自带 python 直接调 `client.unassign(endpoint)`（只需 endpoint 字符串，来自 list_assignments）。教训：批量重试 `colab new` 时串行且限时，别并发。
- **Drive 上传 >10MB 文件 multipart 会写超时**，改 resumable（session URI + PUT）稳定；脚本 `drive_upload_resumable.py` 模式已验证（10.8MB 一次成功）。
- **定妆照路线**：Gemini 3.1 Flash Image（8317 代理，AI Pro 额度，0 CCU）出角色定妆照可行；但 T2V 工作流不吃参考图，一致性仍靠锚点逐字复用+单 seed（实测跨镜服装/场景/人物一致性良好）。

## 升级路线（未验证，待做）

- 单段热修：潜变量断点 `--only-seg`（Delroy715 方案，需 ComfyUI 多段续接工作流）。
- 多镜头视觉记忆：KadoBOT/ComfyUI-H3-Continuity-Studio（五帧 latent 记忆，跨镜房间/服装不漂）。
- 定妆照锚定：本地生图出角色三视图 → Ref2VA/I2V 模式（six-section prompt + `<d>` 台词标签）。
- 后期字幕：ffmpeg + 声学包络对齐（auto_subtitle 思路）。
