"""Curated directory of larger companies hiring in NYC.

Each entry: name, employees (approximate headcount), wlb (1-5 work-life-balance
estimate based on general employee-review reputation -- tweak freely), and an
optional ATS feed that is polled directly ("native company site").

ats formats:
  ("greenhouse", board_token)
  ("lever", company_slug)
  ("ashby", org_slug)
  ("workday", host, tenant, site)
"""

COMPANIES = [
    # --- Greenhouse boards ---
    dict(name="Anthropic", employees=2500, wlb=3.6, ats=("greenhouse", "anthropic")),
    dict(name="Datadog", employees=6500, wlb=3.6, ats=("greenhouse", "datadog")),
    dict(name="MongoDB", employees=5000, wlb=3.9, ats=("greenhouse", "mongodb")),
    dict(name="Stripe", employees=8500, wlb=3.2, ats=("greenhouse", "stripe")),
    dict(name="Airbnb", employees=7000, wlb=4.1, ats=("greenhouse", "airbnb")),
    dict(name="Pinterest", employees=4500, wlb=4.0, ats=("greenhouse", "pinterest")),
    dict(name="Squarespace", employees=1700, wlb=3.8, ats=("greenhouse", "squarespace")),
    dict(name="Databricks", employees=8000, wlb=3.5, ats=("greenhouse", "databricks")),
    dict(name="Cloudflare", employees=4500, wlb=3.8, ats=("greenhouse", "cloudflare")),
    dict(name="Okta", employees=6000, wlb=3.8, ats=("greenhouse", "okta")),
    dict(name="Twilio", employees=5500, wlb=3.9, ats=("greenhouse", "twilio")),
    dict(name="Duolingo", employees=1000, wlb=4.0, ats=("greenhouse", "duolingo")),
    dict(name="Peloton", employees=3000, wlb=3.3, ats=("greenhouse", "peloton")),
    dict(name="Oscar Health", employees=2500, wlb=3.6, ats=("greenhouse", "oscar"), aliases=["oscar"]),
    dict(name="Zocdoc", employees=1000, wlb=3.8, ats=("greenhouse", "zocdoc")),
    dict(name="Braze", employees=1700, wlb=3.8, ats=("greenhouse", "braze")),
    dict(name="Figma", employees=1700, wlb=4.0, ats=("greenhouse", "figma")),
    dict(name="Asana", employees=1800, wlb=4.1, ats=("greenhouse", "asana")),
    dict(name="Dropbox", employees=2500, wlb=4.2, ats=("greenhouse", "dropbox")),
    dict(name="Robinhood", employees=2500, wlb=3.4, ats=("greenhouse", "robinhood")),
    dict(name="Coinbase", employees=3800, wlb=3.4, ats=("greenhouse", "coinbase")),
    dict(name="Affirm", employees=2200, wlb=3.9, ats=("greenhouse", "affirm")),
    dict(name="Brex", employees=1100, wlb=3.2, ats=("greenhouse", "brex")),
    dict(name="Chime", employees=1500, wlb=3.8, ats=("greenhouse", "chime")),
    dict(name="GitLab", employees=2100, wlb=4.2, ats=("greenhouse", "gitlab")),
    dict(name="Elastic", employees=3000, wlb=4.2, ats=("greenhouse", "elastic")),
    dict(name="Samsara", employees=3500, wlb=3.4, ats=("greenhouse", "samsara")),
    dict(name="Scale AI", employees=1000, wlb=2.6, ats=("greenhouse", "scaleai")),
    dict(name="Glean", employees=1000, wlb=3.5, ats=("greenhouse", "gleanwork")),
    dict(name="Betterment", employees=1000, wlb=3.9, ats=("greenhouse", "betterment")),
    dict(name="Justworks", employees=1000, wlb=4.1, ats=("greenhouse", "justworks")),
    dict(name="Lyft", employees=3000, wlb=3.8, ats=("greenhouse", "lyft")),
    dict(name="DoorDash", employees=20000, wlb=3.0, ats=("greenhouse", "doordashusa")),
    dict(name="Instacart", employees=3500, wlb=3.8, ats=("greenhouse", "instacart"), aliases=["maplebear"]),
    dict(name="Reddit", employees=2000, wlb=3.9, ats=("greenhouse", "reddit")),
    dict(name="Discord", employees=1000, wlb=4.0, ats=("greenhouse", "discord")),
    dict(name="Gusto", employees=2500, wlb=4.1, ats=("greenhouse", "gusto")),
    dict(name="Carta", employees=1500, wlb=3.3, ats=("greenhouse", "carta")),
    dict(name="Toast", employees=5500, wlb=3.7, ats=("greenhouse", "toast")),
    dict(name="Flatiron Health", employees=2000, wlb=4.0, ats=("greenhouse", "flatironhealth")),
    dict(name="Attentive", employees=1000, wlb=3.3, ats=("greenhouse", "attentive")),
    dict(name="Yext", employees=1100, wlb=3.6, ats=("greenhouse", "yext")),
    dict(name="Intercom", employees=1200, wlb=3.7, ats=("greenhouse", "intercom")),
    dict(name="Airtable", employees=1000, wlb=3.8, ats=("greenhouse", "airtable")),
    dict(name="PagerDuty", employees=1200, wlb=4.0, ats=("greenhouse", "pagerduty")),
    dict(name="Roblox", employees=2500, wlb=3.8, ats=("greenhouse", "roblox")),
    dict(name="The New York Times", employees=5900, wlb=4.0, ats=("greenhouse", "thenewyorktimes"), aliases=["new york times", "nytimes"]),
    dict(name="Block", employees=11000, wlb=3.8, ats=("greenhouse", "block"), aliases=["square", "cash app", "block inc"]),
    dict(name="New Relic", employees=2500, wlb=3.9, ats=("greenhouse", "newrelic")),
    dict(name="Adyen", employees=4000, wlb=3.6, ats=("greenhouse", "adyen")),
    dict(name="Fivetran", employees=1200, wlb=3.8, ats=("greenhouse", "fivetran")),
    dict(name="Mixpanel", employees=1000, wlb=3.9, ats=("greenhouse", "mixpanel")),
    dict(name="Mercury", employees=1000, wlb=3.7, ats=("ashby", "mercury")),
    # --- Lever ---
    dict(name="Spotify", employees=7300, wlb=4.2, ats=("lever", "spotify")),
    dict(name="Palantir", employees=4000, wlb=3.3, ats=("lever", "palantir"), aliases=["palantir technologies"]),
    # --- Ashby ---
    dict(name="OpenAI", employees=4500, wlb=3.0, ats=("ashby", "openai")),
    dict(name="Ramp", employees=1200, wlb=2.8, ats=("ashby", "ramp")),
    dict(name="Notion", employees=1000, wlb=3.7, ats=("ashby", "notion")),
    dict(name="Snowflake", employees=7500, wlb=3.6, ats=("ashby", "snowflake")),
    dict(name="Confluent", employees=3000, wlb=3.9, ats=("ashby", "confluent")),
    dict(name="Deel", employees=4000, wlb=3.0, ats=("ashby", "deel")),
    # --- Workday career sites ---
    dict(name="Mastercard", employees=33000, wlb=4.0, ats=("workday", "mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers")),
    dict(name="Capital One", employees=52000, wlb=4.0, ats=("workday", "capitalone.wd12.myworkdayjobs.com", "capitalone", "Capital_One")),
    dict(name="Salesforce", employees=72000, wlb=3.9, ats=("workday", "salesforce.wd12.myworkdayjobs.com", "salesforce", "External_Career_Site")),
    dict(name="Adobe", employees=30000, wlb=4.1, ats=("workday", "adobe.wd5.myworkdayjobs.com", "adobe", "external_experienced")),
    dict(name="Workday", employees=19000, wlb=4.1, ats=("workday", "workday.wd5.myworkdayjobs.com", "workday", "Workday")),
    dict(name="PayPal", employees=24000, wlb=3.9, ats=("workday", "paypal.wd1.myworkdayjobs.com", "paypal", "jobs")),
    dict(name="BlackRock", employees=21000, wlb=3.6, ats=("workday", "blackrock.wd1.myworkdayjobs.com", "blackrock", "BlackRock_Professional")),
    dict(name="S&P Global", employees=40000, wlb=3.9, ats=("workday", "spgi.wd5.myworkdayjobs.com", "spgi", "SPGI_Careers"), aliases=["s&p global", "sp global", "s and p global"]),
    dict(name="Nasdaq", employees=9000, wlb=3.9, ats=("workday", "nasdaq.wd1.myworkdayjobs.com", "nasdaq", "Global_External_Site")),
    dict(name="Thomson Reuters", employees=26000, wlb=4.1, ats=("workday", "thomsonreuters.wd5.myworkdayjobs.com", "thomsonreuters", "External_Career_Site")),
    dict(name="Broadridge", employees=15000, wlb=3.7, ats=("workday", "broadridge.wd5.myworkdayjobs.com", "broadridge", "Careers")),
    dict(name="Disney", employees=230000, wlb=3.7, ats=("workday", "disney.wd5.myworkdayjobs.com", "disney", "disneycareer"), aliases=["the walt disney company", "walt disney"]),
    dict(name="Citi", employees=230000, wlb=3.6, ats=("workday", "citi.wd5.myworkdayjobs.com", "citi", "2"), aliases=["citigroup", "citibank"]),
    dict(name="SS&C Technologies", employees=27000, wlb=3.2, ats=("workday", "ssctech.wd1.myworkdayjobs.com", "ssctech", "SSCTechnologies"), aliases=["ss&c", "ssc technologies", "blue prism"]),
    dict(name="FIS", employees=50000, wlb=3.5, ats=("workday", "fis.wd5.myworkdayjobs.com", "fis", "SearchJobs"), aliases=["fis global", "fidelity national information services"]),

    # --- Known large companies without a polled feed (matched on LinkedIn / Built In results) ---
    dict(name="Google", employees=180000, wlb=4.2),
    dict(name="Microsoft", employees=220000, wlb=4.0),
    dict(name="Amazon", employees=1500000, wlb=3.1, aliases=["amazon web services", "aws", "amazon web services (aws)"]),
    dict(name="Meta", employees=70000, wlb=3.6),
    dict(name="Apple", employees=160000, wlb=3.9),
    dict(name="IBM", employees=280000, wlb=4.0),
    dict(name="Oracle", employees=160000, wlb=3.8),
    dict(name="Bloomberg", employees=21000, wlb=3.8, aliases=["bloomberg lp"]),
    dict(name="JPMorgan Chase", employees=310000, wlb=3.6, aliases=["jpmorganchase", "jpmorgan chase & co", "j.p. morgan", "jpmorgan"]),
    dict(name="Goldman Sachs", employees=46000, wlb=3.0),
    dict(name="Morgan Stanley", employees=80000, wlb=3.4),
    dict(name="American Express", employees=75000, wlb=4.1, aliases=["amex"]),
    dict(name="Visa", employees=30000, wlb=4.1),
    dict(name="Atlassian", employees=12000, wlb=4.3),
    dict(name="HubSpot", employees=8000, wlb=4.2),
    dict(name="ServiceNow", employees=26000, wlb=4.1),
    dict(name="Etsy", employees=2400, wlb=4.1),
    dict(name="Uber", employees=31000, wlb=3.6),
    dict(name="Netflix", employees=14000, wlb=3.7),
    dict(name="LinkedIn", employees=20000, wlb=4.3),
    dict(name="Cisco", employees=85000, wlb=4.2),
    dict(name="Intuit", employees=18000, wlb=4.1),
    dict(name="Plaid", employees=1200, wlb=3.8),
    dict(name="Rippling", employees=3500, wlb=2.8),
    dict(name="Moody's", employees=15000, wlb=4.0, aliases=["moodys", "moody's corporation", "moody's analytics"]),
    dict(name="Two Sigma", employees=2000, wlb=3.9),
    dict(name="Citadel", employees=3000, wlb=2.8),
    dict(name="Verizon", employees=100000, wlb=3.9),
    dict(name="Accenture", employees=770000, wlb=3.5),
    dict(name="Deloitte", employees=460000, wlb=3.4),
    dict(name="NVIDIA", employees=36000, wlb=3.9),
    dict(name="Shopify", employees=8000, wlb=3.8),
    dict(name="Zendesk", employees=6000, wlb=4.0),
    dict(name="Fidelity Investments", employees=75000, wlb=4.1, aliases=["fidelity"]),
    dict(name="Wells Fargo", employees=220000, wlb=3.6),
    dict(name="Bank of America", employees=213000, wlb=3.7),
    dict(name="Paramount", employees=20000, wlb=3.7),
    dict(name="Warner Bros. Discovery", employees=35000, wlb=3.6),
]

