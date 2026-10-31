# Workflow switches `workflow.ini`

Everyone makes videos their own way: some submit jobs only off-peak to save credits, some run several at once by day; some want a vertical Short with every explainer, some only the long cut; some share an upload straight away as unlisted, some always check it in Studio first. Dreamfab turns each of these automatic steps into a switch in a small settings file, and you decide which are on.

[中文](../zh-TW/WORKFLOW.md) | English

## Three layers, the later one wins

| Order | Where | For |
|---|---|---|
| 1 | the built-in defaults | what happens with no settings file at all: Dreamfab's own way |
| 2 | `~/.config/dreamfab/workflow.ini` | **your habits**, for every series (`DREAMFAB_WORKFLOW` names another file) |
| 3 | `projects/<series>/workflow.ini` | **one series' exceptions**: only what that series does differently |

`project.py` and command-line flags always win: `RENDER["enhance"]`, `SHORTS["layout"]`, `--off-peak`, `--now`, `--privacy`.

It works like git's config: personal settings in your home folder, a project's exceptions in its folder, a one-off change on the command line. Series folders live under `projects/`, which git ignores, so nobody's settings get in anyone else's way.

## The switches

| Switch | Default | When on or changed |
|---|---|---|
| `credits.off_peak` | `off` | credit jobs are submitted only in the half-price window (03:00-09:00 Taiwan time); outside it `aip_runner.py` waits. `--now` submits anyway |
| `credits.max_parallel` | `1` | AutoIP tasks in flight at once. Most accounts allow one by day; `AIP_MAX` wins |
| `explain.shorts` | `on` | explainers: `render.py` cuts the vertical Short after the episode (when `project.py` has `SHORTS`). Off: the episode alone |
| `explain.shorts_layout` | `band` | the Short's layout when `SHORTS` has none: `band` (the whole picture) or `square` (its middle square) |
| `video.enhance` | `off` | drama and MV: render from the GPU-enhanced `clips_hd/` copies (run that line's `enhance.py` first, see [GPU_ENHANCE.md](GPU_ENHANCE.md)) |
| `youtube.privacy` | `private` | what an upload starts as: `private` (check it in Studio, publish there), `unlisted` or `public`. A scheduled upload is always private first |
| `youtube.log` | `on` | the uploaders record every step in the publishing log (table `youtube_log` of the shared database `dreamfab.db`; the library's shipping log reads it). `youtube_log.py add` by hand still writes |

Values: `on`/`off` (also `true`/`false`, `yes`/`no`, `1`/`0`, `開`/`關`), a number, or one of the listed choices.

## Use

```bash
python dreamfab/workflow.py init                          # start your own file (every switch explained, Chinese and English)
python dreamfab/workflow.py set credits.off_peak on       # change one switch
python dreamfab/workflow.py init projects/my-series       # start a series file (everything commented out)
python dreamfab/workflow.py set explain.shorts off projects/my-series
python dreamfab/workflow.py show projects/my-series/e01   # the values this episode gets, and the file that set each
```

`show` prints:

```
credits.off_peak       off       ~/.config/dreamfab/workflow.ini
credits.max_parallel   1         ~/.config/dreamfab/workflow.ini
explain.shorts         on        ~/.config/dreamfab/workflow.ini
explain.shorts_layout  square    ~/.dreamfab/projects/my-series/workflow.ini
...
```

The file is plain text; edit it directly if you like:

```ini
[credits]
off_peak = on          # submit off-peak only
max_parallel = 1

[explain]
shorts = on
shorts_layout = square
```

## Common setups

- **Credits first**: `credits.off_peak = on`. Running `aip_runner.py` by day never pays full price; the jobs wait for 03:00. `--now` when it cannot wait.
- **Long cuts only**: `explain.shorts = off`. A `SHORTS` in project.py can stay; `render.py P --shorts` cuts the Short when you want one.
- **A GPU and 60 fps every episode**: `video.enhance = on`, plus `fps=60` in project.py's `RENDER`. To leave finished work as it is, put the switch in the new series' `workflow.ini`, not in yours.
- **Share uploads straight away**: `youtube.privacy = unlisted`.

## For the AI assistant (skills)

Dreamfab's skills run `python dreamfab/workflow.py show <episode>` before they start and follow the switches: whether to cut the Short, whether to wait for off-peak. An automatic step that is switched off is not taken; to change your process, change the file instead of repeating it every time.
