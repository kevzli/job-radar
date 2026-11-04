"""Job sources. Each fetcher returns a list of raw job dicts:

  source, external_id, company, title, locations (list[str]), url, posted_at,
  description, salary_min, salary_max, [employees], [workplace]

`title_ok(title)` is used to skip irrelevant postings before fetching details.
"""
import os
import re
import time
import urllib.error
import urllib.parse

from common import http, http_json, strip_html, parse_salary, salary_from_k_text, is_nyc, clean


def _job(**kw):
    base = dict(source="", external_id="", company="", title="", locations=[], url="", posted_at=None,
                description="", salary_min=None, salary_max=None, employees=None, workplace=None)
    base.update(kw)
    if base["salary_min"] is None:
        base["salary_min"], base["salary_max"] = parse_salary(base["description"])
    return base


# ------------------------------------------------------------------ Greenhouse
def greenhouse(company, token, title_ok, log):
    data = http_json("https://boards-api.greenhouse.io/v1/boards/%s/jobs" % token)
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location", {}).get("name", "")] + [o.get("location") or o.get("name") or "" for o in j.get("offices", [])]
        if not title_ok(j["title"]) or not is_nyc(locs):
            continue
        try:
            d = http_json("https://boards-api.greenhouse.io/v1/boards/%s/jobs/%s?pay_transparency=true" % (token, j["id"]))
        except Exception as e:
            log("  greenhouse %s job %s: %s" % (token, j["id"], e))
            d = j
        desc = strip_html(d.get("content", ""))
        lo = hi = None
        for p in d.get("pay_input_ranges") or []:
            if p.get("min_cents") and p.get("max_cents"):
                lo, hi = p["min_cents"] // 100, p["max_cents"] // 100
                if "new york" in (p.get("title") or "").lower():
                    break
        out.append(_job(source="greenhouse", external_id="gh-%s-%s" % (token, j["id"]), company=company,
                        title=clean(j["title"]), locations=[l for l in locs if l], url=j.get("absolute_url"),
                        posted_at=(j.get("first_published") or j.get("updated_at") or "")[:10] or None,
                        description=desc, salary_min=lo, salary_max=hi))
    return out


# ------------------------------------------------------------------ Lever
def lever(company, slug, title_ok, log):
    data = http_json("https://api.lever.co/v0/postings/%s?mode=json" % slug)
    out = []
    for j in data:
        cats = j.get("categories", {})
        locs = [cats.get("location", "")] + list(cats.get("allLocations") or [])
        if not title_ok(j.get("text", "")) or not is_nyc(locs):
            continue
        desc = "\n".join(filter(None, [j.get("descriptionPlain"), j.get("descriptionBodyPlain"),
                                        "\n".join(strip_html(l.get("content", "")) for l in j.get("lists", [])),
                                        j.get("additionalPlain")]))
        sr = j.get("salaryRange") or {}
        lo, hi = sr.get("min"), sr.get("max")
        if lo and "hour" in (sr.get("interval") or ""):
            lo, hi = lo * 2080, hi * 2080
        created = j.get("createdAt")
        out.append(_job(source="lever", external_id="lv-%s" % j["id"], company=company, title=clean(j["text"]),
                        locations=[l for l in locs if l], url=j.get("hostedUrl"),
                        posted_at=time.strftime("%Y-%m-%d", time.gmtime(created / 1000)) if created else None,
                        description=desc, salary_min=lo, salary_max=hi, workplace=j.get("workplaceType")))
    return out


# ------------------------------------------------------------------ Ashby
def ashby(company, org, title_ok, log):
    data = http_json("https://api.ashbyhq.com/posting-api/job-board/%s?includeCompensation=true" % org)
    out = []
    for j in data.get("jobs", []):
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        if not j.get("isListed", True) or not title_ok(j.get("title", "")) or not is_nyc(locs):
            continue
        lo = hi = None
        for c in (j.get("compensation") or {}).get("summaryComponents") or []:
            if c.get("compensationType") == "Salary" and c.get("minValue"):
                lo, hi = c["minValue"], c["maxValue"]
        out.append(_job(source="ashby", external_id="ab-%s" % j["id"], company=company, title=clean(j["title"]),
                        locations=[l for l in locs if l], url=j.get("jobUrl"),
                        posted_at=(j.get("publishedAt") or "")[:10] or None,
                        description=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
                        salary_min=lo, salary_max=hi, workplace=j.get("workplaceType")))
    return out


