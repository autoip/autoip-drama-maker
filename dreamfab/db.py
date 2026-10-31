"""One SQLite file for all of Dreamfab: every series' library index (drama and MV lines) and the publishing log.

Where: $DREAMFAB_DB, else ~/.config/dreamfab/dreamfab.db (next to workflow.ini and the YouTube login).
Inside:
  <line>_<table>   a library's tables with a `series` column (the series folder), e.g. drama_episodes, mv_shots
  probe            the ffprobe cache by absolute path, shared by every library
  youtube_log      every step on YouTube (dreamfab/youtube_log.py)
A library builds its index in memory exactly as before (scratch()), and store() swaps that series' rows in, in one
transaction. open_index() gives a connection whose temporary views carry the line's own table names (episodes, shots
...) and show one series, so the libraries' queries read as they always did.

Older versions kept a library.db in every series folder and the publishing log in ~/.config/dreamfab/youtube_log.db
($YT_LOG_DB). They come in by themselves (adopt()): the log the first time anything opens the shared file, a series'
library.db when its library next indexes that series. Each is renamed to *.merged afterwards, never deleted.

usage: python dreamfab/db.py show                    the tables, with rows per series
       python dreamfab/db.py merge [PATH ...]        bring older files in now: PATH is a folder searched for library.db
                                                     files (default: projects) or one old file, e.g. a log that
                                                     YT_LOG_DB pointed at
"""
import glob, os, sqlite3, sys

HOME = os.path.join(os.path.expanduser("~"), ".config", "dreamfab")
PATH = os.environ.get("DREAMFAB_DB") or os.path.join(HOME, "dreamfab.db")
OLD_LOGS = [p for p in (os.environ.get("YT_LOG_DB"), os.path.join(HOME, "youtube_log.db")) if p]
PROBE = "CREATE TABLE IF NOT EXISTS {}probe (path TEXT PRIMARY KEY, size INT, mtime REAL, dur REAL, w INT, h INT)"
LOG = ("CREATE TABLE IF NOT EXISTS {0}youtube_log (at TEXT, video TEXT, action TEXT, text TEXT, project TEXT, kind TEXT);"
       "CREATE INDEX IF NOT EXISTS {0}youtube_log_video ON youtube_log (video)")
q = lambda name: '"' + name.replace('"', '""') + '"'


def connect(path=None):
    """The shared file (created on first use), ready for several processes at once: WAL, and waits instead of failing
    while another one writes. An older version's publishing log is brought in the first time."""
    path = path or PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(PROBE.format(""))
    db.executescript(LOG.format(""))
    if os.path.abspath(path) == os.path.abspath(PATH):
        for old in OLD_LOGS:
            if os.path.exists(old):
                adopt(old, db)
    return db


def scratch(path=None):
    """An in-memory database for a library build, holding a copy of the shared probe cache; the shared file is
    attached as `lib` for store()."""
    connect(path).close()
    mem = sqlite3.connect(":memory:", timeout=30)
    mem.execute("ATTACH DATABASE ? AS lib", (path or PATH,))
    mem.execute(PROBE.format(""))
    mem.execute("INSERT INTO probe SELECT * FROM lib.probe")
    return mem


def _replace(con, src, line, series):
    """Put every table of schema `src` (but probe) into lib.<line>_<table> as this series' rows; a table whose columns
    changed is made again (the other series of that line come back at their next index)."""
    tables = [r[0] for r in con.execute(f"SELECT name FROM {src}.sqlite_master WHERE type = 'table'") if r[0] != "probe"]
    for t in tables:
        cols = [r[1] for r in con.execute(f"PRAGMA {src}.table_info({q(t)})")]
        name = f"{line}_{t}"
        if [r[1] for r in con.execute(f"PRAGMA lib.table_info({q(name)})")] != ["series"] + cols:
            con.execute(f"DROP TABLE IF EXISTS lib.{q(name)}")
            con.execute(f"CREATE TABLE lib.{q(name)} (series TEXT, {', '.join(map(q, cols))})")
            con.execute(f"CREATE INDEX lib.{q(name + '_series')} ON {q(name)} (series)")
        con.execute(f"DELETE FROM lib.{q(name)} WHERE series = ?", (series,))
        con.execute(f"INSERT INTO lib.{q(name)} SELECT ?, * FROM {src}.{q(t)}", (series,))
    if con.execute(f"SELECT 1 FROM {src}.sqlite_master WHERE name = 'probe'").fetchone():
        con.execute(f"INSERT OR REPLACE INTO lib.probe SELECT * FROM {src}.probe")


