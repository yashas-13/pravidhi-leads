#!/usr/bin/env python3
"""
stealth_leads.py — DuckDuckGo lite + real page fetch + Remotive + HN Algolia
bypasses rate limits via DDG lite + redirect URL decode
"""
import re, csv, json, time, random, html as html_mod
from urllib.parse import quote_plus, unquote
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUTPUT = "stealth_buyers"
H = {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"}
E = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}")
P = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}")
BLK = {"example.com","sentry.io","wixpress","schema.org","w3.org","jquery.com","cloudflare.com",
       "example.net","localhost","gravatar.com","googleapis.com","zoho.com","hubspot.com"}
PROV = ["we provide","we offer","our services","managed services provider","IT consulting",
        "certified partner","pricing","case studies","we are an IT","get a quote",
        "request a demo","free consultation","award-winning","top rated","best rated"]

def is_provider(t):
    return sum(1 for s in PROV if s in t.lower()) >= 2

def ddg_lite(q):
    """DuckDuckGo lite search — decode redirect URLs"""
    try:
        r = requests.get(f"https://lite.duckduckgo.com/lite/?q={quote_plus(q)}", headers=H, timeout=15)
        if r.status_code != 200: return []
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            # decode duckduckgo redirect
            if "duckduckgo.com/l/?uddg=" in href:
                real = unquote(href.split("uddg=")[1].split("&")[0])
                text = a.get_text(strip=True)
                if len(text) < 5: continue
                results.append({"url": real, "title": text[:250]})
            elif href.startswith("http") and "duckduckgo.com" not in href:
                text = a.get_text(strip=True)
                if len(text) >= 10:
                    results.append({"url": href, "title": text[:250]})
            if len(results) >= 10: break
        return results
    except Exception as e:
        print(f"  DDG ERR: {e}")
        return []

def fetch_page(url):
    """Fetch real page, extract emails/phones, detect provider"""
    try:
        r = requests.get(url, headers=H, timeout=10, allow_redirects=True)
        if r.status_code != 200: return None, None, True, ""
        txt = r.text[:15000]
        if is_provider(txt): return None, None, True, ""
        emails = list(set(E.findall(txt)))
        emails = [e for e in emails if not any(b in e.lower() for b in BLK)
                  and not e.endswith((".png",".jpg",".gif",".svg",".webp",".woff",".css",".js",".woff2"))]
        phones = [p.strip() for p in list(set(P.findall(txt)))
                  if 7 <= len(re.sub(r"\D","",p)) <= 15]
        # extract title from HTML
        title = ""
        if "<title>" in txt.lower():
            import re as re2
            m = re2.search(r"<title[^>]*>([^<]+)</title>", txt, re2.I)
            if m: title = m.group(1).strip()[:200]
        return ", ".join(emails[:5]), ", ".join(phones[:5]), False, title
    except:
        return None, None, False, ""

def remotive_it():
    """Remotive API — companies hiring IT"""
    leads = []
    try:
        r = requests.get("https://remotive.com/api/remote-jobs", headers=H, timeout=12)
        for j in r.json().get("jobs", [])[:200]:
            t = j.get("title", "").lower()
            if any(k in t for k in ["it support","help desk","sysadmin","system admin",
                                     "it manager","network","devops","infrastructure",
                                     "security","cloud","admin","support","devops"]):
                leads.append({
                    "source": "remotive", "company": j.get("company_name", ""),
                    "title": j.get("title", "")[:250], "url": j.get("url", ""),
                    "snippet": j.get("description", "")[:500].replace("\n", " "),
                    "emails_page": "", "phones_page": "",
                    "dork": f"category:{j.get('category','')}"
                })
        print(f"  [remotive] {len(leads)} IT jobs")
    except Exception as e:
        print(f"  [remotive] ERR: {e}")
    return leads

def hn_algolia():
    """HN Algolia — buyer intent posts"""
    leads = []
    queries = [
        "small business IT support", "need IT help", "looking for MSP",
        "managed IT services", "hiring IT support", "need IT infrastructure",
    ]
    seen = set()
    for q in queries:
        try:
            r = requests.get(f"https://hn.algolia.com/api/v1/search",
                            params={"query": q, "tags": "story", "hitsPerPage": 15}, timeout=12)
            for hit in r.json().get("hits", []):
                oid = hit.get("objectID", "")
                if oid in seen: continue
                seen.add(oid)
                title = hit.get("title", "")
                text = hit.get("story_text", "") or hit.get("comment_text", "") or ""
                text = html_mod.unescape(text).replace("<p>", " ").replace("</p>", " ")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
                emails = list(set(E.findall(title + " " + text)))
                emails = [e for e in emails if not any(b in e.lower() for b in BLK)]
                leads.append({
                    "source": "hn_algolia", "company": hit.get("author", ""),
                    "title": title[:250], "url": url,
                    "snippet": text[:500],
                    "emails_page": ", ".join(emails[:3]),
                    "phones_page": "", "dork": f"hn:{q}",
                })
        except: pass
    print(f"  [hn] {len(leads)} posts")
    return leads

