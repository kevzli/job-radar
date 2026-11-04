#!/usr/bin/env python3
"""Job Radar web app: dashboard + API + built-in biweekly scheduler.

  python3 server.py        # then open http://localhost:8787
"""
import datetime as dt
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common  # noqa: E402
import companies  # noqa: E402
import db  # noqa: E402
import scan  # noqa: E402

STATIC = os.path.join(HERE, "static")


def status():
    cfg = scan.load_config()
    last = db.last_scan()
    next_due = None
    if last:
        next_due = (dt.datetime.fromisoformat(last["finished"]) + dt.timedelta(days=cfg["scan_every_days"])).isoformat()
    return dict(running=scan.is_running(), progress=scan.progress[-40:], last_scan=last, next_due=next_due,
                scans=db.scans(10), config={k: cfg[k] for k in ("min_salary", "min_employees", "scan_every_days", "lookback_days")
                                            + scan.PREFERENCE_KEYS})


_logo_lock = threading.Lock()


def logo(name):
    """Company logo PNG, fetched once from Google's favicon service and cached in data/logos. None if unavailable."""
    domain = companies.domain_for(name)
    if not domain:
        return None
    d = os.path.join(db.DATA_DIR, "logos")
    path, miss = os.path.join(d, domain + ".png"), os.path.join(d, domain + ".none")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    if os.path.exists(miss) and time.time() - os.path.getmtime(miss) < 30 * 86400:
        return None
    os.makedirs(d, exist_ok=True)
    try:
        import urllib.request
        req = urllib.request.Request("https://www.google.com/s2/favicons?sz=128&domain=" + urllib.parse.quote(domain),
                                     headers={"User-Agent": common.UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = r.read()
        with _logo_lock, open(path, "wb") as f:
            f.write(data)
        return data
    except urllib.error.HTTPError:
        open(miss, "w").close()
    except Exception:
        pass  # offline: try again next time
    return None


def start_scan():
    if scan.is_running():
        return False
    threading.Thread(target=scan.run, daemon=True).start()
    return True


def scheduler():
    """Every hour, run a scan if the last successful one is older than scan_every_days."""
    time.sleep(20)
    while True:
        try:
            if scan.is_due(scan.load_config()) and not scan.is_running():
                scan.log("Scheduled scan is due - starting")
                scan.run()
        except Exception as e:
            scan.log("Scheduler error: %s" % e)
        time.sleep(3600)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", cache=False):
        if not isinstance(body, bytes):
            body = (json.dumps(body) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=604800" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                return self.send(200, f.read(), "text/html")
        if path == "/api/jobs":
            return self.send(200, {"jobs": db.all_jobs(), "latest_scan": (db.last_scan(False) or {}).get("id")})
        if path == "/api/logo":
            name = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("name", [""])[0]
            data = logo(name)
            return self.send(200, data, "image/png", cache=True) if data else self.send(404, b"", "image/png")
        if path == "/api/status":
            return self.send(200, status())
        if path == "/digest":
            d = os.path.join(db.DATA_DIR, "digests")
            files = sorted(os.listdir(d)) if os.path.isdir(d) else []
            if not files:
                return self.send(404, "No digest yet", "text/plain")
            with open(os.path.join(d, files[-1]), "rb") as f:
                return self.send(200, f.read(), "text/html")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/api/scan":
            return self.send(200, {"started": start_scan()})
        if self.path == "/api/preferences":
            scan.save_preferences(body)
            return self.send(200, {"jobs": db.all_jobs(), "config": status()["config"]})
        if self.path == "/api/job-status":
            if body.get("status") not in ("new", "saved", "applied", "hidden"):
                return self.send(400, {"error": "bad status"})
            db.set_status(body["key"], body["status"])
            return self.send(200, {"ok": True})
        self.send(404, {"error": "not found"})


def main():
    scan.load_env()
    port = int(os.environ.get("PORT") or scan.load_config().get("server_port", 8787))
    scan.rescore()
    threading.Thread(target=scheduler, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Job Radar running at http://localhost:%d" % port, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
