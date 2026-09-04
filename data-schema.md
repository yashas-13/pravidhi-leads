# Data Schema — pravidhi-leads

## Standard Lead Format (all CSV/JSONL except govt-rfp)

```json
{
  "source": "hn_algolia",
  "company": "andrewljohnson",
  "title": "Ask HN: What do you use to invoice people?",
  "url": "https://news.ycombinator.com/item?id=1082336",
  "snippet": "Any answer would be good, but I am looking for something simple...",
  "emails_page": "andrewljohnson@gmail.com",
  "phones_page": "1082656, 1082336",
  "dork": "hn:need IT support"
}
```

### Field Definitions

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | string | ✅ | Enum: `hn_algolia`, `remotive`, `arbeitnow`, `ddg`, `usaspending`, `stealth` |
| `company` | string | ❌ | Empty string if unknown (HN username goes here) |
| `title` | string | ✅ | Post title, job title, or page title (truncated 250 chars) |
| `url` | string | ✅ | Original source URL (dedup key) |
| `snippet` | string | ❌ | First 500 chars of description/content |
| `emails_page` | string | ❌ | Comma-separated extracted emails (blocked list filtered) |
| `phones_page` | string | ❌ | Comma-separated extracted phones (7-15 digits) |
| `dork` | string | ❌ | Search query or API category that found this lead |

### Source-Specific Notes

| Source | `company` value | `dork` value | Notes |
|---|---|---|---|
| `hn_algolia` | HN author username | `hn:<query>` | Phones are HN item IDs — NOT real phones |
| `remotive` | Company name | Job category | Only IT-relevant jobs filtered |
| `arbeitnow` | Company name | Job tags | German/EU job board |
| `ddg` | "" (empty) | Search query | Real page fetched, contacts extracted |
| `usaspending` | Recipient name | NAICS code | Govt contract awards (NAICS 541511/541512/541519) |

### Email/Phone Extraction Rules

**Emails:**
- Regex: `[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}`
- Blocked domains: `example.com`, `sentry.io`, `wixpress`, `schema.org`, `w3.org`, `gravatar.com`, `googleapis.com`, `hubspot.com`, `zoho.com`, `mailchimp.com`, `sendgrid.net`, `mailgun.com`, `amazonses.com`, `facebook.com`, `twitter.com`, `linkedin.com`
- Removed file extensions: `.png`, `.jpg`, `.gif`, `.svg`, `.webp`, `.woff`, `.css`, `.js`

**Phones:**
- Regex: `(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}`
- Valid if 7-15 digits after removing non-digits
- HN item IDs (e.g., `1082336`) appear as false positives — filter by `source`

---

## Govt RFP Format (govt-rfp/HOT_BUYER_RFPS.csv)

```json
{
  "buyer": "City of Peosta IA",
  "title": "Managed IT Services RFP",
  "contact_person": "7896 Burds Road Peosta, Iowa 52068 PHONE: 563-556-8755, Ext. 100 E-MAIL: aekhoff@cityofpeosta.org",
  "emails": "aekhoff@cityofpeosta.org",
  "phones": "563-556-8755",
  "deadline": "",
  "url": "https://www.cityofpeosta.org/uploads/documents/IT_Services_RFP.pdf"
}
```

### Field Definitions

| Field | Type | Required | Notes |
|---|---|---|---|
| `buyer` | string | ✅ | Govt/entity name |
| `title` | string | ✅ | What they're procuring |
| `contact_person` | string | ❌ | Full contact line from RFP |
| `emails` | string | ❌ | Extracted email(s) |
| `phones` | string | ❌ | Extracted phone(s) |
| `deadline` | string | ❌ | Submission deadline (ISO format if known) |
| `url` | string | ✅ | Direct PDF link to RFP |

---

## Quality Filters Applied

### Provider Detection (excluded from processed/)

A result is marked as IT provider (not buyer) if title+snippet contains ≥2 of:
- "we provide", "we offer", "our services", "managed services provider"
- "certified partner", "request a demo", "get a quote", "pricing"
- "top rated", "best rated", "case studies", "portfolio"

### Buyer Intent Detection (included in processed/)

A result is marked as buyer if title+snippet contains any of:
- "need", "looking for", "hiring", "recommend", "evaluating"
- "alternative", "seeking", "who do you use", "outsourcing", "migrat"

### Govt Detection (included in processed/ + govt-rfp/)

A result is marked as govt if title+snippet contains any of:
- "rfp", "tender", "government", "city", "county", "town"
- "district", "municipal", "state agency", "public"

---

## Dedup Key

Primary: `url` (normalized: lowercase, trailing slash removed)
- Same URL from different sources → keep first
- Govt RFPs use PDF URL as dedup key

---

## Running Stats (2026-09-04)

```bash
# Total raw leads
wc -l raw/*.csv | tail -1

# Processed buyer count
grep -c "^" processed/FREE_BUYERS_CLEAN.csv  # subtract 1 for header

# Govt RFP count
wc -l govt-rfp/HOT_BUYER_RFPS.csv

# Leads with email
python3 -c "import csv; print(sum(1 for r in csv.DictReader(open('processed/FREE_BUYERS_CLEAN.csv')) if r['emails_page']))"
```

---

## Changelog

| Date | Action | Files Changed |
|---|---|---|
| 2026-09-04 | Initial repo creation, all scrapers moved | All |
| 2026-09-04 | Added free_harvest.py (main) + stealth_leads.py | internal-scripts/ |
| 2026-09-04 | Extracted 9 govt RFPs with contacts | govt-rfp/HOT_BUYER_RFPS.csv |
| 2026-09-04 | Filtered 206→164 buyer leads | processed/FREE_BUYERS_CLEAN.csv |