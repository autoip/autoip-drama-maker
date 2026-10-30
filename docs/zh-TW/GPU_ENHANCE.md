# 本地 GPU 超分＋補幀（NVIDIA）

中文 | [English](../en/GPU_ENHANCE.md)

在等 AutoIP 生成的時候，用本機的 NVIDIA 顯卡把片段先處理好：

- **超解析度**：放大 2 倍。
- **補幀**：24 → 60 fps。

短劇線（`drama/enhance.py`）和 MV 線（`mv/enhance.py`）共用同一個引擎 `dreamfab/enhance.py`；各條線只決定自己的剪輯用到哪些片段。**這是選用功能，預設不跑**：沒設定時合成照舊用原片段，CPU 環境也不用裝 `nvidia-vfx`。這份文件整理做法、實測數字，以及在 MV 上要注意的地方。

## 用什麼

| 功能 | 工具 | 速度（RTX 5060 Ti 16 GB 實測） | 效果 |
|---|---|---|---|
| 超解析度 2 倍 | NVIDIA Video Super Resolution（`nvidia-vfx` 的 `VideoSuperRes`，畫質 `ULTRA`） | 每格 6.4 ms | 清掉壓縮方塊、招牌邊緣變乾淨；皮膚變平滑，毛孔顆粒少一些；縮回 1080 之後銳利度差別不大 |
| 補幀 24 → 60 fps | NVIDIA Video Frame Generation（`VideoFrameGeneration.run_at_timestep`，模式 `HIGH`） | 每張中間格約 13 ms | 動作和推鏡明顯變順；快速揮手沒看到多手指或殘影 |
| 解碼、格式轉換、編碼 | PyAV＋`hevc_nvenc` | 一顆約 4.3 秒（CPU 的 RGB → YUV 轉換佔 2.8 秒） | — |
| **一顆 5 秒片段合計** | | **約 7.5 秒** | AutoIP 一顆要等約 3 分鐘，處理在等待時間內做完 |

## 安裝

- **硬體與驅動**：需要 RTX 顯卡，補幀要 RTX 40 或 50 系列，Windows 驅動要 570.65 以上。
- **Python 套件**：環境裡要有有 CUDA 的 PyTorch 和 PyAV（`pip install av`）。
- **`nvidia-vfx`**：
  - 執行 `pip install nvidia-vfx`。PyPI 上只是一個殼（wheel-stub），真正的套件從 `pypi.nvidia.com` 下載，Windows 版約 436 MB，自帶需要的 NVIDIA 函式庫（NPP、NGX）。
  - 這個 wheel 沒有宣告任何相依套件，可以用 `--no-deps` 裝進現有環境，沿用已經裝好的 PyTorch，不用另外下載一份。
