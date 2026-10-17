# Release notes

[中文](../zh-TW/RELEASE_NOTES.md) | English

## 0.2.0 (2026-10-17): burned-in lip-sync captions, solved

On episode 5 《馬嵬》 every one of the 15 lip-sync clips came back with garbled captions burned in (white or gold; bottom, sides, vertical). Until now the only answers were cropping the frame or cutting away to another shot, and both hurt the picture or the performance. This release changes the workflow:

- **Captions are removed with AutoIP's video restore API.** `POST /videos/restore` with `source_video` + `operations[]=subtitle` (also `watermark` and `upscale`), 30 credits per 8-second segment. In practice a full line across the collar came out clean with the collar edge rebuilt; face and resolution untouched. Lip-sync clips are no longer cropped or re-cut around captions.
- **Lip-sync 3.0 (`engine=h3`).** No captions, tighter mouth and expression (a scream really opens the mouth), but 864×480 output. The docs say when it is worth it.
- **Lip-sync stills, settled: crop the portrait.** The semi-realistic portrait cropped straight to 16:9 at a different zoom per scene; no cut-out, no scene plate, no image-to-image. The detours (cut-outs with flat-cut arms and white halos, text-to-image half bodies with the wrong face, face swaps) are recorded in LESSONS.
- **Subtitles: `TYPO.hold`.** Clear a given line a set number of seconds after its last word, for a shout followed by silence.
- **Render: `EDITS[mode]["crop"]`.** The portrait and landscape cuts can crop differently.
- Docs updated: LESSONS (captions, stills, confirm voice attribution by ear, spell out the mouth in scream prompts), PROJECT_FORMAT, WORKFLOW, skill.

Series status: 《國風淒美對唱》 episode 1 《洛川》 is live, episodes 2–4 are finished, episode 5 《馬嵬》 (Emperor Xuanzong × Yang Guifei, dark K-pop ballad × metalcore) is in production.

## 0.1.0 (2026-10-15)

First public release: one `project.py` is one music video. Storyboard, AutoIP lip-sync and image-to-video, emotion-driven beat-synced editing, kinetic subtitles, render, thumbnails and publishing copy.