def ddg_buyer_searches():
    """DDG lite buyer-intent dorks"""
    dorks = [
        '"need IT support" small business contact email',
        '"looking for IT services" contact us',
        '"hiring IT support" small company',
        '"need managed IT" OR "need MSP" contact',
        '"request for proposal" IT services filetype:pdf',
        'small business IT help "contact me" OR "email me"',
        '"our company needs IT" OR "looking for IT company"',
        'government tender IT services AMC 2024 2025',
        '"need IT infrastructure" OR "need network setup"',
        '"looking for cloud migration" small business',
        '"need cybersecurity" small company contact',
        '"hiring managed services" OR "outsourcing IT"',
        '"IT support for small" contact email phone',
        '"need help with IT" OR "need IT help" business',
        '"seeking IT partner" OR "need IT vendor"',
    ]
    all_results = []
    for i, d in enumerate(dorks):
        print(f"  [{i+1}/{len(dorks)}] {d[:60]}")
        res = ddg_lite(d)
        print(f"    -> {len(res)} results")
        all_results.extend([{"dork": d, **r} for r in res])
        time.sleep(random.uniform(2, 4))
    return all_results

def main():
    print("=== Remotive ===")
    all_leads = remotive_it()

    print("\n=== HN Algolia ===")
    all_leads.extend(hn_algolia())

    print("\n=== DuckDuckGo Lite ===")
    ddg_results = ddg_buyer_searches()
    print(f"\n[*] DDG total: {len(ddg_results)} raw results")

    # Dedup DDG by domain
    seen_domains = set()
    ddg_unique = []
    for r in ddg_results:
        from urllib.parse import urlparse
        domain = urlparse(r["url"]).netloc.lower()
        if domain not in seen_domains:
            seen_domains.add(domain)
            ddg_unique.append(r)
    print(f"[*] DDG unique domains: {len(ddg_unique)}")

    # Fetch real pages, extract contacts, filter providers
    print("\n=== Fetching real pages ===")
    ddg_leads = []
    for i, r in enumerate(ddg_unique):
        print(f"  [{i+1}/{len(ddg_unique)}] {r['url'][:60]}", end=" ")
        e, p, prov, title = fetch_page(r["url"])
        if prov:
            print("-> PROVIDER")
            continue
        if not e and not p:
            print("-> no contact")
            continue
        ddg_leads.append({
            "source": "ddg",
            "company": "",
            "title": title or r.get("title", ""),
            "url": r["url"],
            "snippet": "",
            "emails_page": e or "",
            "phones_page": p or "",
            "dork": r.get("dork", ""),
        })
        print(f"-> {len((e or '').split(','))} emails, {len((p or '').split(','))} phones")
        time.sleep(random.uniform(1, 2))

    all_leads.extend(ddg_leads)

    # Final dedup
    seen = set()
    final = []
    for l in all_leads:
        k = l["url"].rstrip("/").lower()
        if k not in seen:
            seen.add(k)
            final.append(l)

    # Write
    fields = ["source", "company", "title", "url", "snippet", "emails_page", "phones_page", "dork"]
    with open(f"{OUTPUT}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for l in final: w.writerow({k: l.get(k, "") for k in fields})
    with open(f"{OUTPUT}.jsonl", "w", encoding="utf-8") as f:
        for l in final: f.write(json.dumps(l, ensure_ascii=False) + "\n")

    # Stats
    with_email = sum(1 for l in final if l.get("emails_page"))
    with_phone = sum(1 for l in final if l.get("phones_page"))
    sources = {}
    for l in final:
        s = l.get("source", "")
        sources[s] = sources.get(s, 0) + 1

    print(f"\n{'='*60}")
    print(f"[+] DONE: {len(final)} total leads")
    for s, c in sorted(sources.items()): print(f"    {s}: {c}")
    print(f"    With email: {with_email} | With phone: {with_phone}")
    print(f"    Output: {OUTPUT}.csv + {OUTPUT}.jsonl")

    # Top buyers
    print(f"\n{'='*60}")
    print("[TOP BUYER LEADS]")
    for l in final:
        e = l.get("emails_page", "")
        p = l.get("phones_page", "")
        if e or p:
            print(f"  {l['title'][:55]:55}")
            if e: print(f"    EMAIL: {e[:50]}")
            if p: print(f"    PHONE: {p[:50]}")
            print(f"    URL: {l['url'][:70]}")
            print()

if __name__ == "__main__":
    main()
