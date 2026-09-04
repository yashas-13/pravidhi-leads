#!/usr/bin/env python3
"""
all_leads.py — Aggregate ALL accessible buyer sources
Sources:
 1. Remotive API (IT jobs = outsourcing trigger)
 2. RemoteOK API (IT jobs + apply emails)
 3. HN Algolia "Ask HN" buyer intent posts
 4. HN Algolia "Who is Hiring" companies needing IT
 5. USAspending API (gov IT contracts = SME subcontractors)
 6. Brave search snippets (when available)
 7. Jina.ai reader on known buyer URLs
"""
import re, csv, json, time, random, html
from urllib.parse import quote_plus
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUTPUT = "all_buyers_final"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
E = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}")
P = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}")
BLK = {"example.com","sentry.io","wixpress","schema.org","w3.org","jquery.com",
       "cloudflare.com","example.net","localhost","indeed.com","glassdoor.com",
       "gravatar.com","googleapis.com","zoho.com","hubspot.com","freshworks.com"}

PROV = ["we provide","we offer","our services","managed services provider","IT consulting",
        "certified partner","pricing","case studies","we are an IT","get a quote",
        "request a demo","free consultation","award-winning","top rated"]
def is_provider(t):
    return sum(1 for s in PROV if s in t.lower()) >= 2

def jina_read(url):
    try:
        r = requests.get(f"https://r.jina.ai/http://{url}", timeout=15, headers=H)
        if r.status_code==200 and "blocked by network" not in r.text[:500].lower():
            return r.text[:15000]
    except: pass
    return None

def extract_contacts(text):
    if not text: return [], []
    emails = list(set(E.findall(text)))
    emails = [e for e in emails if not any(b in e.lower() for b in BLK)
              and not e.endswith((".png",".jpg",".gif",".svg",".webp",".woff",".css",".js",".woff2"))]
    phones = [p.strip() for p in list(set(P.findall(text)))
              if 7 <= len(re.sub(r"\D","",p)) <= 15]
    return emails[:5], phones[:5]

# ── 1. REMOTEOK ──
def source_remoteok():
    leads = []
    kw = ["it support","help desk","helpdesk","sysadmin","system admin","it manager",
          "network engineer","network admin","security analyst","cloud engineer",
          "devops","infrastructure","database","it director","cto","ciso",
          "it consultant","technical support","desktop support","server admin"]
    try:
        r = requests.get("https://remoteok.com/remote-jobs.json", headers=H, timeout=12)
        jobs = r.json()
        if isinstance(jobs,list): jobs = jobs[1:]
        for j in jobs[:400]:
            pos = j.get("position","").lower()
            tags = " ".join(j.get("tags",[])).lower()
            combined = pos + " " + tags
            if any(k in combined for k in kw):
                email = j.get("email","")
                if email and any(b in email.lower() for b in BLK): email = ""
                leads.append({
                    "source":"remoteok",
                    "company": j.get("company",""),
                    "title": j.get("position","")[:250],
                    "url": j.get("url",""),
                    "snippet": j.get("description","")[:500].replace("\n"," "),
                    "emails_page": email,
                    "phones_page": "",
                    "dork": f"tags: {', '.join(j.get('tags',[])[:3])}",
                })
        print(f"  [remoteok] {len(leads)} IT jobs")
    except Exception as e:
        print(f"  [remoteok] ERR: {e}")
    return leads

# ── 2. REMOTIVE ──
def source_remotive():
    leads = []
    kw = ["it support","help desk","sysadmin","system admin","it manager",
          "network","devops","infrastructure","security","cloud","admin","support"]
    try:
        r = requests.get("https://remotive.com/api/remote-jobs", headers=H, timeout=12)
        for j in r.json().get("jobs",[])[:150]:
            t = j.get("title","").lower()
            if any(k in t for k in kw):
                leads.append({
                    "source":"remotive",
                    "company": j.get("company_name",""),
                    "title": j.get("title","")[:250],
                    "url": j.get("url",""),
                    "snippet": j.get("description","")[:500].replace("\n"," "),
                    "emails_page": "",
                    "phones_page": "",
                    "dork": f"category: {j.get('category','')}",
                })
        print(f"  [remotive] {len(leads)} jobs")
    except Exception as e:
        print(f"  [remotive] ERR: {e}")
    return leads