# ------------------------------------------------------------------ Workday
def workday(company, host, tenant, site, terms, title_ok, log):
    base = "https://%s/wday/cxs/%s/%s" % (host, tenant, site)
    seen, out = set(), []
    for term in terms:
        for offset in (0, 20, 40):
            try:
                data = http_json(base + "/jobs", data={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": term})
            except Exception as e:
                log("  workday %s '%s': %s" % (tenant, term, e))
                break
            posts = data.get("jobPostings") or []
            for p in posts:
                path = p.get("externalPath")
                if not path or path in seen or not title_ok(p.get("title", "")):
                    continue
                seen.add(path)
                lt = p.get("locationsText", "")
                if not (is_nyc(lt) or "Locations" in lt or "new-york" in path.lower()):
                    continue
                try:
                    d = http_json(base + path)["jobPostingInfo"]
                except Exception as e:
                    log("  workday %s detail: %s" % (tenant, e))
                    continue
                locs = [d.get("location", "")] + list(d.get("additionalLocations") or [])
                if not is_nyc(locs):
                    continue
                out.append(_job(source="workday", external_id="wd-%s-%s" % (tenant, d.get("jobReqId") or path),
                                company=company, title=clean(d.get("title")), locations=locs,
                                url=d.get("externalUrl") or ("https://%s/%s%s" % (host, site, path)),
                                posted_at=d.get("startDate"), description=strip_html(d.get("jobDescription"))))
            if len(posts) < 20:
                break
    return out


# ------------------------------------------------------------------ LinkedIn (public guest endpoints)
_LI_CARD = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)".*?base-search-card__title">(.*?)</h3>.*?'
                      r'base-search-card__subtitle">(.*?)</h4>.*?job-search-card__location">(.*?)</span>'
                      r'(.*?)</li>', re.S)


