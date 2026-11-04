# Job Radar

A local web app that scans for NYC forward deployed, solutions engineering and product roles every two weeks. It ranks them against your resume and work-life balance. It never applies to anything; it only lists jobs.

## Run it

```bash
python3 server.py          # open http://localhost:8787, click "Scan now"
./install.sh               # optional: keep it running at login and scan every 14 days
```

You only need the Python 3 that ships with macOS; there are no packages to install.

## Desktop app (Electron)

```bash
cd electron && npm install && npm run package   # builds electron/dist/Job Radar-darwin-arm64/Job Radar.app
```

Drag **Job Radar.app** into Applications. When you open it, the scanner starts in the background and the dashboard opens in a window.

- Closing the window keeps the app running in the menu bar (radar icon), so the scan every 14 days still happens.
- The first time you open it, the app adds itself to Login Items. You can turn this off with **Launch at Login** in the menu bar menu.
- The database, digests and `settings.json` (your Preferences) are in `~/Library/Application Support/Job Radar/data/`; **Open Settings Folder** in the menu takes you there. Put a `.env` there for email or JSearch keys.
- `npm start` runs the app straight from source for development.
- The app isn't code-signed. The first time, right-click it and choose **Open**.

## Where jobs come from

| Source | How |
|---|---|
| Company career sites | Public Greenhouse, Lever, Ashby and Workday job feeds for ~75 larger companies (see `companies.py`) |
| LinkedIn | Public guest job search: NYC, past 3 weeks, $120K+ salary filter, full-time |
| Built In NYC | Job search pages, with company size looked up from Built In profiles |
| Indeed | Indeed blocks automated access. To include it, get a free [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) key and add `JSEARCH_API_KEY=...` to `.env`. JSearch aggregates Indeed, LinkedIn and Glassdoor |

## Filtering and ranking

- **Roles**: title patterns in `config.json` → `role_patterns`. Director, VP, Head of, Staff, Principal, intern and contract titles are excluded.
- **NYC only**: the posting must list a New York City location.
- **Experience**: the posting's required years (e.g. "3+ years", "2–4 years", or implied by Senior/Associate titles) must overlap your level ± flexibility. Set both in **Preferences**; the default is 2 years ± 1.
- **Pay**: the salary range midpoint must be at least `min_salary` (120,000). NYC's pay-transparency law means most postings include a range.
- **Larger company**: at least `min_employees` (1,000) employees.
- **Overall score** = 45% resume fit + 35% work-life balance + 20% salary.
  - *Fit*: role type, keywords from your resume (APIs/SDKs, integrations, SQL/Python, client-facing, …) and years of experience asked for.
  - *Work-life balance*: a 1–5 employer rating in `companies.py` (an estimate from employee-review reputation, so adjust it to your own view), plus positive/negative phrases in the posting (e.g. "flexible", "unlimited PTO" vs "fast-paced", "on-call", "50% travel").

Use the **Preferences** panel for experience, minimum salary and minimum work-life balance; changes re-rank saved jobs instantly. For role patterns and keywords, edit `config.json` or `companies.py`.

## Make it yours

`config.json` holds generic defaults. Put your own values in `data/settings.json` (or `~/Library/Application Support/Job Radar/data/settings.json` for the desktop app). Keys there override the defaults, and the file is never committed. Useful ones are `resume_keywords` (skills from your resume, with weights), `experience_years`, and `email`.

Sites' terms differ on automated access, including LinkedIn's and Built In's. This is a personal tool that only reads public listings at a low rate; check each site's terms before you run it, and disable any source you aren't comfortable with.

## Email digest (optional)

Every scan writes `data/digests/digest-YYYY-MM-DD.html` and shows a macOS notification. To email it as well, create a Gmail [app password](https://myaccount.google.com/apppasswords) and:

1. Add `JOBRADAR_SMTP_PASSWORD=your-app-password` to `.env`.
2. In `settings.json`, set `"email"` with `"enabled": true`, `"to"`, `"smtp_user"` and the other fields shown in `config.json`.

## Files

`server.py` (web app + scheduler) · `scan.py` (scanner; `python3 scan.py --if-due` from cron works too) · `sources.py` · `scoring.py` · `db.py` (SQLite at `data/jobradar.db`) · `static/index.html`
