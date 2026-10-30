# Contributing

[中文](../zh-TW/CONTRIBUTING.md) | English

Bug fixes, features, docs and measured numbers are all welcome. This repo is public: every line you send is visible to everyone and indexed by search engines, and even after deletion it may live on in forks and caches. So besides the code itself, **de-identify everything before you send it** (see below).

## Before you start

- For a larger change, open an issue first saying what you want to change and why. Typos and small fixes can go straight to a PR.
- Set up the environment with [SETUP.md](SETUP.md): Python 3.10 or later, plus ffmpeg / ffprobe.
- Don't spend lots of AutoIP credits to test a contribution. If footage you already generated can verify the change, don't submit new jobs. If you change code that submits jobs, say in the PR how many jobs you submitted and how many credits they cost.

## Code

- **Match the surrounding code**: naming, comment density and idiom follow the same file. The docstring at the top of each script gives its usage and environment variables; when behaviour changes, update it.
- **Public code defaults to the CPU**: GPUs, paid services and experiments are opt-in through an environment variable or flag, and without it the code prints at most a one-line tip.
- **Packages**: standard library plus what is in `requirements.txt`. To add one, say in the PR why the existing ones won't do.
- **Anything that spends credits**: estimate the credits before submitting (`common.estimate`) and keep the still-review gate before video. Never submit by default.
- **Paths**: no hard-coded local paths. Build every path from the project folder (the folder that holds `project.py`).
- **Secrets**: API keys and OAuth files are read only from environment variables or files outside the repo. Code must never print them or write them to logs, `.state` or any output.

## Docs

- **Change both languages together**: `README.md` / `README.en.md`, `docs/zh-TW/` / `docs/en/`, and `skills/autoip-mv-maker/SKILL.md` when it applies.
- **Add an entry at the top of both `RELEASE_NOTES.md` files**: version, date and what changed.
- **Docs describe a framework, not one particular work**: write a reusable formula and leave room for the user's own choices. Don't copy one MV's lyrics, character names, storyboard or style settings.
- **Measured numbers are valuable, but generalize them**: "a woodblock-print MV, 4 of 14 clips walked in a new character" is fine; a song title, channel or video link is not.

## De-identification: check before you send

### Never include

| Kind | Examples | Why |
|---|---|---|
| Keys and credentials | AutoIP API keys starting with `aip_`, `client_secret_*.json`, `*token*.json`, `.env` | A leak hands over the account and its credits |
| Real people's images and voices | Photos of you or anyone else, face reference images, recordings, covers | Not even for testing |
| Personal data | Real names, email, phone, address, ID numbers, birthdays | This includes anything written inside files, beyond the commit author info |
| Account identifiers | YouTube channel IDs, private or unlisted video / playlist IDs, AutoIP task uuids, download links, credit balances | They can be traced back to you or your account |
| Local paths | `C:\Users\alice\...`, `/home/alice/...`, `/Users/bob/...` | Paths often contain a user name |
| Unpublished work | Lyrics, songs, characters and planning notes you haven't released | Your work stays in your own `projects/` |

`projects/`, media files, `jobs/`, `*.state` and `*.log` are already in `.gitignore`. **Don't force them in with `git add -f`.**

### Docs, examples, screenshots

- **Example projects**: use a made-up song title, characters and story (see `examples/demo`), and include only config files, no media.
- **Screenshots**: first crop out browser tabs, the bookmarks bar, the desktop, file-explorer paths, account avatars, email and credit balances. Then check the image for real faces.
- **Paths**: write `P/`, `<project>` or `~/` instead of real paths.

### Logs and error messages

Before pasting into an issue or PR, mask the key:

```bash
python mvkit/aip_runner.py P/jobs/x.json 2>&1 | sed 's/aip_[A-Za-z0-9_]*/aip_***/g'
```

```powershell
python mvkit/aip_runner.py P/jobs/x.json 2>&1 | ForEach-Object { $_ -replace 'aip_\w+', 'aip_***' }
```

- Paste the error code and message only (for example `validation_failed`, `concurrency_limit`), not a whole `.state` or job file.
- Turn paths into relative ones, then check once more for emails and channel IDs.

### Self-check before pushing

```bash
git status                       # anything that shouldn't be added?
git diff --cached --stat         # only the files you expect? no images, video, audio, .state, jobs/
git diff --cached | grep -nE 'aip_[A-Za-z0-9]{8,}|client_secret|refresh_token|access_token|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z.]{2,}|[A-Za-z]:[\\/]+Users[\\/]|/home/[^/ ]+|/Users/[^/ ]+'
```

If the last command finds anything, check each hit and remove it. Also look through earlier commits with `git log -p` in case they carry it too.

### If something slipped through

1. **Revoke the key right away**: for AutoIP, revoke it and make a new one at https://autoip.app/dashboard/api-keys; for YouTube OAuth, delete the credential in the Google Cloud Console. Deleting the file is not enough, because the history, forks and caches still have it.
2. Remove the file on your branch, rewrite its history and force-push your branch.
3. If it has already been merged, open an issue **without** the content, naming only the commit that needs cleaning, and the maintainers will handle it.

## Pull requests

1. Fork and branch off `main`.
2. One change per commit. Write commit messages in English in the existing style: `file or feature: what changed (version)`, for example `aip_runner.py: submit only in the off-peak window (0.7.1)`.
3. Go through the PR template checklist, including the de-identification check.
4. Say what changed, why and how you verified it: which step you ran, on what footage, and how many credits it cost.

## Reporting problems

- **Please include**: the version (the top entry of `RELEASE_NOTES.md`), OS, Python and ffmpeg versions, the command you ran, and the error message **with the key masked**.
- **Don't attach**: your project folder, songs, character images or photos of real people. To reproduce a problem, use `examples/demo` or a minimal made-up project.
- For a security problem (for example, code that writes the key into an output), don't put details in a public issue. Open an issue saying you have a security problem to report and ask a maintainer to contact you.

## License

Code and docs you contribute are released under this repo's [MIT License](../../LICENSE). Send only what you have the right to publish: fonts, music and images you didn't make yourself stay out unless their license allows redistribution.
