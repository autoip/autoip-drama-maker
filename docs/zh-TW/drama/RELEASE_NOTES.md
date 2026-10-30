# 更新紀錄

中文 | [English](../../en/drama/RELEASE_NOTES.md)

## Dreamfab 0.8.0（2026-10-30）：短劇和 MV 合併成 Dreamfab 造夢廠

autoip-drama-maker 和 autoip-mv-maker 合併成 [Dreamfab](https://github.com/autoip/dreamfab)（AI 自動化媒體工作站），兩邊的歷史都保留，舊網址自動轉址。`project.py` 的格式沒有改。

- **資料夾**：`dramakit/` → `drama/`、`mvkit/` → `mv/`；共用的放進核心 `dreamfab/`：`aip_runner.py`、`credits.py`、`check_public.py`、`gpu_check.py`、`make_static_font.py`、`youtube_api.py`、`youtube_playlists.py`、超分補幀引擎 `enhance.py`、共用函式 `util.py`。新舊路徑對照見 [README](../../../README.md)。
- **影片編碼**：兩條線統一成「ffmpeg 能用 NVENC 就用」，`VENC=x264` 強制用 CPU。MV 線以前預設用 CPU，現在有顯卡就變快，畫質一樣（VMAF 99.2 對 99.3）。
- **runner**：用短劇版（會問伺服器現在是不是離峰；被拒絕的任務內容沒改不會重送），`AIP_OFFPEAK=1` 照樣能用；原價送出時印一行離峰提示。
- **資源庫**：`python dreamfab/library.py serve projects` 一個網頁看所有系列（短劇和 MV），各系列照用自己那條線的資源庫。
- **YouTube**：兩條線共用一個登入，憑證預設改放 `~/.config/dreamfab/`（舊的 `~/.config/autoip-mv-maker/` 照樣讀得到）。
- **安裝**：`~/.dreamfab`、`DREAMFAB_*` 環境變數；`DREAMFAB_LINES=drama` 只裝短劇需要的套件（MV 另外的套件在 `requirements-mv.txt`）。skill 改名 `dreamfab-drama`、`dreamfab-mv`，plugin 改名 `dreamfab`。
- **文件**：共用的 [SETUP.md](../SETUP.md)、[GPU_ENHANCE.md](../GPU_ENHANCE.md)、[CONTRIBUTING.md](../../../CONTRIBUTING.md)；各條線的文件在 `docs/zh-TW/drama/`、`docs/zh-TW/mv/`。以下舊紀錄裡的路徑是當時的寫法。

## 0.1.0（2026-10-27）：第一版

架構沿用 [autoip-mv-maker](https://github.com/autoip/autoip-mv-maker)：一集一個 `project.py`、每一批任務前先看審核圖、可續跑的 runner、ffmpeg 本機合成、Claude Code／Codex skill。改成以劇本和對白為中心：

- **鏡頭**（`storyboard.py`、`make_jobs.py`）：`M` 多參考影片（說話的人用自己的聲音樣本講台詞，嘴型一起生成）、`LS` 對嘴（自己錄的台詞）、`I2V` 圖生影片、`K` 關鍵幀影片。參考圖自動組合（說話的人、`@KEY`、道具、場景）、`@KEY` 換成 `@圖片 N`、每個 SHOT 寫地點、有聲音樣本時拿掉描述裡的性別字眼、台詞長度與點數估算。`make_jobs.py` 每次直接從 `project.py` 重建，沒有要記得先重跑的中間檔。
- **素材**：`make_jobs.py P refs` 生成定裝、場景、道具，也可以從你有的圖延伸（`base`、`base_crop`、`base_box`，多個強度一次出候選）；`voices.py` 把錄音整理成聲音樣本。整部劇共用的素材放上一層資料夾。
- **品管**：`qc/sheets.py jobs`（每個任務的參考圖、台詞、prompt、點數）、`qc/clips.py`（壞檔、換鏡點、有沒有聲音）、`speech.py`（台詞在哪幾秒、有沒有講完、講的是不是劇本那句）。
- **剪輯**（`timeline.py`）：一列一鏡、接在上一列後面；`auto` 依台詞剪；插入列 `^` 只換畫面（反應鏡頭、L/J cut）；`zoom`、`flash`、`black`、`freeze`、`sfx`、`mute`；別集的片段當前情提要；`@name` 貼上另一組剪輯。`edl_draft.py` 產生初剪。
- **合成**（`render_ep.py`）：每列用自己片段的聲音，配樂自動壓在對白下面，音效疊上去，整體 −16 LUFS；直式 1080×1920 預設，可出橫式版；片尾卡選用。
- **字幕與字卡**（`subs.py`）：台詞依標點切段、照逐字時間對上；人物字卡、片名卡、左上標籤、卡點「未完待續」、集數小標。`qc/subprev.py` 只渲字幕預覽。
- **封面**（`thumbkit.py`）：直式 1080×1920，鉤子文案、上下對切、集數標。
- **文件**：WORKFLOW、PROJECT_FORMAT、EDITING（短劇剪輯）、SERIES_PLANNING（整部劇企劃）、PUBLISHING、LESSONS（沿用 MV 的經驗，並列出短劇待實測的項目）、SETUP。
- **劇情去識別化**：repo 裡的示範集、範本與文件只有結構（角色 A／B／C、場景與台詞都是 `<…>` 佔位），具體的劇本、角色與素材只放在 `projects/`（不進 git）。
- 沿用 autoip-mv-maker：`aip_runner.py`、`credits.py`、`make_static_font.py`。

**還沒做**：YouTube 自動上傳與播放清單整理（autoip-mv-maker 的 `youtube_upload.py`、`youtube_playlists.py` 要改成一集一集上傳的版本）、對嘴鏡頭的嘴型品管（`qc/mouth.py`）、橫式素材裁直式的臉部定位（`qc/focus.py`）。
