"""Shared helpers: HTTP, HTML stripping, salary parsing, NYC detection."""
import gzip
import html
import json
import re
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


def http(url, data=None, headers=None, timeout=25, retries=3, backoff=4.0):
    """GET (or POST when data is given) and return the decoded body."""
    hdrs = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode() if not isinstance(data, bytes) else data
        hdrs.setdefault("Content-Type", "application/json")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (404, 400, 401, 403, 422):
                raise
            time.sleep(backoff * (attempt + 1) * (3 if e.code == 429 else 1))
        except Exception as e:  # network hiccup / timeout
            last = e
            time.sleep(backoff * (attempt + 1))
    raise last


def http_json(url, data=None, headers=None, **kw):
    h = {"Accept": "application/json"}
    h.update(headers or {})
    return json.loads(http(url, data=data, headers=h, **kw))


def strip_html(s):
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</div>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()


# ---------------------------------------------------------------- salary
_NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*([kK])?"
_RANGE = re.compile(
    r"\$\s?" + _NUM + r"\s*(?:USD|usd)?\s*(?:/\s*(?:yr|year|hr|hour))?\s*(?:-|–|—|to|and)\s*\$?\s?" + _NUM
    + r"(?:\s*(?:USD|usd))?\s*(/\s*(?:hr|hour)|per hour|an hour|hourly)?")
_SALARY_CUE = re.compile(r"(?i)salary|base pay|pay range|compensation|annual|base|range")
_NYC_CUE = re.compile(r"(?i)new york|nyc|ny\b")


def _to_num(n, k):
    v = float(n.replace(",", ""))
    if k:
        v *= 1000
    return v


def parse_salary(text):
    """Find an annual base-salary range in free text. Returns (lo, hi) or (None, None)."""
    if not text:
        return None, None
    best = None
    for m in _RANGE.finditer(text):
        lo, hi = _to_num(m.group(1), m.group(2)), _to_num(m.group(3), m.group(4))
        if m.group(2) and not m.group(4) and hi < 1000:
            hi *= 1000  # "$120k-150" -> thousands
        if m.group(4) and not m.group(2) and lo < 1000:
            lo *= 1000  # "$120-150K" -> thousands
        hourly = bool(m.group(5))
        if hourly or (lo < 300 and hi < 300):
            lo, hi = lo * 2080, hi * 2080
        if lo > hi:
            lo, hi = hi, lo
        if not (30000 <= lo <= 1500000 and 30000 <= hi <= 1500000):
            continue
        ctx = text[max(0, m.start() - 160): m.start()]
        score = (2 if _NYC_CUE.search(ctx) else 0) + (1 if _SALARY_CUE.search(ctx) else 0)
        if best is None or score > best[0]:
            best = (score, lo, hi)
    if best:
        return int(best[1]), int(best[2])
    return None, None


def salary_from_k_text(t):
    """Built In style: '140K-220K Annually', '75-95 Hourly'."""
    m = re.search(r"([\d.]+)\s*([kK])?\s*-\s*([\d.]+)\s*([kK])?\s*(Annually|Hourly)?", t or "")
    if not m:
        return None, None
    lo, hi = float(m.group(1)), float(m.group(3))
    if m.group(2) or m.group(4):
        lo, hi = lo * 1000, hi * 1000
    if (m.group(5) or "").lower() == "hourly":
        lo, hi = lo * 2080, hi * 2080
    return int(lo), int(hi)


# ---------------------------------------------------------------- location
_NYC = re.compile(r"(?i)\bnew york(?:,?\s*(?:ny\b|new york|city|metro))|\bnyc\b|\bmanhattan\b|\bbrooklyn\b"
                  r"|^new york$|new york city metropolitan|\bnew york, us\b|new york, united states")


def is_nyc(*locs):
    for loc in locs:
        if isinstance(loc, (list, tuple)):
            if is_nyc(*loc):
                return True
        elif loc and _NYC.search(loc.strip()):
            return True
    return False


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()
