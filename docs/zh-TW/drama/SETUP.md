# 安裝補充：短劇

中文 | [English](../../en/drama/SETUP.md)

安裝、Python 環境、顯卡、AutoIP API key 和離峰半價、YouTube 登入都見共用的 [SETUP.md](../SETUP.md)。這裡只寫短劇線另外要的東西。

## 1. Python 套件

- `requirements.txt` 就夠了（只做短劇的話，一行安裝設 `DREAMFAB_LINES=drama`）。
- `faster-whisper` 給 `drama/speech.py` 用：台詞的逐字時間、檢查台詞有沒有講完。第一次執行會下載 `medium` 模型到使用者快取。沒裝的話 `speech.py` 改用靜音偵測，只抓得到台詞的起訖。
- **選用：`mediapipe`**（0.10 以上）：`drama/restage.py` 把定裝圖的人去背貼進場景時要用，第一次會下載人像分割模型到 `~/.cache/dreamfab/`。裝了 MV 線就已經有。
- **選用：本地超分＋補幀**（`drama/enhance.py`）：見 [GPU_ENHANCE.md](../GPU_ENHANCE.md)，用法在 [WORKFLOW.md](WORKFLOW.md) 第 7 節。

## 2. 字型

字型不隨專案發布，請自行下載後放進這一集或這部劇的 `fonts/`（合成會先找這一集，再找上一層）。

| 用途 | 建議 | 備註 |
|---|---|---|
| 台詞、人物字卡、片名卡 | Noto Sans TC（思源黑體），取 Black 或 Bold 字重 | SIL OFL |

**libass 只會用可變字型的預設字重。** 要粗體，先切出靜態字重，再取一個新的家族名稱：

```bash
python dreamfab/make_static_font.py NotoSansTC-VF.ttf 900 "DK Sans Black" projects/<劇名>/fonts/DKSansBlack.ttf
```

接著在 `project.py` 設定 `TYPO = dict(font="DK Sans Black", ...)`。封面（`drama/thumbkit.py`）用同一個字型檔。
