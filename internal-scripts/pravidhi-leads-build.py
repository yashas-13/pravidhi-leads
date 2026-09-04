#!/usr/bin/env python3
"""Build all markdown views from CSVs in pravidhi-leads"""
import csv, json, re, html, os
from pathlib import Path
from datetime import date
ROOT = Path("/data/data/com.termux/files/home/pravidhi-leads")
today = date.today().isoformat()

def load_csv(p):
    rows = []
    if not p.exists(): return rows
    try:
        for r in csv.DictReader(open(p, encoding='utf-8')):
            rows.append(r)
    except Exception as e:
        print(f"ERR {p}: {e}")
    return rows

def md_escape(s):
    if not s: return ""
    return s.replace("|","\\|").replace("\n","<br>")

def write_md_rows(path, title, rows, cols, limit=None, badge=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    if limit: rows = rows[:limit]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title} ({today})\n\n")
        if badge: f.write(f"> {badge}\n\n")
        f.write(f"**Rows:** {len(rows)}  \n")
        if limit and len(rows) == limit:
            f.write(f"*(showing first {limit} — see CSV for all)*  \n")
        f.write(f"**Source CSV:** `{(path.with_suffix('.csv').as_posix() if False else '')}`  \n")
        f.write("\n")
        if not rows:
            f.write("_No leads found in this batch._\n")
            return
        # header
        f.write("| # | " + " | ".join(c for c in cols) + " |\n")
        f.write("|---" + "|---" * len(cols) + "|\n")
        for i, r in enumerate(rows, 1):
            vals = []
            for c in cols:
                v = md_escape(r.get(c, ""))
                if c == "url" and v: v = f"[{v[:42]}]({v})"
                vals.append(v[:120] if len(v) > 120 else v)
            f.write(f"| {i} | " + " | ".join(vals) + " |\n")
        f.write("\n---\n\n*Generated from CSV. Export: same directory as `.csv`* \n")

