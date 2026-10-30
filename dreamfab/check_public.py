"""Before a commit or a pull request: finds what must not go public (secrets, personal data, your story, media).

usage: python dreamfab/check_public.py                          # staged changes: what the next commit adds
       python dreamfab/check_public.py --range origin/main..HEAD   # the commits a push or pull request adds
       python dreamfab/check_public.py --all                    # every file git would publish
       python dreamfab/check_public.py --install-hook           # run it before every commit (.git/hooks/pre-commit)

- files: anything under projects/, media and fonts (images only under docs/images), job and state files,
  speech / storyboard / clips json, YouTube upload records, OAuth client secrets and tokens, .env, databases
- secrets: AutoIP keys (aip_...), Google OAuth client ids, secrets and tokens, private keys, common API key shapes
- personal data: e-mail addresses, Taiwan phone and ID numbers, home folders that name a user (C:\\Users\\<name>,
  /Users/<name>, /home/<name>), YouTube channel ids
- your story: each word in .private_terms at the repo root (one per line, # comments; the file is in .gitignore):
  series title, character names and keys, places, channel and video ids
- EXIF (camera, GPS) in an image added under docs/images
A line that really is meant to be public: put `public-ok` on it (`<!-- public-ok -->` in Markdown, `# public-ok` in
Python); that never covers a secret. Exit status 1 when anything is found; secrets are printed masked.
"""
import os, re, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MEDIA = (".mp3 .wav .m4a .aac .flac .ogg .opus .mp4 .mov .mkv .webm .avi .png .jpg .jpeg .webp .gif .heic .bmp .tif "
         ".tiff .psd .ttf .otf .ttc .woff .woff2").split()
FILES = [  # (pattern on the path, why)
    (r"(^|/)projects/", "your projects stay local"),
    (r"(^|/)jobs/[^/]*\.json$|\.state$", "job files hold your prompts, lines and absolute paths"),
    (r"(^|/)(speech|storyboard|clips)\.json$", "holds your dialogue"),
    (r"(^|/)(youtube|upload_plan)\.json$", "YouTube upload record"),
    (r"client_secret[^/]*\.json$|token[^/]*\.json$|\.env$|\.(pem|key|p12)$|(^|/)cookies[^/]*\.txt$", "credentials"),
    (r"\.(db|sqlite|sqlite3)$", "database"),
    (r"(^|/)\.private_terms$", "your private word list"),
]
SECRETS = [
    (r"\baip_[A-Za-z0-9]{16,}", "AutoIP API key"),
    (r"\d{6,}-[a-z0-9]{20,}\.apps\.googleusercontent\.com", "Google OAuth client id"),
    (r"GOCSPX-[\w-]{10,}", "Google OAuth client secret"),
    (r"\bya29\.[\w-]{20,}|(?<![\w/])1//[\w-]{20,}", "Google OAuth token"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\bxox[abposr]-[\w-]{10,}",
     "API token"),
    (r"(?i)[\"']?(?:api[_-]?key|secret|token|password)[\"']?\s*[=:]\s*[\"'][^\"'\s<>{}$]{12,}[\"']", "credential value"),
]
PERSONAL = [
    (r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}", "e-mail address"),
    (r"(?<!\d)(?:\+886[- ]?9\d{2}|09\d{2})[- ]?\d{3}[- ]?\d{3}(?!\d)", "phone number"),
    (r"\b[A-Z][12]\d{8}\b", "ID number"),
    (r"(?i)(?:\b[a-z]:[\\/]+|(?<![\w.])/(?:[a-z]/)?)(?:users|home)[\\/]+([^\\/\s\"'<>`*%$]+)", "home folder"),
    (r"\bUC[\w-]{22}\b", "YouTube channel id"),
]
EMAIL_OK = re.compile(r"(?i)^git@|@(example\.(com|org|net)|users\.noreply\.github\.com|noreply\.github\.com)$|^noreply@")
USER_OK = {"public", "default", "you", "user", "username", "name", "me", "runner", "shared", "..."}


def git(*a, raw=False):
    r = subprocess.run(["git", "-c", "core.quotepath=false", *a], cwd=ROOT, capture_output=True)
    return r.stdout if raw else r.stdout.decode("utf-8", "replace")