# ── 3. HN ALGOLIA "Ask HN" (buyer intent posts) ──
def source_hn_algolia():
    leads = []
    queries = [
        "small business IT support",
        "need IT help",
        "looking for MSP",
        "managed IT services",
        "IT infrastructure",
        "hiring IT support",
    ]
    try:
        seen_ids = set()
        for q in queries:
            r = requests.get(f"https://hn.algolia.com/api/v1/search",
                            params={"query": q, "tags": "story", "hitsPerPage": 10},
                            timeout=12)
            data = r.json()
            for hit in data.get("hits",[]):
                oid = hit.get("objectID","")
                if oid in seen_ids: continue
                seen_ids.add(oid)
                title = hit.get("title","")
                text = hit.get("story_text","") or hit.get("comment_text","") or ""
                text = html.unescape(text).replace("<p>"," ").replace("</p>"," ")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
                emails = list(set(E.findall(title + " " + text)))
                emails = [e for e in emails if not any(b in e.lower() for b in BLK)]
                leads.append({
                    "source":"hn_algolia",
                    "company": hit.get("author",""),
                    "title": title[:250],
                    "url": url,
                    "snippet": text[:500],
                    "emails_page": ", ".join(emails[:3]),
                    "phones_page": "",
                    "dork": f"hn query: {q}",
                })
        print(f"  [hn_algolia] {len(leads)} posts")
    except Exception as e:
        print(f"  [hn_algolia] ERR: {e}")
    return leads

# ── 4. USASPENDING.GOV (govt IT contracts → SME subcontractor leads) ──
def source_usaspending():
    leads = []
    try:
        r = requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
            json={
                "filters": {
                    "time_period": [{"start_date":"2024-01-01","end_date":"2025-12-31"}],
                    "award_type_codes": ["A","B","C"],
                    "naics_codes": {"require": ["541511","541512","541519","541513","541519"]}
                },
                "fields": ["Award ID","Recipient Name","Award Amount","Description","URI","Recipient DUNS"],
                "limit": 20, "sort": "Award Amount", "order": "desc"
            }, timeout=15)
        data = r.json()
        for a in data.get("results",[]):
            name = a.get("Recipient Name","")
            amt = a.get("Award Amount",0)
            desc = (a.get("Description") or "")[:500]
            url = a.get("URI","") or ""
            leads.append({
                "source":"usaspending",
                "company": name,
                "title": f"Govt IT Contract: ${amt:,.0f}"[:250],
                "url": url,
                "snippet": desc,
                "emails_page": "",
                "phones_page": "",
                "dork": "NAICS 5415xx IT services",
            })
        print(f"  [usaspending] {len(leads)} contracts")
    except Exception as e:
        print(f"  [usaspending] ERR: {e}")
    return leads

# ── 5. BRAVE SEARCH (fallback, when rate-limited returns empty) ──
def source_brave():
    dorks = [
        "small business hiring IT support contact email",
        "need IT managed services SME",
        "request for proposal IT services 2024 2025",
        "government tender IT AMC services",
        "small business need IT help contact us",
    ]
    leads = []
    skip = {"cdn.search","imgs.search","tiles.search","brave.com","hackerone",
            "youtube","facebook","x.com","twitter","instagram","tiktok","linkedin.com"}
    for q in dorks:
        try:
            r = requests.get(f"https://search.brave.com/search?q={quote_plus(q)}&source=web",
                            headers=H, timeout=15)
            if r.status_code!=200 or "anomaly" in r.text[:600]:
                time.sleep(random.uniform(6,9))
                continue
            soup = BeautifulSoup(r.text,"html.parser")
            for a in soup.select("a[href]"):
                href = a.get("href","")
                if not href.startswith("http") or any(s in href for s in skip): continue
                t = a.get_text(strip=True)
                if len(t)<10: continue
                par = a.find_parent("div")
                snip = html.unescape(par.get_text(" ",strip=True)[:600]) if par else ""
                leads.append({"source":"brave","company":"","title":t[:250],"url":href,
                             "snippet":snip[:500],"emails_page":"","phones_page":"","dork":q})
            time.sleep(random.uniform(5,8))
        except: pass
    print(f"  [brave] {len(leads)} results")
    return leads

