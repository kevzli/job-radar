"""SQLite storage for jobs and scan history."""
import json
import os
import re
import sqlite3
import threading
import time

DATA_DIR = os.environ.get("JOBRADAR_DATA") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PATH = os.path.join(DATA_DIR, "jobradar.db")
_lock = threading.RLock()
_conn = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  key TEXT PRIMARY KEY, company TEXT, title TEXT, category TEXT, locations TEXT,
  urls TEXT, sources TEXT, external_ids TEXT, salary_min INTEGER, salary_max INTEGER,
  employees INTEGER, wlb_rating REAL, wlb_score INTEGER, fit_score INTEGER, salary_score INTEGER,
  score INTEGER, years_required INTEGER, years_max INTEGER, senior INTEGER, passes INTEGER, flags TEXT, reasons TEXT,
  snippet TEXT, description TEXT, workplace TEXT, posted_at TEXT, first_seen TEXT, last_seen TEXT,
  first_scan INTEGER, status TEXT DEFAULT 'new', closed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS company_sizes (slug TEXT PRIMARY KEY, employees INTEGER, checked TEXT);
CREATE TABLE IF NOT EXISTS scans (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started TEXT, finished TEXT, ok INTEGER,
  counts TEXT, errors TEXT, new_count INTEGER
);
"""


def conn():
    global _conn
    with _lock:
        if _conn is None:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            _conn = sqlite3.connect(PATH, check_same_thread=False)
            _conn.row_factory = sqlite3.Row
            _conn.executescript(SCHEMA)
            cols = {r[1] for r in _conn.execute("PRAGMA table_info(jobs)")}
            if "years_max" not in cols:
                _conn.execute("ALTER TABLE jobs ADD COLUMN years_max INTEGER")
        return _conn


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def job_key(company, title):
    n = lambda s: re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
    return n(company) + "|" + n(title)


def known_external_ids():
    with _lock:
        ids = set()
        for r in conn().execute("SELECT external_ids FROM jobs WHERE description != ''"):
            ids.update(json.loads(r["external_ids"] or "[]"))
        return ids


def upsert(job, scan_id):
    """Insert or merge a scored job. Returns True when the job is new."""
    c = conn()
    key = job_key(job["company"], job["title"])
    with _lock:
        row = c.execute("SELECT * FROM jobs WHERE key=?", (key,)).fetchone()
        ts = now()
        if row:
            urls = json.loads(row["urls"]); urls[job["source"]] = urls.get(job["source"]) or job["url"]
            srcs = sorted(set(json.loads(row["sources"])) | {job["source"]})
            ext = sorted(set(json.loads(row["external_ids"])) | {job["external_id"]})
            locs = sorted(set(json.loads(row["locations"])) | set(job["locations"]))
            if job.get("cached"):
                c.execute("UPDATE jobs SET urls=?, sources=?, external_ids=?, last_seen=?, closed=0 WHERE key=?",
                          (json.dumps(urls), json.dumps(srcs), json.dumps(ext), ts, key))
                return False
            # keep the richer description / salary across sources
            better = len(job.get("description") or "") >= len(row["description"] or "") or not row["description"]
            sal_lo = job.get("salary_min") or row["salary_min"]
            sal_hi = job.get("salary_max") or row["salary_max"]
            if not better:
                for f in ("fit_score", "wlb_score", "score", "flags", "reasons", "years_required", "years_max"):
                    job[f] = row[f] if f not in ("flags", "reasons") else json.loads(row[f])
            c.execute("""UPDATE jobs SET category=?, locations=?, urls=?, sources=?, external_ids=?, salary_min=?, salary_max=?,
                         employees=?, wlb_rating=?, wlb_score=?, fit_score=?, salary_score=?, score=?, years_required=?, years_max=?, senior=?,
                         passes=?, flags=?, reasons=?, snippet=?, description=?, workplace=?, posted_at=?, last_seen=?, closed=0
                         WHERE key=?""",
                      (job["category"], json.dumps(locs), json.dumps(urls), json.dumps(srcs), json.dumps(ext), sal_lo, sal_hi,
                       job.get("employees"), job.get("wlb_rating"), job["wlb_score"], job["fit_score"], job["salary_score"],
                       job["score"], job.get("years_required"), job.get("years_max"), job["senior"], job["passes"], json.dumps(job["flags"]),
                       json.dumps(job["reasons"]), job["snippet"] if better else row["snippet"],
                       job.get("description") if better else row["description"], job.get("workplace") or row["workplace"],
                       min(filter(None, [job.get("posted_at"), row["posted_at"]]), default=None), ts, key))
            return False
        if job.get("cached"):
            return False
        c.execute("""INSERT INTO jobs (key, company, title, category, locations, urls, sources, external_ids, salary_min, salary_max,
                     employees, wlb_rating, wlb_score, fit_score, salary_score, score, years_required, years_max, senior, passes, flags, reasons,
                     snippet, description, workplace, posted_at, first_seen, last_seen, first_scan)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (key, job["company"], job["title"], job["category"], json.dumps(job["locations"]),
                   json.dumps({job["source"]: job["url"]}), json.dumps([job["source"]]), json.dumps([job["external_id"]]),
                   job.get("salary_min"), job.get("salary_max"), job.get("employees"), job.get("wlb_rating"), job["wlb_score"],
                   job["fit_score"], job["salary_score"], job["score"], job.get("years_required"), job.get("years_max"), job["senior"], job["passes"],
                   json.dumps(job["flags"]), json.dumps(job["reasons"]), job["snippet"], job.get("description"),
                   job.get("workplace"), job.get("posted_at"), ts, ts, scan_id))
        return True