def private_terms():
    p = os.path.join(ROOT, ".private_terms")
    if not os.path.exists(p):
        return None
    terms = [t.strip() for t in open(p, encoding="utf-8") if t.strip() and not t.lstrip().startswith("#")]
    return re.compile("|".join(map(re.escape, terms))) if terms else None   # exact case: a key KING is not the word king


def mask(s):
    return s[:6] + "…" if len(s) > 8 else "…"


def scan_line(path, n, line, terms, out):
    for pat, what in SECRETS:  # public-ok does not cover a secret
        for m in re.finditer(pat, line):
            out.append(f"{path}:{n}: [{what}] {mask(m.group(0))}")
    if "public-ok" in line:
        return
    for pat, what in PERSONAL:
        for m in re.finditer(pat, line):
            v = m.group(0)
            if what == "e-mail address" and EMAIL_OK.search(v) or what == "home folder" and m.group(1).lower() in USER_OK:
                continue
            out.append(f"{path}:{n}: [{what}] {v}")
    if terms:
        for t in sorted({m.group(0) for m in terms.finditer(line)}):
            out.append(f"{path}:{n}: [.private_terms: {t}] {line.strip()[:100]}")


def check_file(path, data, out):
    for pat, why in FILES:
        if re.search(pat, path):
            out.append(f"{path}: [file] {why}")
            return
    ext = os.path.splitext(path)[1].lower()
    if ext in MEDIA:
        if not path.startswith("docs/images/") or ext in (".ttf", ".otf", ".ttc", ".woff", ".woff2"):
            out.append(f"{path}: [file] media and fonts stay out of the repo (images only under docs/images)")
        elif data is not None and (b"Exif" in data[:131072] or b"eXIf" in data[:131072]):
            out.append(f"{path}: [file] image carries EXIF metadata (camera, GPS): save it again without")


def added_lines(diff):
    """(path, line number, text) of every line a unified diff adds."""
    path, n = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:].rstrip("	") if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            n = int(re.search(r"\+(\d+)", line).group(1))
        elif line.startswith("+") and path:
            yield path, n, line[1:]
            n += 1


def install_hook():
    hook = os.path.join(ROOT, ".git", "hooks", "pre-commit")
    if os.path.exists(hook):
        sys.exit(f"{hook} already exists: add this line to it yourself:\n  python dreamfab/check_public.py")
    py = sys.executable.replace("\\", "/")
    with open(hook, "w", encoding="utf-8", newline="\n") as f:
        f.write(f'#!/bin/sh\n# runs dreamfab/check_public.py on what is being committed\nexec "{py}" dreamfab/check_public.py\n')
    os.chmod(hook, 0o755)
    print("installed", hook)


def main(args):
    if "--install-hook" in args:
        return install_hook()
    terms, out = private_terms(), []
    if "--all" in args:
        files = [f for f in (git("ls-files") + git("ls-files", "--others", "--exclude-standard")).splitlines() if f]
        for f in files:
            p = os.path.join(ROOT, f)
            if not os.path.isfile(p):
                continue
            data = open(p, "rb").read()
            check_file(f, data, out)
            if os.path.splitext(f)[1].lower() not in MEDIA and b"\0" not in data[:8192]:
                for n, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
                    scan_line(f, n, line, terms, out)
        what = f"{len(files)} files"
    else:
        rng = args[args.index("--range") + 1] if "--range" in args else None
        diff = ["diff", rng] if rng else ["diff", "--cached"]
        names = [f for f in git(*diff, "--name-only", "--diff-filter=ACMR").splitlines() if f]
        tip = (re.split(r"\.\.\.?", rng)[-1] or "HEAD") if rng and ".." in rng else "HEAD"
        for f in names:
            data = git("show", f"{tip}:{f}" if rng else f":{f}", raw=True)
            check_file(f, data, out)
        for path, n, line in added_lines(git(*diff, "-U0", "--no-color", "--no-ext-diff")):
            scan_line(path, n, line, terms, out)
        what = f"{len(names)} changed files" + (f" in {rng}" if rng else " (staged)")
    for o in out:
        print(o)
    if terms is None:
        print("note: no .private_terms at the repo root, so your story words were not checked (CONTRIBUTING.md)")
    if out:
        print(f"\n{len(out)} found in {what}. Remove them, or mark a line that really is public with public-ok.")
        sys.exit(1)
    print(f"ok: {what}, nothing found")


if __name__ == "__main__":
    main(sys.argv[1:])