# ── 6. JINA READER on known buyer URLs ──
def source_jina_read(urls):
    leads = []
    for i,u in enumerate(urls[:20]):
        print(f"  jina [{i+1}] {u[:60]}")
        txt = jina_read(u)
        if not txt: continue
        if is_provider(txt): continue
        emails, phones = extract_contacts(txt)
        if emails or phones:
            leads.append({"source":"jina","company":"","title":u.split("/")[-2][:250] if "/" in u else "",
                         "url":u,"snippet":txt[:500],
                         "emails_page":", ".join(emails),"phones_page":", ".join(phones),"dork":"jina_read"})
        time.sleep(random.uniform(1,2))
    print(f"  [jina] {len(leads)} with contacts")
    return leads

def main():
    all_leads = []

    print("[1/6] RemoteOK")
    all_leads.extend(source_remoteok())

    print("[2/6] Remotive")
    all_leads.extend(source_remotive())

    print("[3/6] HN Algolia")
    all_leads.extend(source_hn_algolia())

    print("[4/6] USAspending.gov")
    all_leads.extend(source_usaspending())

    print("[5/6] Brave search")
    all_leads.extend(source_brave())

    # dedup by URL
    seen = set()
    uniq = []
    for l in all_leads:
        k = l["url"].rstrip("/").lower()
        if k not in seen:
            seen.add(k)
            uniq.append(l)

    # enrich first 30 with jina for contacts
    print(f"\n[6/6] Jina enrich ({len(uniq)} unique, enriching top 25)")
    jina_urls = [l["url"] for l in uniq if not l.get("emails_page")][:25]
    jina_results = source_jina_read(jina_urls)
    jina_map = {r["url"].rstrip("/").lower(): r for r in jina_results}
    for l in uniq:
        j = jina_map.get(l["url"].rstrip("/").lower())
        if j:
            l["emails_page"] = j.get("emails_page","")
            l["phones_page"] = j.get("phones_page","")

    # filter: keep only with contacts OR job listings (company hiring = buyer)
    final = [l for l in uniq if l.get("emails_page") or l.get("phones_page")
             or l.get("source") in ("remoteok","remotive","usaspending","hn_algolia")]

    # write
    fields = ["source","company","title","url","snippet","emails_page","phones_page","dork"]
    with open(f"{OUTPUT}.csv","w",newline="",encoding="utf-8") as f:
        w = csv.DictWriter(f,fieldnames=fields)
        w.writeheader()
        for l in final: w.writerow({k:l.get(k,"") for k in fields})
    with open(f"{OUTPUT}.jsonl","w",encoding="utf-8") as f:
        for l in final: f.write(json.dumps(l,ensure_ascii=False)+"\n")

    # stats
    sources = {}
    for l in final:
        s = l.get("source","")
        sources[s] = sources.get(s,0)+1
    emails_ct = sum(1 for l in final if l.get("emails_page"))
    phones_ct = sum(1 for l in final if l.get("phones_page"))
    print(f"\n[+] DONE: {len(final)} buyer leads")
    for s,c in sorted(sources.items()): print(f"    {s}: {c}")
    print(f"    With email: {emails_ct} | With phone: {phones_ct}")
    print(f"    Output: {OUTPUT}.csv + {OUTPUT}.jsonl")

    # top 20 preview
    print("\n[TOP 20]")
    for l in final[:20]:
        e = l.get("emails_page","")[:30]
        p = l.get("phones_page","")[:25]
        print(f"  {l['source']:12} | {l.get('company','')[:25]:25} | {l['title'][:45]:45} | e={e:30} p={p}")

if __name__ == "__main__":
    main()
