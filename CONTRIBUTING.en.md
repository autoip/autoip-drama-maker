# Contributing

[中文](CONTRIBUTING.md) | English

Bug fixes, docs, new features and your own measured numbers are all welcome.

This repo is public, and anyone making short dramas or music videos holds things that must not be: scripts, lyrics, songs, characters, voice samples, photos of real people, API keys, YouTube credentials. Every line you send is seen by everyone and indexed by search engines; deleting it later may be too late, as it may already be forked or cached. So there is one rule for contributions: **what you send is the tool, not your work and not your personal data.**

## 1. Before you start

- Open an issue first for big changes, e.g. a new shot kind, a change to the `project.py` format, a new package, a new line (explainers, news). Typos and small fixes can go straight to a pull request.
- Flow: fork → branch from `main` → change → check (section 5) → pull request against `main`.
- Setup: see [SETUP.md](docs/en/SETUP.md).
- Right after cloning, install the pre-commit check:

```bash
python dreamfab/check_public.py --install-hook
```

- **Don't spend many AutoIP credits for a contribution**: if footage you already generated can prove the change, don't submit new jobs. When you change code that submits jobs, write in the pull request how many jobs you sent and what they cost.

## 2. What belongs in the repo

| Yes | No |
|---|---|
| Code of the shared core `dreamfab/` and of each line (`drama/`, `mv/`, …) | Anything under `projects/` (scripts, songs, characters, voices, footage, renders) |
| `docs/`, and explanatory screenshots in `docs/images/` | Video, audio, images, fonts, model files (except those screenshots) |
| `examples/`: structure only, no story | Job files `jobs/*.json`, `*.state` (your prompts, lines and absolute local paths) |
| `skills/`, installers, plugin manifests | `speech.json`, `storyboard.json`, `clips.json`, `align.json`, `faces.json` (your lines, lyrics, characters) |
| | `youtube.json`, `upload_plan.json`, `YouTube_SEO.txt` (your channel, videos and copy) |
| | `client_secret*.json`, `token*.json`, `.env`, any API key |
| | `library.db` and other databases |

`.gitignore` blocks most of this. It cannot stop `git add -f`, a renamed extension or a format it does not list (`.mkv`, `.heic`, `.flac` …); the pre-commit check catches those. **Never force-add with `git add -f`.**

## 3. De-identification

Take your own work out of everything you write: examples, docs, LESSONS, code comments, test data, commit messages, pull requests and issues. **Commit messages and pushed files stay in history for good**; deleting a file later does not remove it.

- **Docs describe a method, not one work**: write what can be applied again and leave the user room to decide. Don't copy one episode's lines, one MV's lyrics, characters, storyboard or art direction.
- **Characters**: A / B / C, with keys like `A` or `B_CASUAL`. Not the names, keys, series title, episode or song titles of your work.
- **Places**: generic names like `ROOM` or `OFFICE` are fine; a company, shop or place name from your story is not.
- **Lines, lyrics and prompts**: `<…>` placeholders, e.g. `say=("B", "<B's pressing line>", "<delivery>")`.
- **LESSONS**: what happened and how it was fixed, with generic wording for measured numbers. "Season 2, episode 7 of a short drama" or "a woodcut-style MV where 4 of 14 segments drifted into a new character" is fine; quoting the line, naming the song or channel, or linking the video is not.
- **Numbers can stay**: seconds, `crop` values, strengths and credits are part of the fix and give nothing away.
- **Screenshots** (`docs/images/`): use `examples/<line>/demo`, or blur. Crop away browser tabs, the bookmarks bar, the desktop, file-explorer paths, avatars, e-mail and credit balance; no series title, character faces (real people above all), account or channel. Strip EXIF (camera, GPS) before saving.
- **Real people**: no one's photo, voice sample or cover version, not even your own, not even for a test.
- **YouTube and AutoIP**: no channel id, video id, playlist id, AutoIP task uuid, download link or credit balance of yours in examples or tests.

## 4. Personal data and credentials

- **The API key** lives only in the `AUTOIP_API_KEY` environment variable. Never in code, docs, tests or sample logs; code must never print it or write it into a log, a `.state` or any output.
- **YouTube OAuth**: `client_secret*.json` and `token*.json` stay outside the repo (default `~/.config/dreamfab/`); code reads them through an environment variable or a path argument.
- **Paths**: no hard-coded `C:\Users\<your name>\...` or `/Users/<your name>/...`. Code builds paths from the project folder (where `project.py` is), `os.path.expanduser("~")` or an environment variable; docs write `P` or `projects/<series>/s1e01_<title>`.
- **Contact details**: no e-mail, phone number, ID number, address or LINE id in any file, test data or screenshot.
- **Commit author**: a commit publishes your `user.email`. To keep it private, use GitHub's noreply address (GitHub settings → Emails → Keep my email addresses private), e.g. `git config user.email <ID>+<username>@users.noreply.github.com`.
- **Mask keys before you paste a log**, and paste only the error code and message (e.g. `validation_failed`, `concurrency_limit`), never a whole `.state` or job file; make paths relative:

```bash
python dreamfab/aip_runner.py P/jobs/x.json 2>&1 | sed 's/aip_[A-Za-z0-9_]*/aip_***/g'
```

```powershell
python dreamfab/aip_runner.py P/jobs/x.json 2>&1 | ForEach-Object { $_ -replace 'aip_\w+', 'aip_***' }
```

