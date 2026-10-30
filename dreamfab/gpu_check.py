"""What an NVIDIA GPU on this machine can take over, and the flags or installs that switch each step to it.

usage: python dreamfab/gpu_check.py
What each Dreamfab line (drama, mv, ...) can hand to the GPU. Encoding switches by itself when ffmpeg can use NVENC;
the rest needs a flag or an install. Measured on an RTX 5060 Ti 16 GB with a
16-thread CPU (2026-10): ASR 10x, final encode 4x, segment encode 2x, demucs 1.5x; MediaPipe stays on the CPU.
"""
import importlib.util, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run as a script: the repo root
from dreamfab.util import nvenc_ok

try:
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
except FileNotFoundError:
    smi = gpu = ""
if not gpu:
    sys.exit("no NVIDIA GPU found: everything runs on the CPU (the default), nothing to change")
cuda = re.search(r"CUDA (?:UMD )?Version:\s*([\d.]+)", smi)
cuda = cuda.group(1) if cuda else "?"
print(f"GPU    {gpu}, CUDA {cuda}")
flags = []

if nvenc_ok():
    print("encode yes  renders encode on the GPU by themselves (final 4x faster, VMAF 99.2 vs 99.3); VENC=x264 forces the CPU")
else:
    print("encode no   this ffmpeg build cannot use NVENC here: it needs a newer GPU driver (or an older ffmpeg)")

try:
    import ctranslate2
    n = ctranslate2.get_cuda_device_count()
except ImportError:
    n = 0
libs = all(importlib.util.find_spec(m) for m in ("nvidia.cublas", "nvidia.cudnn")) if os.name == "nt" else True
if n and libs:
    print("asr    yes  ASR_DEVICE=cuda: audio/asr_words.py on the GPU (about 10x)")
    flags.append("ASR_DEVICE=cuda")
elif n:
    print('asr    yes after: pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10", then ASR_DEVICE=cuda')
else:
    print("asr    no   ctranslate2 sees no CUDA device")

try:
    import torch
    if torch.cuda.is_available():
        print("demucs yes  torch has CUDA: python -m demucs uses the GPU by itself (about 1.5x incl. model load)")
    else:
        idx = "cu130" if cuda[:2].isdigit() and int(cuda.split(".")[0]) >= 13 else "cu128"
        print(f"demucs no   torch {torch.__version__} is a CPU build; for the GPU: pip install "
              f"torch=={torch.__version__.split('+')[0]} --index-url https://download.pytorch.org/whl/{idx}")
except ImportError:
    print("demucs -    torch is not installed")

rtx = re.search(r"RTX\s*(\d)0\d0", gpu)
try:
    import nvvfx  # noqa: F401
    vfx = True
except Exception:
    vfx = False
if vfx and rtx and int(rtx.group(1)) >= 4:
    print("hd     yes  drama/enhance.py or mv/enhance.py: 2x super resolution + 60 fps frame generation into clips_hd/, then an edit with "
          "render=dict(fps=60, enhance=True) (docs GPU_ENHANCE.md)")
elif vfx and rtx:
    print("hd     half nvidia-vfx is here, but frame generation needs an RTX 40 / 50 card: run enhance.py with --fps 24")
elif rtx:
    print("hd     yes after: pip install nvidia-vfx --no-deps (about 436 MB from pypi.nvidia.com), then drama/enhance.py or mv/enhance.py")
else:
    print("hd     no   NVIDIA super resolution / frame generation need an RTX card")
print("faces, mattes, mouth/zoom QC: CPU (MediaPipe's pip builds have no GPU on Windows)")
print("suggested:", " ".join(flags) if flags else "nothing (keep the CPU defaults)")