_SUFFIXES = (" incorporated", " inc", " llc", " ltd", " corp", " corporation", " co", " plc", " lp", " holdings", " technologies inc", " group")


def norm_company(name):
    import re
    s = (name or "").lower().replace("&amp;", "&").strip()
    s = re.sub(r"[.,()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    changed = True
    while changed:
        changed = False
        for suf in _SUFFIXES:
            if s.endswith(suf):
                s = s[: -len(suf)].strip()
                changed = True
    return s


_INDEX = {}
for _c in COMPANIES:
    for _n in [_c["name"]] + _c.get("aliases", []):
        _INDEX.setdefault(norm_company(_n), _c)


def lookup(name):
    """Return the directory entry for a company name, or None."""
    return _INDEX.get(norm_company(name))


# Domains that can't be guessed as "<name>.com" (used for logos).
DOMAINS = {
    "anthropic": "anthropic.com", "capital one": "capitalone.com", "s&p global": "spglobal.com", "the new york times": "nytimes.com",
    "block": "block.xyz", "oscar health": "hioscar.com", "scale ai": "scale.com", "glean": "glean.com", "flatiron health": "flatiron.com",
    "citi": "citi.com", "ss&c technologies": "ssctech.com", "fis": "fisglobal.com", "thomson reuters": "thomsonreuters.com",
    "jpmorgan chase": "jpmorganchase.com", "goldman sachs": "goldmansachs.com", "morgan stanley": "morganstanley.com",
    "american express": "americanexpress.com", "bank of america": "bankofamerica.com", "wells fargo": "wellsfargo.com",
    "two sigma": "twosigma.com", "moody's": "moodys.com", "warner bros discovery": "wbd.com", "fidelity investments": "fidelity.com",
    "notion": "notion.so", "new relic": "newrelic.com", "doordash": "doordash.com", "palantir": "palantir.com", "meta": "meta.com",
    "the walt disney company": "disney.com", "disney": "disney.com", "linear": "linear.app", "deel": "deel.com",
    "nvidia": "nvidia.com", "servicenow": "servicenow.com", "pagerduty": "pagerduty.com", "toast": "toasttab.com",
    "mercury": "mercury.com", "ramp": "ramp.com", "brex": "brex.com", "chime": "chime.com", "carta": "carta.com",
}


def domain_for(name):
    """Best-guess website domain for a company (directory override, else '<name>.com')."""
    import re
    entry = lookup(name)
    key = norm_company(entry["name"] if entry else name)
    if key in DOMAINS:
        return DOMAINS[key]
    slug = re.sub(r"[^a-z0-9]", "", key)
    return slug + ".com" if slug else None


def feeds():
    return [c for c in COMPANIES if c.get("ats")]