def store(mem, line, series):
    """Swap one series' index (the tables built in a scratch() database) into the shared file, all at once."""
    with mem:
        _replace(mem, "main", line, os.path.abspath(series))


def open_index(line, series, path=None):
    """A connection to the shared file where the line's tables (episodes, shots ...) are temporary views of one series."""
    db = connect(path)
    s = os.path.abspath(series).replace("'", "''")
    names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name GLOB ?", (line + "_*",))]
    for name in names:
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({q(name)})") if r[1] != "series"]
        db.execute(f"CREATE TEMP VIEW {q(name[len(line) + 1:])} AS SELECT {', '.join(map(q, cols))} FROM main.{q(name)} "
                   f"WHERE series = '{s}'")
    return db


def has_index(line, series, path=None):
    """Whether the series has been indexed into the shared file yet."""
    if not os.path.exists(path or PATH):
        return False
    db = connect(path)
    try:
        return bool(db.execute(f"SELECT 1 FROM {q(line + '_meta')} WHERE series = ? LIMIT 1", (os.path.abspath(series),)).fetchone())
    except sqlite3.Error:
        return False
    finally:
        db.close()


def line_of(tables):
    """Which library wrote an old library.db: the MV one has lyrics; the drama one has cast and sets."""
    return "mv" if "lyrics" in tables else "drama"


def _retire(p):
    """Rename an old file to *.merged (*.merged2 ... when that is taken; never deleted, never written over). The rename
    is the claim: when two programs find the file at once only one gets it. None when it can't be had right now."""
    for i in range(1, 100):
        to = p + ".merged" + (str(i) if i > 1 else "")
        if not os.path.exists(to):
            try:
                os.rename(p, to)
                return to
            except OSError:
                return None   # another program took it, or it is open somewhere: next time
    return None


def adopt(old, db=None):
    """Bring one older file into the shared one, then rename it *.merged. A publishing log adds the entries the shared
    log doesn't have yet. A series' library.db gives its probe cache, so the series' next index needn't ffprobe every
    video again; the index itself is always rebuilt from the series' files, so nothing else in it is needed."""
    if os.path.abspath(old) == os.path.abspath(PATH):
        return
    taken = _retire(old)
    if not taken:
        return
    own = db is None
    db = db or connect()
    try:
        db.execute("ATTACH DATABASE ? AS old", (taken,))
        tables = {r[0] for r in db.execute("SELECT name FROM old.sqlite_master WHERE type = 'table'")}
        with db:
            if "actions" in tables:
                n = db.execute("SELECT count(*) FROM old.actions").fetchone()[0]
                cur = db.execute("INSERT INTO youtube_log SELECT at, video, action, text, project, kind FROM old.actions "
                                 "EXCEPT SELECT * FROM youtube_log")
                what = f"publishing log, {cur.rowcount} of {n} entries added"
            elif "probe" in tables:
                cur = db.execute("INSERT OR REPLACE INTO probe SELECT * FROM old.probe")
                what = f"{line_of(tables)} library of {os.path.dirname(os.path.abspath(old))}, {cur.rowcount} probed media"
            else:
                what = "nothing Dreamfab uses"
        print(f"dreamfab.db: {what} from {old} (now {os.path.basename(taken)})", file=sys.stderr)
    except sqlite3.Error as e:
        print(f"dreamfab.db: could not read {taken}: {e} (rename it back to {os.path.basename(old)} to try again)",
              file=sys.stderr)
    finally:
        if any(r[1] == "old" for r in db.execute("PRAGMA database_list")):
            db.execute("DETACH DATABASE old")
        if own:
            db.close()


def merge(paths):
    """Bring older files in now rather than when they're next used (adopt())."""
    db = connect()   # the old publishing log in its usual place comes in here
    for arg in paths:
        found = sorted(glob.glob(os.path.join(arg, "**", "library.db"), recursive=True)) if os.path.isdir(arg) else [arg]
        for p in found:
            adopt(p, db)
    db.close()
    print(f"-> {PATH}")


def show():
    db = connect()
    print(PATH)
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"):
        cols = [r[1] for r in db.execute(f"PRAGMA table_info({q(name)})")]
        if "series" in cols:
            for s, n in db.execute(f"SELECT series, count(*) FROM {q(name)} GROUP BY series"):
                print(f"  {name:<20} {n:>7}  {s}")
        else:
            print(f"  {name:<20} {db.execute(f'SELECT count(*) FROM {q(name)}').fetchone()[0]:>7}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if not a or a[0] not in ("show", "merge"):
        sys.exit(__doc__)
    merge(a[1:] or ["projects"]) if a[0] == "merge" else show()
