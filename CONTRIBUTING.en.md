# Contributing

[中文](CONTRIBUTING.md) | English

Bug fixes, docs and features are welcome.

This repo is public, and anyone making a drama holds things that must stay private: scripts, characters, voice samples, photos of real people, API keys, YouTube credentials. So contributing has one rule: **what you send is the tool, not your drama, and not your personal data.**

## 1. Before you start

- Open an issue first for a large change, such as a new shot kind, a change to the `project.py` format, or a new dependency. Small fixes can go straight to a PR.
- Flow: fork → branch from `main` → change → check (section 5) → open a PR against `main`.
- Setup: see [SETUP.md](docs/en/SETUP.md).
- Right after cloning, install the pre-commit check:

```bash
python dramakit/check_public.py --install-hook
```

## 2. What belongs in the repo

| Yes | No |
|---|---|
| Code in `dramakit/` | Anything under `projects/` (scripts, characters, voices, material, renders) |
| Docs in `docs/`, screenshots in `docs/images/` | Video, audio, images, fonts (doc screenshots aside) |
| `examples/`: structure only, no story | Job files `jobs/*.json` and `*.state` (your prompts, lines and absolute local paths) |
| `skills/`, install scripts, plugin config | `speech.json`, `storyboard.json`, `clips.json` (your dialogue) |
| | `youtube.json`, `upload_plan.json` (your channel and videos) |
| | `client_secret*.json`, `token*.json`, `.env`, any API key |
| | `library.db` and other databases |

`.gitignore` already blocks most of this. It can't stop `git add -f`, a renamed extension, or a format it doesn't list (`.mkv`, `.heic`, `.flac`…); the pre-commit check catches those.

## 3. De-identification

Take your own drama out of everything you write here: examples, docs, LESSONS, code comments, test data, commit messages, PRs and issues. **Commit messages and pushed files stay in the history for good**; deleting a file later doesn't remove them.

- **Characters**: use A / B / C and keys like `A` or `B_CASUAL`. Not your characters' names or keys, the series title or episode titles.
- **Places**: generic names like `ROOM` or `OFFICE` are fine. Not the companies, shops or places invented for your story.
- **Lines and prompts**: use `<…>` placeholders, e.g. `say=("B", "<B's line that raises the stakes>", "<delivery>")`.
- **LESSONS**: say what happened and how you fixed it. "Drama season 2, episode 7" is fine; don't quote the line, describe it ("a line that starts with one word and a long pause").
- **Numbers can stay**: seconds, `crop` values and strengths are part of the fix and give nothing away.
- **Screenshots** (`docs/images/`): use `examples/demo`, or blur. Keep series titles, characters' faces (real people above all), accounts, channels, folder paths and browser tabs out of frame. Strip EXIF (camera, GPS) before saving.
- **Real people**: no photo or voice sample of anyone, yourself included.
- **YouTube**: keep your channel, video and playlist ids out of examples and tests.

## 4. Personal data and credentials

- **API key**: only in the `AUTOIP_API_KEY` environment variable. Never in code, docs, tests or sample logs; read a log before you paste it.
- **YouTube OAuth**: keep `client_secret*.json` and `token*.json` in `projects/` or outside the repo, and pass their paths to the scripts.
- **Paths**: don't hard-code `C:\Users\<your name>\...` or `/Users/<your name>/...`. Code uses relative paths, `os.path.expanduser("~")` or environment variables; docs write `P` or `projects/<series>/s1e01_<title>`.
- **Contact details**: no e-mail address, phone number, ID number, street address or chat handle in any file, test data or screenshot.
- **Commit author**: a commit publishes your `user.email`. To keep yours private, use GitHub's noreply address (GitHub Settings → Emails → Keep my email addresses private), e.g. `git config user.email <ID>+<username>@users.noreply.github.com`.

### If something got pushed