def mark_closed(ok_sources, scan_started):
    """Jobs whose sources all scanned fine this run but weren't seen are marked closed."""
    with _lock:
        c = conn()
        for r in c.execute("SELECT key, sources FROM jobs WHERE closed=0 AND last_seen < ?", (scan_started,)).fetchall():
            if set(json.loads(r["sources"])) <= set(ok_sources):
                c.execute("UPDATE jobs SET closed=1 WHERE key=?", (r["key"],))
        c.commit()


def start_scan():
    with _lock:
        cur = conn().execute("INSERT INTO scans (started, ok) VALUES (?, 0)", (now(),))
        conn().commit()
        return cur.lastrowid


def finish_scan(scan_id, ok, counts, errors, new_count):
    with _lock:
        conn().execute("UPDATE scans SET finished=?, ok=?, counts=?, errors=?, new_count=? WHERE id=?",
                       (now(), int(ok), json.dumps(counts), json.dumps(errors), new_count, scan_id))
        conn().commit()


def last_scan(ok_only=True):
    with _lock:
        q = "SELECT * FROM scans WHERE finished IS NOT NULL" + (" AND ok=1" if ok_only else "") + " ORDER BY id DESC LIMIT 1"
        r = conn().execute(q).fetchone()
        return dict(r) if r else None


def cached_size(slug):
    """(hit, employees) for a Built In company slug; entries expire after 90 days."""
    with _lock:
        r = conn().execute("SELECT employees, checked FROM company_sizes WHERE slug=?", (slug,)).fetchone()
    if r and r["checked"] > time.strftime("%Y-%m-%d", time.localtime(time.time() - 90 * 86400)):
        return True, r["employees"]
    return False, None


def cache_size(slug, employees):
    with _lock:
        conn().execute("INSERT OR REPLACE INTO company_sizes VALUES (?,?,?)", (slug, employees, now()))
        conn().commit()


def all_jobs():
    with _lock:
        rows = conn().execute("SELECT * FROM jobs ORDER BY score DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for f in ("locations", "urls", "sources", "external_ids", "flags", "reasons"):
            d[f] = json.loads(d[f] or "[]")
        d.pop("description", None)
        out.append(d)
    return out


def rescore(evaluate):
    """Re-run scoring on every stored job (after criteria or preferences change)."""
    with _lock:
        c = conn()
        for r in c.execute("SELECT * FROM jobs").fetchall():
            job = dict(r)
            ev = evaluate(job)
            if not ev["category"]:
                c.execute("DELETE FROM jobs WHERE key=?", (r["key"],))
                continue
            c.execute("""UPDATE jobs SET category=?, fit_score=?, wlb_score=?, salary_score=?, score=?, years_required=?, years_max=?,
                         senior=?, passes=?, flags=?, reasons=?, employees=?, wlb_rating=? WHERE key=?""",
                      (ev["category"], ev["fit_score"], ev["wlb_score"], ev["salary_score"], ev["score"], ev["years_required"],
                       ev["years_max"], ev["senior"], ev["passes"], json.dumps(ev["flags"]), json.dumps(ev["reasons"]),
                       ev["employees"], ev["wlb_rating"], r["key"]))
        c.commit()


def set_status(key, status):
    with _lock:
        conn().execute("UPDATE jobs SET status=? WHERE key=?", (status, key))
        conn().commit()


def scans(limit=20):
    with _lock:
        return [dict(r) for r in conn().execute("SELECT * FROM scans ORDER BY id DESC LIMIT ?", (limit,))]
