#!/usr/bin/env python3
"""Run a job scan.

  python3 scan.py            # scan now
  python3 scan.py --if-due   # scan only if the last good scan is older than scan_every_days
  python3 scan.py --only greenhouse,ashby   # restrict sources (for testing)
"""
import argparse
import datetime as dt
import html
import json
import os
import smtplib
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import companies  # noqa: E402
import db  # noqa: E402
import sources  # noqa: E402
from scoring import Matcher  # noqa: E402

_running = threading.Lock()
progress = []  # recent log lines, shown in the web UI


def load_env():
    for p in (os.path.join(db.DATA_DIR, ".env"), os.path.join(HERE, ".env")):
        if not os.path.exists(p):
            continue
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


PREFERENCE_KEYS = ("experience_years", "experience_flex", "include_unstated_years", "min_salary", "min_wlb_score")


def settings_path():
    return os.path.join(db.DATA_DIR, "settings.json")


def load_settings():
    try:
        with open(settings_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def load_config():
    """Defaults from config.json, overridden by data/settings.json (saved from the Preferences panel or edited by hand)."""
    with open(os.path.join(HERE, "config.json")) as f:
        cfg = json.load(f)
    cfg.update(load_settings())
    return cfg


def save_preferences(prefs):
    s = load_settings()
    s.update({k: prefs[k] for k in PREFERENCE_KEYS if k in prefs})
    os.makedirs(db.DATA_DIR, exist_ok=True)
    with open(settings_path(), "w") as f:
        json.dump(s, f, indent=2)
    rescore()


def rescore():
    m = Matcher(load_config())

    def evaluate(row):
        entry = companies.lookup(row["company"]) or {}
        return m.evaluate(dict(row), entry)

    db.rescore(evaluate)


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    progress.append(line)
    del progress[:-300]
    print(line, flush=True)


def is_due(cfg):
    last = db.last_scan()
    if not last:
        return True
    age = dt.datetime.now() - dt.datetime.fromisoformat(last["finished"])
    return age >= dt.timedelta(days=cfg["scan_every_days"])


def is_running():
    return _running.locked()


def run(only=None):
    if not _running.acquire(blocking=False):
        log("A scan is already running")
        return None
    try:
        return _run(only)
    finally:
        _running.release()


def _run(only):
    load_env()
    cfg = load_config()
    m = Matcher(cfg)
    del progress[:]
    scan_id = db.start_scan()
    started = db.now()
    log("Scan #%d started" % scan_id)
    want = lambda s: not only or s in only
    raw, errors, counts, ok_sources = [], {}, {}, set()

    def size_ok(name):
        c = companies.lookup(name)
        return not c or c["employees"] >= cfg["min_employees"]

    def collect(name, fn):
        t0 = time.time()
        try:
            jobs = fn()
            log("%s: %d matching NYC roles (%.0fs)" % (name, len(jobs), time.time() - t0))
            return name, jobs, None
        except Exception as e:
            log("%s: FAILED %s" % (name, e))
            return name, [], str(e)

    tasks = []
    terms = cfg["workday_search_terms"]
    for c in companies.feeds():
        kind = c["ats"][0]
        if not want(kind) and not want("company"):
            continue
        if kind == "greenhouse":
            fn = lambda c=c: sources.greenhouse(c["name"], c["ats"][1], m.title_ok, log)
        elif kind == "lever":
            fn = lambda c=c: sources.lever(c["name"], c["ats"][1], m.title_ok, log)
        elif kind == "ashby":
            fn = lambda c=c: sources.ashby(c["name"], c["ats"][1], m.title_ok, log)
        else:
            fn = lambda c=c: sources.workday(c["name"], c["ats"][1], c["ats"][2], c["ats"][3], terms, m.title_ok, log)
        tasks.append(("%s/%s" % (kind, c["name"]), kind, fn))

    known = db.known_external_ids()
    slow = []
    if want("linkedin"):
        slow.append(("linkedin", "linkedin", lambda: sources.linkedin(
            cfg["linkedin_queries"], cfg["linkedin_pages_per_query"], cfg["lookback_days"],
            m.title_ok, size_ok, lambda i: i in known, log)))
    if want("builtin"):
        slow.append(("builtin", "builtin", lambda: sources.builtin(
            cfg["builtin_queries"], cfg["builtin_pages_per_query"], cfg["lookback_days"], m.title_ok, log)))
    key = sources.jsearch_key(cfg)
    if want("indeed") and key:
        slow.append(("indeed (jsearch)", "indeed", lambda: sources.jsearch(cfg["jsearch_queries"], key, m.title_ok, log)))
    elif want("indeed"):
        log("indeed: skipped (Indeed blocks direct scraping; set JSEARCH_API_KEY in .env to enable)")

    kinds = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {}
        for name, kind, fn in slow + tasks:
            futs[pool.submit(collect, name, fn)] = kind
        for f in as_completed(futs):
            name, jobs, err = f.result()
            kind = futs[f]
            kinds.setdefault(kind, []).append(err)
            raw.extend(jobs)
            counts[name] = len(jobs)
            if err:
                errors[name] = err
    for kind, errs in kinds.items():
        if not any(errs):
            ok_sources.add(kind)
        # one failed board shouldn't mark every greenhouse job closed, so require all boards of that kind to succeed

    # Company size: directory first, then Built In profile lookup for unknown companies.
    log("Scoring %d postings..." % len(raw))
    new_count = 0
    sources._size_state.update(lookups=0, failures=0)
    for j in raw:
        entry = companies.lookup(j["company"])
        if entry:
            j["company"] = entry["name"]
        if not j.get("employees") and not entry and not j.get("cached") and m.category(j["title"]):
            j["employees"] = sources.builtin_company_size(j.get("company_slug") or j["company"], log)
        if j.get("cached"):
            db.upsert(j, scan_id)
            continue
        j.update(m.evaluate(j, entry or {}))
        if not j["category"]:
            continue
        j["snippet"] = (j.get("description") or "")[:600]
        if db.upsert(j, scan_id) and j["passes"]:
            new_count += 1
    db.conn().commit()
    db.mark_closed(ok_sources, started)
    ok = len(errors) < max(3, len(counts) // 3)
    db.finish_scan(scan_id, ok, counts, errors, new_count)
    log("Scan #%d done: %d new matching jobs, %d source errors" % (scan_id, new_count, len(errors)))
    send_digest(cfg, scan_id)
    return scan_id


# ------------------------------------------------------------------ digest
def fmt_money(lo, hi):
    if not lo:
        return "Salary not listed"
    k = lambda v: "$%dK" % round(v / 1000)
    return k(lo) if not hi or hi == lo else "%s – %s" % (k(lo), k(hi))


def build_digest(scan_id, cfg):
    jobs = [j for j in db.all_jobs() if j["passes"] and not j["closed"] and j["status"] != "hidden"]
    new = [j for j in jobs if j["first_scan"] == scan_id]
    rest = [j for j in jobs if j["first_scan"] != scan_id]

    def rows(js):
        out = []
        for j in js:
            url = next(iter(j["urls"].values()), "#")
            out.append(
                '<tr><td style="padding:10px 8px;border-bottom:1px solid #eee"><a href="%s" style="color:#1a56db;font-weight:600;text-decoration:none">%s</a>'
                '<div style="color:#555;font-size:13px">%s · %s</div><div style="color:#888;font-size:12px">%s</div></td>'
                '<td style="padding:10px 8px;border-bottom:1px solid #eee;white-space:nowrap;font-size:13px">%s</td>'
                '<td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;font-size:13px;white-space:nowrap"><b>Score %s</b><br><span style="color:#888">WLB %s</span></td></tr>'
                % (html.escape(url), html.escape(j["title"]), html.escape(j["company"]), html.escape(j["category"] or ""),
                   html.escape(" · ".join(j["reasons"][:2])), fmt_money(j["salary_min"], j["salary_max"]), j["score"], j["wlb_score"]))
        return "".join(out)

    table = '<table style="border-collapse:collapse;width:100%%;font-family:-apple-system,Helvetica,Arial,sans-serif">%s</table>'
    body = ('<div style="font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:760px">'
            '<h2 style="margin:0 0 4px">Job Radar: %d new NYC roles</h2>'
            '<p style="color:#666;margin:0 0 16px">Forward deployed / solutions / product roles · $%dK+ · %d–%d yrs experience · %s+ employees · ranked by fit + work-life balance</p>'
            % (len(new), cfg["min_salary"] // 1000, max(0, cfg["experience_years"] - cfg["experience_flex"]),
               cfg["experience_years"] + cfg["experience_flex"], format(cfg["min_employees"], ",")))
    body += "<h3>New since last scan</h3>" + (table % rows(new) if new else "<p>No new matches this time.</p>")
    if rest:
        body += "<h3>Still open (top 15)</h3>" + table % rows(rest[:15])
    body += "</div>"
    return len(new), body


def send_digest(cfg, scan_id):
    n_new, body = build_digest(scan_id, cfg)
    out_dir = os.path.join(db.DATA_DIR, "digests")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "digest-%s.html" % time.strftime("%Y-%m-%d"))
    with open(path, "w") as f:
        f.write("<!doctype html><meta charset=utf-8><title>Job Radar digest</title>" + body)
    log("Digest written to data/digests/" + os.path.basename(path))

    em = cfg.get("email", {})
    pw = os.environ.get(em.get("smtp_password_env", ""), "")
    if em.get("enabled") and em.get("smtp_user") and pw:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Job Radar: %d new NYC roles" % n_new
            msg["From"] = em.get("from") or em["smtp_user"]
            msg["To"] = em["to"]
            msg.attach(MIMEText(body, "html"))
            with smtplib.SMTP_SSL(em["smtp_host"], em["smtp_port"], timeout=30) as s:
                s.login(em["smtp_user"], pw)
                s.send_message(msg)
            log("Digest emailed to " + em["to"])
        except Exception as e:
            log("Email failed: %s" % e)
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", 'display notification "%d new matching roles - open localhost:%d" with title "Job Radar"'
                        % (n_new, cfg.get("server_port", 8787))], check=False, capture_output=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--if-due", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    cfg = load_config()
    if a.if_due and not is_due(cfg):
        print("Not due yet (last scan %s)" % db.last_scan()["finished"])
        sys.exit(0)
    run(set(filter(None, a.only.split(","))) or None)
