"""Role matching and scoring: resume fit, work-life balance, salary, company size."""
import re


class Matcher:
    def __init__(self, cfg):
        self.cfg = cfg
        self.roles = [(cat, re.compile("|".join(p), re.I)) for cat, p in cfg["role_patterns"].items()]
        self.exclude = re.compile("|".join(cfg["exclude_title_patterns"]), re.I)
        self.senior = re.compile("|".join(cfg["senior_title_patterns"]), re.I)
        self.kw = {k.lower(): w for k, w in cfg["resume_keywords"].items()}
        alts = "|".join(re.escape(k) for k in sorted(self.kw, key=len, reverse=True))
        self.kw_rx = re.compile(r"(?<![a-z])(" + alts + r")(?![a-z])")
        self.pos = [k.lower() for k in cfg["wlb_positive"]]
        self.neg = [k.lower() for k in cfg["wlb_negative"]]

    def category(self, title):
        if not title or self.exclude.search(title):
            return None
        for cat, rx in self.roles:
            if rx.search(title):
                # "Software Engineer, Solutions Engineering" is a pure SWE role unless it's forward deployed
                if cat != "Forward Deployed" and re.search(r"(?i)software engineer|data engineer", title):
                    return None
                return cat
        return None

    def title_ok(self, title):
        return self.category(title) is not None

    def evaluate(self, job, company):
        """Return the scored/flagged fields for a raw job. `company` is the directory entry or None."""
        cfg = self.cfg
        title, desc = job["title"], job.get("description") or ""
        low = desc.lower()
        cat = self.category(title)
        reasons, flags = [], []

        # --- resume fit
        fit = {"Forward Deployed": 34, "Solutions Engineering": 32, "Product Management": 26}.get(cat, 0)
        hits = [(k, self.kw[k]) for k in set(self.kw_rx.findall(low))]
        fit += min(sum(w for _, w in hits) * 1.6, 46)
        matched = [k for k, _ in sorted(hits, key=lambda h: -h[1])[:6]]
        if matched:
            reasons.append("Matches your background: " + ", ".join(matched))
        senior = bool(self.senior.search(title))
        ylo, yhi, ysrc = required_years(title, desc, senior)
        exp, flex = cfg["experience_years"], cfg["experience_flex"]
        exp_ok = experience_ok(ylo, yhi, cfg)
        if ylo is None:
            flags.append("years-unstated")
            reasons.append("Years of experience not stated")
        else:
            label = ("%d–%d yrs" % (ylo, yhi)) if yhi is not None and yhi != ylo else ("%d+ yrs" % ylo)
            reasons.append("Asks for %s%s" % (label, " (implied by title)" if ysrc == "title" else ""))
            if exp_ok:
                fit += 14 - 4 * abs(ylo - exp)
            else:
                flags.append("too-senior" if ylo > exp + flex else "too-junior")
        if senior:
            flags.append("senior-title")
        fit = max(0, min(100, round(fit)))

        # --- work-life balance
        rating = company.get("wlb") if company else None
        wlb = (rating if rating else 3.4) / 5 * 72
        pos = [k for k in self.pos if k in low]
        neg = [k for k in self.neg if k in low]
        wlb += min(len(pos) * 5, 20) - min(len(neg) * 7, 35)
        if (job.get("workplace") or "").lower() in ("hybrid",) or "hybrid" in low:
            wlb += 4
        wlb = max(0, min(100, round(wlb)))
        if rating:
            reasons.append("Employer WLB rating ~%.1f/5" % rating)
        if pos:
            reasons.append("WLB perks: " + ", ".join(pos[:4]))
        if neg:
            reasons.append("Watch out: " + ", ".join(neg[:4]))
            flags.append("wlb-warning")
        tm = re.search(r"travel[^.\n]{0,40}?(\d{2})\s*%|(\d{2})\s*%[^.\n]{0,25}travel", low)
        if tm:
            pct = int(tm.group(1) or tm.group(2))
            reasons.append("Travel ~%d%%" % pct)
            if pct >= 30:
                wlb = max(0, wlb - 10)
                flags.append("travel")

        # --- salary
        lo, hi = job.get("salary_min"), job.get("salary_max")
        if lo and not hi:
            hi = lo
        basis = None
        if lo:
            basis = {"min": lo, "max": hi}.get(cfg["salary_basis"], (lo + hi) / 2)
            sal_score = max(0, min(100, round((basis - 100000) / 150000 * 100)))
        else:
            sal_score = 30
            flags.append("no-salary")

        # --- size
        emp = job.get("employees") or (company.get("employees") if company else None)
        if not emp:
            flags.append("size-unknown")

        if re.search(r"security clearance|active clearance|ts/sci|top secret", low):
            flags.append("clearance")
            reasons.append("Requires security clearance")

        passes = (bool(cat)
                  and ((basis is not None and basis >= cfg["min_salary"]) or (basis is None and cfg["include_no_salary"]))
                  and ((emp is not None and emp >= cfg["min_employees"]) or (emp is None and cfg["include_unknown_size"]))
                  and exp_ok and wlb >= cfg["min_wlb_score"] and "clearance" not in flags)

        score = round(0.45 * fit + 0.35 * wlb + 0.20 * sal_score)
        return dict(category=cat, fit_score=fit, wlb_score=wlb, salary_score=sal_score, score=score,
                    employees=emp, wlb_rating=rating, years_required=ylo, years_max=yhi, senior=int(senior),
                    passes=int(passes), flags=flags, reasons=reasons)


