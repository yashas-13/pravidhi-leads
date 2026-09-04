# pravidhi-leads

Buyer lead database — SMEs actively needing IT services (MSP, cloud migration, cybersecurity, helpdesk, managed IT, dev, infrastructure).

**Goal:** Find companies/people who are BUYERS (need IT providers), NOT providers selling IT services.

## Quick Start

```bash
# Latest clean leads (buyer intent only, no noise)
cat processed/FREE_BUYERS_CLEAN.csv | head -20

# Govt RFPs with contact emails/phones
cat govt-rfp/HOT_BUYER_RFPS.csv

# Raw data (all sources, unfiltered)
cat raw/FREE_BUYERS.csv | wc -l   # 206 total
```

## Directory Structure

Every CSV has a matching `.md` file — read on GitHub or any editor without opening a spreadsheet.

```
pravidhi-leads/
├── README.md                  ← you are here
├── raw/                       ← unfiltered scraper outputs + readable .md views
│   ├── README.md              ← overview table of all raw files
│   ├── FREE_BUYERS.csv        ← 206 leads (HN + Remotive + Arbeitnow + USAspending + DDG)
│   ├── FREE_BUYERS.md         ← readable version
│   ├── stealth_buyers.csv/.md ← 106 leads (DDG lite + HN + Remotive)
│   ├── all_buyers_final.csv/.md ← 64 leads (HN + USAspending + Remotive)
│   ├── BUYERS_CLEAN.csv/.md   ← 23 buyer-intent HN posts (filtered)
│   ├── buyers_hot2.csv/.md    ← 36 leads from intermediate runs
│   └── dork_leads*.csv/.md    ← IndiaMART/JustDial provider listings (noisy)
├── processed/                 ← cleaned & enriched (segmented .md views)
│   ├── FREE_BUYERS_CLEAN.csv  ← 164 buyer leads (buyer intent + govt + hiring)
│   ├── FREE_BUYERS_CLEAN.md   ← index: links to all segments
│   ├── FREE_BUYERS_CLEAN-buyers.md   ← 95 buyer-intent leads
│   ├── FREE_BUYERS_CLEAN-govt.md     ← 29 govt/tender leads
│   └── FREE_BUYERS_CLEAN-hiring.md   ← 40 hiring=outsourcing leads
├── govt-rfp/                  ← government RFPs (verified real buyers)
│   ├── HOT_BUYER_RFPS.csv     ← 9 RFPs with emails + phones
│   ├── HOT_BUYER_RFPS.jsonl
│   └── HOT_BUYER_RFPS.md      ← card-style readable RFPs
└── internal-scripts/          ← scraper code (for reruns)
    ├── free_harvest.py        ← main scraper (DDG lite + APIs) — RUN THIS
    ├── stealth_leads.py       ← DDG lite + real page fetch
    ├── hot_leads_extract.py   ← RFP PDF parser (Jina reader)
    ├── all_leads.py           ← first-gen aggregator
    └── buyers_hunt.py         ← initial DDG/Brave scraper
```

## Data Schema (CSV columns)

| Column | Description |
|---|---|
| `source` | Where the lead came from (hn_algolia, remotive, arbeitnow, ddg, usaspending) |
| `company` | Company name (or HN username) |
| `title` | Post/job title |
| `url` | Original source URL |
| `snippet` | First 500 chars of description |
| `emails_page` | Extracted email(s) from page — comma-separated |
| `phones_page` | Extracted phone(s) from page — comma-separated |
| `dork` | Search query that found this lead |

**Govt RFP columns** (HOT_BUYER_RFPS.csv):

| Column | Description |
|---|---|
| `buyer` | Entity name (City of Peosta, CLASP, etc.) |
| `title` | What they're buying (Managed IT Services, etc.) |
| `contact_person` | Named contact (Sara Santor, Kaneisha Hall, etc.) |
| `emails` | Contact email |
| `phones` | Contact phone |
| `deadline` | RFP submission deadline (if available) |
| `url` | PDF link to full RFP |

## How to Rerun

```bash
cd internal-scripts/
python3 free_harvest.py   # main harvest — takes ~3 min, outputs FREE_BUYERS.csv
```

## Sources (all free, no auth)

| Source | Type | Rate Limit | Status |
|---|---|---|---|
| DDG lite | Search engine | ~50 queries/day | ✅ |
| HN Algolia | API | Unlimited | ✅ |
| Remotive | API | Unlimited | ✅ |
| Arbeitnow | API | Unlimited | ✅ |
| USAspending.gov | API | Unlimited (POST) | ✅ |
| Jina reader | Web reader | ~20/page | ✅ |
| Reddit | Search | Needs OAuth | ❌ |
| LinkedIn | Search | Needs Playwright | ❌ |
| Indeed | Search | Needs Playwright | ❌ |

## Coverage (as of 2026-09-04)

| Metric | Count | Read now |
|---|---|---|
| Total leads (raw) | 206 | [`raw/FREE_BUYERS.md`](raw/FREE_BUYERS.md) |
| Buyer intent (filtered) | 95 | [`processed/FREE_BUYERS_CLEAN-buyers.md`](processed/FREE_BUYERS_CLEAN-buyers.md) |
| Govt RFPs (active) | 29 | [`processed/FREE_BUYERS_CLEAN-govt.md`](processed/FREE_BUYERS_CLEAN-govt.md) |
| Companies hiring IT (= outsourcing) | 40 | [`processed/FREE_BUYERS_CLEAN-hiring.md`](processed/FREE_BUYERS_CLEAN-hiring.md) |
| Verified govt RFPs w/ contact | 9 | [`govt-rfp/HOT_BUYER_RFPS.md`](govt-rfp/HOT_BUYER_RFPS.md) |
| Leads with verified email | 13 | search in any `.md` |
| Leads with phone | 77 | search in any `.md` |


## Rerun Instructions

When ready to refresh leads:

1. `python3 internal-scripts/free_harvest.py` — main scraper
2. Move `FREE_BUYERS.csv` → `raw/`
3. Rerun filter → `FREE_BUYERS_CLEAN.csv` → `processed/`
4. `python3 internal-scripts/hot_leads_extract.py` — RFP parser
5. Move `HOT_BUYER_RFPS.csv` → `govt-rfp/`
6. `git add && git commit -m "leads: refresh $(date +%Y-%m-%d)"`

## Notes

- DDG lite works from any IP, just decode redirect URLs (`uddg=` parameter)
- Phone numbers from HN posts are HN item IDs, not real phones — filter by `dork` column
- Govt RFPs are the highest quality leads (real budget, real deadline, named contact)
- For Reddit/LinkedIn leads, need Playwright + real browser on non-mobile IP