def write_govt_md():
    rows = load_csv(ROOT / "govt-rfp" / "HOT_BUYER_RFPS.csv")
    path = ROOT / "govt-rfp" / "HOT_BUYER_RFPS.md"
    cols = ["buyer","title","emails","phones","deadline","url"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Govt & Org RFPs — Verified IT Buyers ({today})\n\n")
        f.write(f"> Highest quality leads: real budget, real deadline, named contact.\n\n")
        f.write(f"**Rows:** {len(rows)}  \n\n")
        if not rows:
            f.write("_No RFPs found._\n"); return
        # Card-style list + table
        for i, r in enumerate(rows, 1):
            buyer = r.get("buyer","").strip()
            title = r.get("title","").strip()
            cp = r.get("contact_person","").strip()[:160]
            email = r.get("emails","").strip()
            phone = r.get("phones","").strip()
            deadline = r.get("deadline","").strip() or "—"
            url = r.get("url","").strip()
            f.write(f"## {i}. {buyer}\n\n")
            f.write(f"**What:** {title}  \n")
            if cp: f.write(f"**Contact:** {md_escape(cp)}  \n")
            if email: f.write(f"**Email:** `{email}`  \n")
            if phone: f.write(f"**Phone:** `{phone}`  \n")
            f.write(f"**Deadline:** {deadline}  \n")
            if url: f.write(f"**RFP PDF:** [{url[:60]}]({url})  \n")
            f.write("\n---\n\n")

def write_processed_md():
    rows = load_csv(ROOT / "processed" / "FREE_BUYERS_CLEAN.csv")
    # Split: govt + buyer + hiring
    govt, buyer, hiring, other = [], [], [], []
    for r in rows:
        blob = (r.get("title","") + " " + r.get("snippet","") + " " + r.get("dork","")).lower()
        if any(k in blob for k in ["rfp","tender","government","city","county","town","district","municipal","state agency"]):
            govt.append(r)
        elif any(k in blob for k in ["hiring","job opening","recruiting","join our team"]) and any(k in blob for k in ["it","network","devops"]):
            hiring.append(r)
        elif any(k in blob for k in ["need","looking for","recommend","evaluating","alternative","seeking","outsourcing","migrat"]):
            buyer.append(r)
        else:
            other.append(r)
    # Main buyers MD
    base = ROOT / "processed"
    write_md_rows(base / "FREE_BUYERS_CLEAN-buyers.md", "Buyer Intent Leads", buyer,
                  ["source","company","title","emails_page","phones_page","url","dork"],
                  badge="Filtered: actively searching for IT / MSP / cloud / helpdesk.")
    write_md_rows(base / "FREE_BUYERS_CLEAN-govt.md", "Govt / Tender Leads", govt,
                  ["source","company","title","emails_page","phones_page","url","dork"],
                  badge="Govt/municipal IT tenders.")
    write_md_rows(base / "FREE_BUYERS_CLEAN-hiring.md", "Companies Hiring IT (Outsourcing Triggers)", hiring,
                  ["source","company","title","emails_page","phones_page","url","dork"],
                  badge="Hiring IT staff — potential outsourcer if headcount stall / skill gap.")
    # Overview index
    with open(base / "FREE_BUYERS_CLEAN.md", "w", encoding="utf-8") as f:
        f.write(f"# Free Buyer Leads — Clean ({today})\n\n")
        f.write(f"**Total:** {len(rows)}  — Buyer {len(buyer)} + Govt {len(govt)} + Hiring {len(hiring)} + Other {len(other)}\n\n")
        f.write("## Files\n\n")
        f.write("| Segment | File | Count | Description |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| ✅ Buyer intent | `FREE_BUYERS_CLEAN-buyers.md` | {len(buyer)} | Actively needing IT/MSP/cloud/helpdesk |\n")
        f.write(f"| 🏛️ Govt / Tender | `FREE_BUYERS_CLEAN-govt.md` | {len(govt)} | RFPs / tenders |\n")
        f.write(f"| 🏢 Hiring IT | `FREE_BUYERS_CLEAN-hiring.md` | {len(hiring)} | Companies hiring IT (outsourcing trigger) |\n")
        f.write(f"| 📦 Other | in CSV | {len(other)} | Unclassified |\n")
        f.write(f"| 📄 All | `FREE_BUYERS_CLEAN.csv` | {len(rows)} | Full CSV |\n")
        f.write("\n---\n\n*See per-segment `.md` files for the full table.*\n")

def write_raw_md():
    csvs = list((ROOT / "raw").glob("*.csv"))
    with open(ROOT / "raw" / "README.md", "w", encoding="utf-8") as f:
        f.write(f"# Raw Leads — Unfiltered ({today})\n\n")
        f.write(f"> All scraper outputs before quality filter. Use `../processed/` for buyer-only leads.\n\n")
        f.write("## Files\n\n")
        f.write("| File | Leads | With email | With phone | Sources |\n")
        f.write("|---|---|---|---|---|\n")
        cols = ["source","company","title","url","snippet","emails_page","phones_page","dork"]
        for csvf in sorted(csvs):
            rows = load_csv(csvf)
            with_email = sum(1 for r in rows if r.get("emails_page","").strip())
            with_phone = sum(1 for r in rows if r.get("phones_page","").strip())
            sources = ", ".join(sorted(set(r.get("source","") for r in rows if r.get("source")))) or "—"
            stem = csvf.stem
            f.write(f"| `{csvf.name}` | {len(rows)} | {with_email} | {with_phone} | {md_escape(sources)} |\n")
            # per-file markdown view
            mdp = csvf.with_suffix(".md")
            write_md_rows(mdp, stem, rows, cols)
        f.write("\n---\n\n*Each `.md` beside a `.csv` is an auto-readable copy of that file.*\n")

if __name__ == "__main__":
    print("=== Building MD views ===")
    write_govt_md();       print("  ✅ govt-rfp/HOT_BUYER_RFPS.md")
    write_processed_md();  print("  ✅ processed/*.md (buyers + govt + hiring + index)")
    write_raw_md();        print("  ✅ raw/*.md + raw/README.md")
    print("Done.")