def linkedin(queries, pages, lookback_days, title_ok, company_ok, known, log, delay=1.5):
    out, seen = [], set()
    for q in queries:
        for page in range(pages):
            params = {"keywords": q, "location": "New York, New York, United States", "f_TPR": "r%d" % (lookback_days * 86400),
                      "f_SB2": "5", "f_JT": "F", "start": str(page * 25)}
            url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(params)
            try:
                html = http(url, retries=2)
            except Exception as e:
                log("  linkedin '%s' p%d: %s" % (q, page, e))
                break
            time.sleep(delay)
            cards = _LI_CARD.findall(html)
            for jid, title, comp, loc, rest in cards:
                if jid in seen:
                    continue
                seen.add(jid)
                title, comp, loc = clean(re.sub("<[^>]+>", "", title)), clean(re.sub("<[^>]+>", "", comp)), clean(loc)
                if not title_ok(title) or not is_nyc(loc) or not company_ok(comp):
                    continue
                m = re.search(r'datetime="([\d-]+)"', rest)
                job = dict(source="linkedin", external_id="li-" + jid, company=comp, title=title, locations=[loc],
                           url="https://www.linkedin.com/jobs/view/" + jid, posted_at=m.group(1) if m else None)
                if known("li-" + jid):
                    out.append(dict(job, cached=True))
                    continue
                desc, lo, hi = "", None, None
                try:
                    d = http("https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + jid, retries=2)
                    time.sleep(delay)
                    sm = re.search(r'compensation__salary">(.*?)</div>', d, re.S) or re.search(r'salary-range">(.*?)</', d, re.S)
                    if sm:
                        lo, hi = parse_salary(strip_html(sm.group(1)))
                    dm = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', d, re.S)
                    desc = strip_html(dm.group(1)) if dm else ""
                except Exception as e:
                    log("  linkedin detail %s: %s" % (jid, e))
                out.append(_job(description=desc, salary_min=lo, salary_max=hi, **job))
            if len(cards) < 10:
                break
        log("  linkedin '%s' done (%d roles so far)" % (q, len(out)))
    return out


# ------------------------------------------------------------------ Built In NYC
def builtin(queries, pages, lookback_days, title_ok, log, delay=1.0):
    out, seen = [], set()
    for q in queries:
        for page in range(1, pages + 1):
            url = "https://www.builtinnyc.com/jobs?" + urllib.parse.urlencode(
                {"search": q, "daysSinceUpdated": str(min(lookback_days, 30)), "page": str(page)})
            try:
                html = http(url, retries=2)
            except Exception as e:
                log("  builtin '%s' p%d: %s" % (q, page, e))
                break
            time.sleep(delay)
            chunks = html.split('data-id="job-card"')[1:]
            for ch in chunks:
                tm = re.search(r'href="(/job/[^"]+/(\d+))"[^>]*data-id="job-card-title"[^>]*>(.*?)</a>', ch, re.S)
                cm = re.search(r'href="/company/([^"]+)"[^>]*data-id="company-title"[^>]*><span>(.*?)</span>', ch, re.S)
                if not tm or not cm or tm.group(2) in seen:
                    continue
                seen.add(tm.group(2))
                title = clean(re.sub("<[^>]+>", "", tm.group(3)))
                text = strip_html(ch)
                locm = re.search(r'fa-location-dot.*?<span[^>]*>(.*?)</span>', ch, re.S)
                loc = clean(re.sub("<[^>]+>", "", locm.group(1))) if locm else ""
                if not title_ok(title) or not (is_nyc(loc) or is_nyc(text[:600])):
                    continue
                sal = re.search(r'fa-sack-dollar.*?<span[^>]*>(.*?)</span>', ch, re.S)
                lo, hi = salary_from_k_text(sal.group(1)) if sal else (None, None)
                wp = re.search(r'fa-house-building.*?<span[^>]*>(.*?)</span>', ch, re.S)
                desc_m = re.search(r'id="drop-data-\d+".*', ch, re.S)
                out.append(_job(source="builtin", external_id="bi-" + tm.group(2), company=clean(cm.group(2)),
                                company_slug=cm.group(1), title=title, locations=[loc or "New York, NY"],
                                url="https://www.builtinnyc.com" + tm.group(1), description=strip_html(desc_m.group(0))[:3000] if desc_m else "",
                                salary_min=lo, salary_max=hi, workplace=clean(wp.group(1)) if wp else None))
            if len(chunks) < 20:
                break
    return out


_size_state = {"lookups": 0, "failures": 0}


def builtin_company_size(slug_or_name, log, max_lookups=80):
    """Look up employee count from the company's Built In profile (cached in the DB).

    Returns None when unknown. Stops trying after repeated failures so a slow site can't stall a scan.
    """
    import db
    slug = re.sub(r"[^a-z0-9]+", "-", slug_or_name.lower()).strip("-")
    hit, n = db.cached_size(slug)
    if hit:
        return n
    if _size_state["lookups"] >= max_lookups or _size_state["failures"] >= 5:
        return None
    _size_state["lookups"] += 1
    n = None
    try:
        page = re.sub("<[^>]+>", " ", http("https://www.builtinnyc.com/company/" + slug, retries=1, timeout=8))
        m = re.search(r"([\d,]+)\s*(?:Total\s*)?Employees", page)
        n = int(m.group(1).replace(",", "")) if m else None
        _size_state["failures"] = 0
    except urllib.error.HTTPError as e:
        if e.code not in (404, 410):
            _size_state["failures"] += 1
            return None
    except Exception as e:
        _size_state["failures"] += 1
        log("  builtin size %s: %s" % (slug, e))
        return None
    db.cache_size(slug, n)
    time.sleep(0.4)
    return n


# ------------------------------------------------------------------ Indeed etc. via JSearch (RapidAPI)
def jsearch(queries, api_key, title_ok, log):
    out = []
    for q in queries:
        url = "https://jsearch.p.rapidapi.com/search?" + urllib.parse.urlencode(
            {"query": q + " in New York, NY", "page": "1", "num_pages": "2", "date_posted": "month", "employment_types": "FULLTIME"})
        try:
            data = http_json(url, headers={"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "jsearch.p.rapidapi.com"})
        except Exception as e:
            log("  jsearch '%s': %s" % (q, e))
            continue
        for j in data.get("data") or []:
            title = clean(j.get("job_title"))
            loc = ", ".join(filter(None, [j.get("job_city"), j.get("job_state")]))
            if not title_ok(title) or not is_nyc(loc):
                continue
            pub = (j.get("job_publisher") or "").strip()
            lo, hi = j.get("job_min_salary"), j.get("job_max_salary")
            if lo and (j.get("job_salary_period") or "").upper() == "HOUR":
                lo, hi = lo * 2080, (hi or lo) * 2080
            out.append(_job(source="indeed" if "indeed" in pub.lower() else "jsearch", external_id="js-%s" % j.get("job_id"),
                            company=clean(j.get("employer_name")), title=title, locations=[loc],
                            url=j.get("job_apply_link"), posted_at=(j.get("job_posted_at_datetime_utc") or "")[:10] or None,
                            description=j.get("job_description") or "", salary_min=lo and int(lo), salary_max=hi and int(hi)))
    return out


def jsearch_key(cfg):
    return os.environ.get(cfg.get("jsearch_api_key_env", "JSEARCH_API_KEY"), "").strip()