# ---------------------------------------------------------------- experience
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_N = r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"
_YEARS = re.compile(
    r"(?:(?:at least|minimum of|min\.?|minimum|over|more than)\s+)?" + _N
    + r"(?:\s*(?:-|–|—|to)\s*" + _N + r")?\s*(\+|\s*or more)?\s*(?:\(\d+\)\s*)?years?", re.I)
_OPTIONAL = re.compile(r"(?i)prefer|bonus|nice to have|nice-to-have|a plus|ideally|desired")
_OPTIONAL_HEADING = re.compile(r"preferred qualifications|preferred skills|nice to have|nice-to-have|bonus points|added plus|pluses|preferred:")
_JUNIOR_TITLE = re.compile(r"(?i)\bassociate\b|\bjunior\b|\bjr\.?\b|new grad|early career|\bentry\b|\b(?:I|1)$")


def _num(t):
    return int(t) if t.isdigit() else _WORDS[t.lower()]


def required_years(title, desc, senior_title):
    """Minimum (and optional maximum) years of experience a posting asks for.

    Returns (lo, hi, source) where hi is None for open-ended "N+" and source is
    "posting", "title" (inferred from Senior/Associate etc.) or None when unknown.
    """
    best = None
    for m in _YEARS.finditer(desc or ""):
        after = re.split(r"[.;\n]", desc[m.end(): m.end() + 70].lower())[0]
        before = re.split(r"[.;\n]", desc[max(0, m.start() - 40): m.start()].lower())[-1]
        open_ended = bool(m.group(2) or m.group(3))  # "3+ years", "3-5 years", "3 or more years"
        if re.match(r"\s*(ago|old|of age|later)", after):
            continue
        if not open_ended and "experience" not in after and "experience" not in before:
            continue
        if open_ended and not re.match(r"\s*(of|in|as|working|building|shipping|leading|managing|with|experience|professional|relevant|industry|hands|\w+ experience)", after):
            continue
        line_start = desc.rfind("\n", 0, m.start()) + 1
        heading = desc[max(0, m.start() - 160): m.start()].lower()
        if _OPTIONAL.search(desc[line_start: m.start()]) or _OPTIONAL_HEADING.search(heading):
            continue
        lo = _num(m.group(1))
        hi = _num(m.group(2)) if m.group(2) else None
        if not 0 <= lo <= 15 or (hi is not None and not lo <= hi <= 20):
            continue
        # The requirement that matters is the largest minimum (e.g. "5+ years overall, 2+ in SaaS" -> 5).
        if best is None or lo > best[0]:
            best = (lo, hi)
    if best:
        return best[0], best[1], "posting"
    if senior_title:
        return 5, None, "title"
    if _JUNIOR_TITLE.search(title or ""):
        return 0, 2, "title"
    return None, None, None


def experience_ok(lo, hi, cfg):
    """Does the posting's required range overlap [experience - flex, experience + flex]?"""
    exp, flex = cfg["experience_years"], cfg["experience_flex"]
    if lo is None:
        return cfg["include_unstated_years"]
    return lo <= exp + flex and (hi is None or hi >= exp - flex)
