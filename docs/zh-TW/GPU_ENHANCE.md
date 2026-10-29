# 本地 GPU 超分＋補幀（NVIDIA）

中文 | [English](../en/GPU_ENHANCE.md)

在等 AutoIP 生成的時候，用本機的 NVIDIA 顯卡把片段先處理好：

- **超解析度**：放大 2 倍。
- **補幀**：24 → 60 fps。

這套做法已經在 [autoip-drama-maker](https://github.com/autoip/autoip-drama-maker) 上線，程式是 `dramakit/enhance.py`。這份文件整理它的做法、實測數字，以及搬到 mv-maker 時要注意的地方。

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

## autoip-drama-maker 的做法

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

## 搬到 mv-maker 要注意的

- **片段規格**：MV 的片段是 1344×768、24 fps。放大 2 倍是 2688×1536，像素數跟短劇的 1536×2688 一樣，所以速度相同，一顆約 7.5 秒。
- **直式版最受益**：從橫式片段裁直式（`size=(1080, 1920)`＋`focus`），等於高度放大 2.5 倍（768 → 1920）。這時超分的差別比橫式版明顯很多，建議先拿直式版比較。
- **`render_mv.py` 要改的地方**：
  - 片段路徑：`CLIPS = os.path.join(D, "clips")`，以及每一列讀片段的地方，要能改讀 `clips_hd/`。
  - `R["crop"]` 的像素值要乘倍數，`E["crop"]` 合併進來的也一樣。
  - `R["fps"]` 改成 60。
  - 卡點是用秒數換算成影格（`round(t * FPS)`），所以 60 fps 只是對得更細，節拍位置不變。
- **調色**：MV 的 `grade` 預設有 `noise=alls=4:allf=t`（膠片顆粒）。超分會把皮膚磨平，這個顆粒剛好能補回質感，不需要另外處理。
- **舞蹈和對嘴鏡頭**：動作快的鏡頭最容易看出補幀的瑕疵（手、頭髮、裙擺），換鏡頭前先逐格檢查幾顆。
- **畫面風格**：MV 走電影感，60 fps 會變得很「順」，有時像直播或電視。建議先用一首歌做左右對照再決定。
- **GPU 檢查**：`gpu_check.py` 可以加一行，檢查 `import nvvfx` 能不能成功，以及顯卡是不是 RTX 40 或 50 系列。
- **已公開的 MV 不要重做**：YouTube 不能替換影片檔，換版本只能重新上傳，會失去觀看數和留言。

## 還能更快

- **格式轉換改在顯示卡上做**：現在 RGB → YUV 在 CPU 做，佔 2.8 秒。改在顯示卡上做，一顆預估從 7.5 秒降到約 4 秒；搬回記憶體的資料量也減半。
- **補幀改用 `MEDIUM` 模式**：會更快，畫質要另外比較。

## 參考

- [nvidia-vfx Python API](https://docs.nvidia.com/maxine/vfx-python/latest/api.html)
- [NVIDIA Video Frame Generation](https://docs.nvidia.com/maxine/vfx/latest/Filters/VideoFrameGeneration.html)
- [NGC：Video Super Resolution](https://catalog.ngc.nvidia.com/orgs/nvidia/maxine/collections/nvvfxvideosuperres)
- autoip-drama-maker：[`dramakit/enhance.py`](https://github.com/autoip/autoip-drama-maker/blob/main/dramakit/enhance.py)、`render_ep.py` 的 `picture()` 和 `at_scale()`、`common.hd_path()`
