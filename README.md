# autoip-drama-maker：AI 短劇製作管線

中文 | [English](README.en.md)

把劇本做成直式短劇的半自動流程。一集 1–2 分鐘：

- 固定的角色造型與聲音：每個角色用自己的聲音樣本講台詞，嘴型一起生成
- 依台詞剪輯：正反打、反應鏡頭、L/J cut、爽點推近加音效、卡點定格「未完待續」
- 台詞字幕、人物字卡、片名卡；配樂自動壓在對白下面
- 直式封面、標題、說明欄；整部劇的企劃框架

影像與語音生成使用 [AutoIP](https://autoip.ai) 公開 API：多參考影片（角色、場景、道具參考圖＋台詞＋聲音樣本）、對嘴、圖生影片、關鍵幀影片、文生圖、圖生圖。剪輯、字幕、混音與合成全部在本機用 ffmpeg + libass 完成。

架構沿用 [autoip-mv-maker](https://github.com/autoip/autoip-mv-maker)：一集一個 `project.py`、每一批任務送出前先看審核圖、可續跑的 runner。

## 一句話做出一集短劇

裝好之後（安裝方式見下方），在 Claude Code 或 Codex 裡說：

```text
用 autoip-drama-maker 把 劇本.md 做成短劇
```

agent 會照流程一步一步做。**每一批任務送出前，都會先給你看審核圖、報點數**，你點頭才會送出。

要做一整部劇：

```text
用 autoip-drama-maker 規劃一部 30 集的短劇：<題材>
```

agent 會先問你題材、爽點引擎、篇章和想固定的錨點，寫好整部劇的企劃（`plan.md`）、人物設定（`characters.md`）和風格聖經（`style.md`）給你確認，再一集一集做。框架有公式，故事和風格全部由你決定。方法見 [SERIES_PLANNING.md](docs/zh-TW/SERIES_PLANNING.md)。

## 一行安裝（Claude Code / Codex）

**macOS / Linux / Git Bash：**

```bash
curl -fsSL https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.sh | bash
```

**Windows PowerShell：**

```powershell
irm https://raw.githubusercontent.com/autoip/autoip-drama-maker/main/install.ps1 | iex
```

安裝程式會把工具裝到 `~/.autoip-drama-maker`（含 Python 虛擬環境），skill 會同時裝進 Claude Code 和 Codex。

也可以改用 plugin 安裝：

```bash
claude plugin marketplace add autoip/autoip-drama-maker && claude plugin install autoip-drama-maker@autoip-drama-maker
codex plugin marketplace add autoip/autoip-drama-maker && codex plugin add autoip-drama-maker@autoip-drama-maker
```

還需要自己準備：
- **ffmpeg**（含 libass）
- **字型**
- **AutoIP API key**：放在環境變數 `AUTOIP_API_KEY`，不要寫進任何檔案。
- **聲音樣本**：每個角色一段 5–15 秒、你有權使用的聲音。

詳見 [docs/zh-TW/SETUP.md](docs/zh-TW/SETUP.md)。

## 特色

- **一個 `project.py` 就是一集**：角色、場景、道具、場次、鏡頭、台詞、剪輯表、配樂、字幕主題都寫在這裡，其餘檔案都由它產生。
- **先看圖再花點數**：定裝、場景、首幀先出靜圖審核；影片任務先出審核表（每個任務的參考圖、台詞、prompt、點數）；每個角色先試拍一顆，聽過聲音才整批送。
- **一顆鏡頭一個人說話**：多參考影片帶說話者的聲音樣本，台詞和嘴型一起生成；對話用正反打剪出來。
- **prompt 自動組好**：參考圖自動組合（說話的人、`@KEY`、道具、場景），`@KEY` 換成 `@圖片 N`，每個 SHOT 都寫地點（不會掉進灰色攝影棚），有聲音樣本時拿掉描述裡會蓋過音色的性別字眼，台詞超過每秒 4 字就警告。
- **台詞品管**：語音辨識檢查每句台詞有沒有講完、講的是不是劇本那句；壞檔、片段內的換鏡點、有沒有聲音一次列出來。
- **依台詞剪輯**：剪輯表一列一鏡，`auto` 照台詞剪掉前後空白；插入列只換畫面不換聲音，反應鏡頭與 L/J cut 一行寫完；`zoom`、`sfx=hit`、`flash`、`freeze`、`end`；別集的片段直接當前情提要。
- **混音**：每一鏡用自己的對白與音效，配樂自動避讓對白，整體 −16 LUFS。
- **字幕與字卡**：台詞依標點切段、照逐字時間對上；人物字卡、片名卡、左上標籤、卡點文字。

## 手動使用

```bash
git clone https://github.com/autoip/autoip-drama-maker && cd autoip-drama-maker
python -m venv venv && venv/Scripts/activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
export AUTOIP_API_KEY=aip_xxx                       # 在 AutoIP 儀表板申請；不要寫進任何檔案
mkdir -p projects/my_drama && cp -r examples/demo projects/my_drama/s1e01_pilot   # projects/ 已被 .gitignore 排除
# 放入角色圖或寫 prompt、聲音樣本、配樂、音效、fonts/，編輯 project.py
```

接著照 [docs/zh-TW/WORKFLOW.md](docs/zh-TW/WORKFLOW.md) 一步一步做。從劇本到上架共 12 個步驟，每一步都附指令和審核點。

## 文件

| 文件 | 內容 |
|---|---|
| [SETUP.md](docs/zh-TW/SETUP.md) | 安裝：一行安裝、Python 套件、ffmpeg、字型、API key、素材權利 |
| [WORKFLOW.md](docs/zh-TW/WORKFLOW.md) | 完整流程：劇本 → 定裝 → 聲音 → 分鏡 → 首幀 → 試拍 → 影片 → 品管 → 剪輯 → 字幕與聲音 → 合成 → 上架 |
| [PROJECT_FORMAT.md](docs/zh-TW/PROJECT_FORMAT.md) | `project.py` 每個欄位、剪輯表的寫法 |
| [EDITING.md](docs/zh-TW/EDITING.md) | 短劇剪輯心法：鉤子、正反打、反應鏡頭、節奏、爽點、卡點 |
| [SERIES_PLANNING.md](docs/zh-TW/SERIES_PLANNING.md) | 整部劇的企劃：一句話、爽點引擎、每集結構、篇章與大揭露、角色與聲音、包裝 |
| [PUBLISHING.md](docs/zh-TW/PUBLISHING.md) | 封面、標題、說明欄、合集、平台規格 |
| [LESSONS.md](docs/zh-TW/LESSONS.md) | 踩過的坑與解法（沿用 MV 的經驗），以及短劇待實測的項目 |
| [RELEASE_NOTES.md](docs/zh-TW/RELEASE_NOTES.md) | 更新紀錄 |

英文版在 [docs/en/](docs/en/)。

## 目錄

```
dramakit/
  common.py            專案載入、EDL 解析、ffmpeg 小工具、點數估算
  storyboard.py        project.py -> 每顆鏡頭要送給 AutoIP 的東西（參考圖、prompt、台詞、聲音）+ 警告
  make_jobs.py         產生 AutoIP 任務檔：refs（定裝、場景、道具）/ kf（首幀）/ video（M、LS、I2V、K）
  aip_runner.py        送出、輪詢、下載（可續跑、預設一次一個）
  credits.py           每個任務資料夾實際花了多少點數
  voices.py            錄音 -> 聲音樣本
  speech.py            台詞在片段的哪幾秒、有沒有講完（faster-whisper）
  timeline.py          剪輯表 -> 每一列在整集的哪幾秒（render、預覽、初剪共用）
  edl_draft.py         照劇本順序、剪到台詞前後的初剪
  render_ep.py         剪輯表 -> 畫面 -> 對白 + 配樂避讓 + 音效 -> 字幕 -> 成品 mp4 + srt
  subs.py              台詞字幕、人物字卡、片名卡、標籤、卡點文字（ASS）
  endcard.py           片尾字卡（文字＋按鈕，背景是最後一格模糊壓暗）
  compile.py           合集：好幾集（拿掉片尾卡）＋銜接卡＋其他影片 -> 一支 mp4、合併字幕、YouTube 章節
  thumbkit.py          直式封面工具
  make_static_font.py  可變字型 -> 靜態字重（libass 用）
  qc/                  sheets（審核圖、任務審核表）/ clips（壞檔、換鏡點）/ subprev（字幕預覽）
skills/                Claude Code / Codex skill
examples/demo/         去識別化的示範集：只有結構、沒有劇情（project.py、covers.py）
examples/series_template/  空白的整部劇範本（plan.md、style.md、characters.md、每集骨架）
docs/zh-TW/, docs/en/  文件（中文 / 英文）
install.sh, install.ps1                    一行安裝
.claude-plugin/, .codex-plugin/            plugin 與 marketplace 設定
```

## 注意事項

- 生成會消耗 AutoIP 點數，送出即扣、沒有取消 API。正式送影片任務前務必先看審核圖、先試拍。
- 本專案不附任何角色圖、聲音、配樂、字型或生成素材。請使用你有權使用的素材（尤其是聲音樣本），不要用真實公眾人物的臉或聲音，並遵守各平台對 AI 生成內容的揭露規定。
- repo 裡的範例只有結構，沒有劇情；你的劇本、角色與素材都放在 `projects/`（不進 git）。

## 授權

[MIT](LICENSE)
