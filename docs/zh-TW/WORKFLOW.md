# 工作流程開關 `workflow.ini`

每個人做片的步驟都不一樣：有人只在離峰送任務省點數，有人白天也要多工；有人每集都要直版短影音，有人只做長片；有人上傳完想直接不公開分享，有人一定要先在 Studio 看過。Dreamfab 把這些「會自己做的步驟」做成開關，放在一個小設定檔裡，你決定哪些要打開。

中文 | [English](../en/WORKFLOW.md)

## 三層設定，越後面越優先

| 順序 | 在哪裡 | 用途 |
|---|---|---|
| 1 | 程式內建的預設值 | 沒有任何設定檔時的行為，就是 Dreamfab 原本的做法 |
| 2 | `~/.config/dreamfab/workflow.ini` | **你自己的習慣**，所有系列都套用（環境變數 `DREAMFAB_WORKFLOW` 可以指到別的檔） |
| 3 | `projects/<系列>/workflow.ini` | **某個系列的例外**，只寫這個系列跟平常不一樣的地方 |

`project.py` 和指令列參數永遠最優先，例如 `RENDER["enhance"]`、`SHORTS["layout"]`、`--off-peak`、`--now`、`--privacy`。

這個做法跟 git 的設定一樣：個人設定放在家目錄，專案的例外放在專案資料夾，臨時的改變用指令參數。系列資料夾在 `projects/` 底下，不會進 git，所以每個人的設定互不干擾。

## 有哪些開關

| 開關 | 預設 | 打開或改了會怎樣 |
|---|---|---|
| `credits.off_peak` | `off` | 要花點數的任務只在離峰半價時段（03:00–09:00 台灣時間）送出，其他時間 `aip_runner.py` 會等。要馬上送就加 `--now` |
| `credits.max_parallel` | `1` | 同時跑幾個 AutoIP 任務。多數帳號白天只能 1 個；環境變數 `AIP_MAX` 優先 |
| `explain.shorts` | `on` | 解說：`render.py` 剪完寬版，接著剪直版 Shorts（`project.py` 要有 `SHORTS`）。關掉就只出寬版 |
| `explain.shorts_layout` | `band` | 解說直版的版面（`SHORTS` 沒寫 `layout` 時）：`band` 整張畫在中間、`square` 取中間的正方形 |
| `video.enhance` | `off` | 短劇和 MV：成片用 GPU 超分補幀的 `clips_hd/`（要先跑各線的 `enhance.py`，見 [GPU_ENHANCE.md](GPU_ENHANCE.md)） |
| `youtube.privacy` | `private` | 上傳後的狀態：`private` 私人（在 Studio 看過再公開）、`unlisted` 不公開、`public` 公開。排程發布一定先私人 |
| `youtube.log` | `on` | 上傳程式把每個動作記進上架紀錄 `youtube_log.db`（資源庫的「出貨紀錄」讀它）。手動的 `youtube_log.py add` 不受影響 |

值可以寫 `on`／`off`（也接受 `true`／`false`、`yes`／`no`、`1`／`0`、`開`／`關`）、數字，或列出的選項。

## 怎麼用

```bash
python dreamfab/workflow.py init                          # 產生你自己的設定檔（每個開關都附中英說明）
python dreamfab/workflow.py set credits.off_peak on       # 改一個開關
python dreamfab/workflow.py init projects/我的系列         # 產生一個系列的設定檔（全部先註解掉）
python dreamfab/workflow.py set explain.shorts off projects/我的系列
python dreamfab/workflow.py show projects/我的系列/e01      # 這一集實際會用的值，和是哪個檔設的
```

`show` 的輸出長這樣：

```
credits.off_peak       off       ~/.config/dreamfab/workflow.ini
credits.max_parallel   1         ~/.config/dreamfab/workflow.ini
explain.shorts         on        ~/.config/dreamfab/workflow.ini
explain.shorts_layout  square    ~/.dreamfab/projects/我的系列/workflow.ini
...
```

設定檔就是一般的文字檔，也可以直接打開來改：

```ini
[credits]
off_peak = on          # 只在離峰送
max_parallel = 1

[explain]
shorts = on
shorts_layout = square
```

## 幾個常見的組合

- **省點數優先**：`credits.off_peak = on`。白天跑 `aip_runner.py` 也不會花全價，任務排著等 03:00；真的急就加 `--now`。
- **只做長片**：`explain.shorts = off`。專案裡的 `SHORTS` 留著也沒關係，要剪直版時再用 `render.py P --shorts`。
- **有顯卡、每集都要 60 fps**：`video.enhance = on`，然後在 `project.py` 的 `RENDER` 寫 `fps=60`。舊作品不想被改，就把這個開關寫在新系列的 `workflow.ini`，不要寫在你自己的檔。
- **上傳後直接給朋友看**：`youtube.privacy = unlisted`。

## 給 AI 助理（skill）

Dreamfab 的 skill 在動手前會先跑 `python dreamfab/workflow.py show <這一集>`，照開關決定要不要做直版、要不要等離峰。開關沒打開的自動步驟，AI 不會自己做；要改流程，改設定檔就好，不用每次交代。