- **授權**：NVIDIA 專有授權，模型在 NGC 上標示可商用。NVIDIA 的範例程式（[nvidia-vfx-python-samples](https://github.com/NVIDIA-Maxine/nvidia-vfx-python-samples)）是 MIT 授權。

```python
import torch
from nvvfx import VideoSuperRes, VideoFrameGeneration
sr = VideoSuperRes(quality=VideoSuperRes.QualityLevel.ULTRA)
sr.output_width, sr.output_height = 2688, 1536; sr.load()           # 輸入 (3, H, W) float32 0–1，在 CUDA 上
fg = VideoFrameGeneration(mode=VideoFrameGeneration.Mode.HIGH)
fg.input_width, fg.input_height = 2688, 1536; fg.frame_multiplier = 3; fg.load()
mid = torch.from_dlpack(fg.run_at_timestep(prev, cur, 0.4).image).clone()   # 輸出指向 SDK 的記憶體，要馬上 clone
```

## 做法（以短劇線為例）

1. **片段 → `clips_hd/`**：
   - `enhance.py P` 對每顆片段做超分 2 倍＋補幀到 60 fps，存成 `clips_hd/<id>.mp4`。只存畫面，聲音照樣取原片段。
   - 重拍留在 `clips/_takes/` 的舊版也會處理，放到 `clips_hd/_takes/`。
2. **剛好 2 倍**：
   - `RENDER["crop"]` 裡 `crop=`、`delogo=` 的像素值，合成時自動乘 2；`iw*0.8` 這種運算式不動。
   - 不放大成任意尺寸，是因為這些像素值只有整數倍才換算得準。
3. **補幀用時間位置，不用倍數**：
   - 輸出第 k 格對應原片段第 `k × 24 / 60` 格的位置，落在兩格之間就用 `run_at_timestep(前一格, 後一格, 小數部分)` 生出來。24 → 60 是 2.5 倍，不能用整數倍數。
   - 最後幾格停在最後一張，讓處理後的長度跟原片段一樣。
   - 片段裡面如果有換鏡，`automatic_shot_change_detection_enabled` 預設開著，會自己處理。
4. **什麼時候重做**：`clips_hd/<id>.mp4.json` 記著用了哪些參數（fps、scale、quality）。片段比副本新（重拍過）或參數改了，就重做。
5. **`--watch`**：跟 runner 同時跑。每輪先跳過 20 秒內還在變動的檔案（runner 可能還在寫入），讀不了的下一輪再試；全部任務都有片段、也都處理完就自己結束。
6. **合成**：
   - `RENDER` 加 `fps=60, enhance=True`，畫面就改用 `clips_hd/`；沒有副本的片段照用原片段，並印出提醒。
   - 單一個剪輯可以帶自己的 `render=dict(...)` 蓋過 `RENDER`，例如同一個剪輯另出一版 60 fps 來比較。
7. **已公開的不重做**：已經用 25 fps 上傳的不重新上傳。合集如果想全部用 60 fps，就給每集另外出一版 `_hd60`，合集設定寫 `episode_suffix="_hd60"`。

## 在 MV 線使用（選用）

```bash
python mv/enhance.py P               # project.EDITS 用到的片段 → clips_hd/<id>.mp4；加 --watch 可以跟 runner 同時跑
python mv/render_mv.py P full_hd60   # 用增強副本渲的對照版
```

在 `project.py` 加對照用的剪輯，沿用原本的剪輯表，只換渲染設定：

```python
HD60 = dict(fps=60, enhance=True)
EDITS["full_hd60"] = dict(EDITS["full"], suffix="_hd60", render=HD60)
EDITS["shorts_hd60"] = dict(EDITS["shorts"], suffix="_1min_shorts_hd60", render=HD60)
```

- **`enhance.py`**：做法跟短劇線一樣（同一個引擎），包括超分 2 倍、照時間位置補幀，以及最後幾格停在最後一張。
  - **什麼時候重做**：參數記在 `clips_hd/<id>.mp4.json`，片段比副本新（重做過）或參數改了就重做。
  - **`--watch`**：等 `jobs/*.json` 裡寫進 `clips/` 的任務都下載完、副本也都做完才結束。
  - **載入模型**：只在片段尺寸改變時重新載入（關鍵幀是 1280×704，其他是 1344×768），所以會先照尺寸排序。
  - `ONLY=B05,M02` 只做這幾段。
- **`render_mv.py`**：剪輯的 `render=dict(...)` 會蓋過 `RENDER`。
  - `enhance=True` 時，每一列改讀 `clips_hd/` 裡比片段新的副本；沒有副本的照用原片段，並印出提醒。
  - `crop` 濾鏡裡 `crop=`、`delogo=` 的像素值會自動乘倍數。
  - 對嘴列照 `align.json` 用秒數對齊，不受影響。
  - 卡點是秒數換算成影格，60 fps 只是對得更細，節拍位置不變。
- **`gpu_check.py`**：多印一行 `hd`，說明能不能跑、還缺什麼。

### 一支 MV 的實測

一支金箔工筆畫風的 MV，70 段片段，RTX 5060 Ti 16 GB：

| 項目 | 結果 |
|---|---|
| 超分＋補幀 70 段 | 16 分鐘、1.1 GB。5 秒的片段平均 11 秒，比短劇的 7.5 秒慢；8–10 秒的片段 14–29 秒；第一段含載入模型約 20 秒 |
| 渲 60 fps | 直式 1 分鐘版 40 秒，3 分鐘的完整版 2 分鐘 |
| 直式版 | 明顯變清楚：壓縮方塊不見，睫毛、唇線、皺紋、刺繡線條變清楚；皮膚變平滑 |
| 橫式版 | 縮回 1080 之後幾乎看不出差別 |
| 補幀 | 打鬥、舞刀逐格看，沒有多手指或殘影，只有原片本來就有的動態模糊 |
| 決策者的決定 | 「太利、少了藝術感」→ 成品用原版 25 fps，增強留著當選項 |

畫風偏繪畫、走電影感的 MV，多出來的銳利和 60 fps 的順暢反而會沖淡畫感。先用一首歌做左右對照，讓決策者看過再決定，不要預設開啟。

### 要注意的

- **直式版最受益**：從橫式片段裁直式（`size=(1080, 1920)`＋`focus`），等於高度放大 2.5 倍（768 → 1920），超分的差別比橫式版明顯很多。要比較就先比直式版。
- **調色**：MV 的 `grade` 預設有 `noise=alls=4:allf=t`（膠片顆粒）。超分會把皮膚磨平，這個顆粒能補回一點質感，但補不回畫感。
- **舞蹈和對嘴鏡頭**：動作快的鏡頭最容易看出補幀的瑕疵（手、頭髮、裙擺），換成增強版前先逐格檢查幾段。
- **空間**：副本是 2 倍大的 HEVC，一支 MV 約 1 GB。`clips_hd/` 跟 `clips/` 一樣不進 git。
- **已公開的 MV 不要重做**：YouTube 不能替換影片檔，換版本只能重新上傳，會失去觀看數和留言。

## 還能更快

- **格式轉換改在顯示卡上做**：現在 RGB → YUV 在 CPU 做，佔 2.8 秒。改在顯示卡上做，一顆預估從 7.5 秒降到約 4 秒；搬回記憶體的資料量也減半。
- **補幀改用 `MEDIUM` 模式**：會更快，畫質要另外比較。

## 參考

- [nvidia-vfx Python API](https://docs.nvidia.com/maxine/vfx-python/latest/api.html)
- [NVIDIA Video Frame Generation](https://docs.nvidia.com/maxine/vfx/latest/Filters/VideoFrameGeneration.html)
- [NGC：Video Super Resolution](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/collections/nvvfxvideosuperres)
- 共用引擎：`dreamfab/enhance.py`；`dreamfab/util.py` 的 `hd_path()`
- MV 線：`mv/enhance.py`、`render_mv.py` 的 `picture()` 和 `at_scale()`、`dreamfab.util.hd_path()`
- 短劇線：[`drama/enhance.py`](https://github.com/autoip/dreamfab/blob/main/drama/enhance.py)、`render_ep.py` 的 `picture()` 和 `at_scale()`、`dreamfab.util.hd_path()`