### If something got pushed by mistake

1. **Revoke first, then clean up**:
   - AutoIP key: delete it at https://autoip.app/dashboard/api-keys and create a new one.
   - YouTube OAuth: reset the client secret in Google Cloud Console and revoke the granted tokens.
2. **Then clean the git history** (e.g. with `git filter-repo`) and tell a maintainer. Deleting the file in a new commit is not enough: old commits still have it, and someone may have forked or cloned already. If it reached the main branch, open an issue **without** the content, naming only the commit to clean.
3. **Your work or personal data**: clean the history the same way; the shorter it was up, the smaller the chance it was copied.

## 5. The check before you send: `check_public.py`

```bash
python dreamfab/check_public.py --install-hook                # once: runs before every commit from then on
python dreamfab/check_public.py                               # by hand: the staged changes
python dreamfab/check_public.py --range origin/main..HEAD     # before a pull request: every commit you will push
python dreamfab/check_public.py --all                         # the whole repo
```

It finds:

- **Files that don't belong**: `projects/`, media and fonts (except images in `docs/images/`), job files and `.state`, dialogue json, YouTube upload records, credentials, databases.
- **Secrets**: AutoIP keys (`aip_…`), Google OAuth client ids / secrets / tokens, private keys, common API tokens. They are printed mostly masked.
- **Personal data**: e-mail addresses, Taiwanese mobile numbers, Taiwanese ID numbers, home-folder paths with a user name, YouTube channel ids.
- **Your work**: every word listed in `.private_terms` at the repo root.
- **Image EXIF** (camera, GPS) on images added to `docs/images/`.

**`.private_terms`** is the vocabulary of your own work: one word per line, `#` starts a comment, case-sensitive. It is in `.gitignore` and never pushed. List the series and song titles, character names and keys, proper place names, channel and video ids:

```
# .private_terms
<series or song title>
<lead character's name>
<character key, e.g. HERO_>
<company or shop name>
<channel id>
<video id>
```

**False alarms**: if a line really is meant to be public (e.g. the showcase in the README), add `public-ok` to it: `<!-- public-ok -->` in Markdown, `# public-ok` in Python and shell. `public-ok` never lets a secret through.

Don't skip the check with `git commit --no-verify`. The check only catches what slips through; it is no substitute for reading your diff: it cannot recognise a line from your story unless its words are in `.private_terms`. Also look through earlier commits with `git log -p`.

## 6. Code and docs

- **Style**: match the surrounding code: naming, how much it comments, idioms. Each script's docstring gives its usage and environment variables; change it when the behaviour changes.
- **Shared things go in the core**: what two or more lines use (submitting jobs, credits, super resolution and frame generation, the library, YouTube, the checks) lives in `dreamfab/`; what only one line uses stays in that line's folder.
- **Packages**: if the standard library plus ffmpeg can do it, don't add a package. If you must, add it to `requirements.txt` (`requirements-mv.txt` when only the MV line uses it) and explain in the pull request why the existing ones can't.
- **Defaults**: paid services, experimental features and GPU processing that changes the output (e.g. super resolution and frame generation) are switched on by an argument or setting, with at most one line of hint when off; acceleration that doesn't change the result (e.g. NVENC encoding) may switch on by itself.
- **Flows that spend credits**:
  - Before submitting, the credits can be estimated (`dreamfab.util.estimate`), and there is a review sheet or a still to look at before video goes out. Never let code submit a batch the user hasn't seen.
  - The runner takes one job at a time by default (`AIP_MAX=1`).
  - A rejected job is never resent automatically unless its content changed.
- **Docs**: write `docs/zh-TW/` first, then `docs/en/`; update both READMEs and add an entry at the top of both `RELEASE_NOTES.md` (version, date, what changed).
- **New commands or fields**: update that line's `PROJECT_FORMAT.md`, `WORKFLOW.md` and `skills/dreamfab-<line>/SKILL.md`.
- **Testing**:
  - At least `python -m py_compile` on the files you touched.
  - What costs no credits runs on the examples, e.g. `python drama/storyboard.py examples/drama/demo`, `python mv/storyboard.py examples/mv/demo`.
  - Tests with real footage stay in your own `projects/`; don't bring the footage into the pull request.

## 7. Pull requests

- One thing per commit. Commit messages in English, in the existing style: `file or feature: what it does`, e.g. `aip_runner.py: submit only in the off-peak window`.
- Say what changed, why, and how you checked it: which step, on what footage, how many credits.
- Images or video attached must be demo material, or footage you may publish and have de-identified.
- Tick the checklist in the pull request template.

## 8. Reporting a problem (issues)

- **Include**: which line, the version (the top entry of `RELEASE_NOTES.md`), OS, Python and ffmpeg versions, the command, and the error message **with the key masked**.
- **Don't attach**: your project folder, photos or voices of real people, an unpublished script, song or character art. To reproduce, use `examples/<line>/demo`, a minimal made-up project, or describe the structure, e.g. "three characters, one multi-reference shot, two people in frame".
- **Security problems** (e.g. a bug that can leak a key): no details in a public issue. Open one that only says you have a security problem to report privately, and a maintainer will contact you.

## Licence

By contributing you agree that your contribution is released under this project's [MIT License](LICENSE), and that you have the right to do so. Send only what you may publish: fonts, music or images you didn't make yourself, without a licence that allows redistribution, stay out.