1. **Revoke first, clean up second**:
   - AutoIP key: delete it in the dashboard and create a new one.
   - YouTube OAuth: reset the client secret in Google Cloud Console and revoke the tokens it granted.
2. **Then rewrite the git history** (e.g. with `git filter-repo`) and tell a maintainer. Deleting the file in a new commit is not enough: the old commit still has it, and someone may already have forked or cloned it.
3. **Story or personal data**: rewrite the history too; the shorter it stays public, the less chance it was copied.

## 5. Check before you send: `check_public.py`

```bash
python dramakit/check_public.py --install-hook                # once: checks before every commit from now on
python dramakit/check_public.py                               # by hand: the staged changes
python dramakit/check_public.py --range origin/main..HEAD     # before a PR: every commit you are about to push
python dramakit/check_public.py --all                         # the whole repo
```

It finds:

- **Files that don't belong**: `projects/`, media and fonts (images under `docs/images/` aside), job and `.state` files, dialogue json, YouTube upload records, credentials, databases.
- **Secrets**: AutoIP keys (`aip_…`), Google OAuth client ids / secrets / tokens, private keys, common API tokens. They are printed mostly masked.
- **Personal data**: e-mail addresses, Taiwan mobile numbers, Taiwan ID numbers, home-folder paths that name a user, YouTube channel ids.
- **Your story**: every word listed in `.private_terms` at the repo root.
- **Image EXIF** (camera, GPS): images added under `docs/images/`.

**`.private_terms`** is the word list of your own drama: one word per line, `#` starts a comment, case must match exactly. The file is in `.gitignore`, so it is never pushed. List the series title, character names and keys, invented places, channel and video ids:

```
# .private_terms
<series title>
<lead's name>
<character key, e.g. HERO_>
<company or shop name>
<channel id>
<video id>
```

**False alarms**: when a line really is meant to be public (like the showcase in the README), put `public-ok` on it: `<!-- public-ok -->` in Markdown, `# public-ok` in Python. `public-ok` never lets a secret through.

Don't skip the check with `git commit --no-verify`. The check only catches what slips through; it doesn't replace reading your own diff. It can't recognise a line of your dialogue unless its words are in `.private_terms`.

## 6. Code and docs

- **Style**: match the surrounding code: naming, how much it comments, idiom. If the standard library plus ffmpeg can do it, don't add a dependency; if you must, add it to `requirements.txt` and say why in the PR.
- **Steps that spend credits**:
  - The user must be able to see a review sheet before a batch is submitted; don't make code that submits a batch nobody has looked at.
  - The runner runs one job at a time by default (`AIP_MAX=1`).
  - A rejected job is never resent automatically unless its content changed.
- **Docs**: write `docs/zh-TW/` first, then sync `docs/en/`; update both READMEs.
- **New commands or fields**: update [PROJECT_FORMAT.md](docs/en/PROJECT_FORMAT.md), [WORKFLOW.md](docs/en/WORKFLOW.md) and `skills/autoip-drama-maker/SKILL.md` too.
- **Testing**:
  - At least run `python -m py_compile` on the files you changed.
  - Run what costs no credits on `examples/demo`, e.g. `python dramakit/storyboard.py examples/demo`.
  - Test with real material inside your own `projects/`, and keep that material out of the PR.

## 7. Pull requests

- Say what changed, why, and how you tested it.
- Images or video in a PR: demo material, or footage you may publish and have de-identified.
- Tick the checklist in the PR template.

## 8. Reporting issues

- Before pasting a log, mask keys, tokens, the user name in paths and e-mail addresses.
- Don't attach photos or voices of real people or an unpublished script. To reproduce a problem, use `examples/demo` or describe the structure ("three characters, one multi-reference shot, two people in frame").
- **Security problems** (a bug that could leak a key, say): don't put the details in a public issue. Open an issue that only says you have a security problem to report privately, and a maintainer will contact you.

## License

By contributing you agree that your contribution is released under this project's [MIT License](LICENSE), and that you have the right to release it.
