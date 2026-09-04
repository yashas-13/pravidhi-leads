#!/usr/bin/env python3
"""
free_harvest.py — max free buyer harvest (no paid APIs)
Sources: HN Algolia, Remotive, Arbeitnow DE, USAspending, DDG-lite RFPs + gov tenders,
         Spiceworks/Freecodecamp/Reddit via Jina, Craigslist RSS, ProductHunt
All free, no auth. Run: python3 free_harvest.py
"""
import re, csv, json, time, random, html as hm, urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup

OUT="FREE_BUYERS"
H={"User-Agent":"Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Mobile Safari/537.36"}
E=re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}")
P=re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}")
BLK={"example.com","sentry.io","wixpress","schema.org","w3.org","jquery.com","cloudflare.com","gravatar.com","googleapis.com","hubspot.com","zoho.com","mailchimp.com","sendgrid.net","mailgun.com","amazonses.com","facebook.com","twitter.com","linkedin.com"}

def contacts(txt):
    emails=list(set(E.findall(txt or "")))
    emails=[e for e in emails if not any(b in e.lower() for b in BLK) and not e.endswith((".png",".jpg",".gif",".svg",".webp",".woff",".css",".js",".woff2"))]
    phones=[p.strip() for p in list(set(P.findall(txt or ""))) if 7<=len(re.sub(r"\D","",p))<=15]
    return emails[:5], phones[:5]

def jina(url):
    try:
        r=requests.get(f"https://r.jina.ai/http://{url}", headers=H, timeout=15)
        if r.status_code==200 and "Just a moment" not in r.text[:600] and len(r.text)>800:
            return r.text
    except: pass
    return None

def hn_algolia():
    out=[]
    queries=["need IT support","looking for MSP","managed IT services","hiring IT support","need IT infrastructure","cloud migration small business","cybersecurity small business","IT support for small","looking for IT services","need help IT","outsourcing IT"]
    seen=set()
    for q in queries:
        try:
            r=requests.get("https://hn.algolia.com/api/v1/search", params={"query":q,"tags":"story","hitsPerPage":12}, timeout=10)
            for h in r.json().get("hits",[]):
                oid=h.get("objectID","")
                if oid in seen: continue
                seen.add(oid)
                txt=hm.unescape((h.get("story_text","") or h.get("comment_text","") or "")).replace("<p>"," ")
                title=h.get("title","")
                e,p=contacts(title+" "+txt)
                # buyer intent filter
                blob=(title+" "+txt).lower()
                if any(k in blob for k in ["looking for","need","hiring","recommend","evaluating","alternative","seeking","who do you use"]):
                    out.append({"source":"hn_algolia","company":h.get("author",""),"title":title[:250],"url":h.get("url") or f"https://news.ycombinator.com/item?id={oid}","snippet":txt[:500],"emails_page":", ".join(e),"phones_page":", ".join(p),"dork":q})
        except: pass
        time.sleep(0.3)
    print(f"  [hn] {len(out)}")
    return out

def remotive_it():
    out=[]
    try:
        r=requests.get("https://remotive.com/api/remote-jobs", headers=H, timeout=12)
        for j in r.json().get("jobs",[])[:400]:
            t=j.get("title","").lower()
            if any(k in t for k in ["it support","help desk","sysadmin","system admin","it manag","network","devops","infrastructure","security","cloud"]):
                out.append({"source":"remotive","company":j.get("company_name",""),"title":j.get("title","")[:200],"url":j.get("url",""),"snippet":(j.get("description","") or "")[:400].replace("\n"," "),"emails_page":"","phones_page":"","dork":j.get("category","")})
    except Exception as e: print(f"  [remotive ERR] {e}")
    print(f"  [remotive] {len(out)}")
    return out

def arbeitnow():
    out=[]
    try:
        r=requests.get("https://www.arbeitnow.com/api/job-board-api", headers=H, timeout=12)
        for j in r.json().get("data",[])[:200]:
            t=j.get("title","").lower()
            if any(k in t for k in ["it support","helpdesk","admin","support","network","devops","infrastructure","cloud","security"]):
                tags=" ".join(j.get("tags",[]) or []).lower()
                out.append({"source":"arbeitnow","company":j.get("company_name",""),"title":j.get("title","")[:200],"url":j.get("url",""),"snippet":(j.get("description","") or "")[:400].replace("\n"," "),"emails_page":"","phones_page":"","dork":tags})
    except Exception as e: print(f"  [arbeitnow ERR] {e}")
    print(f"  [arbeitnow] {len(out)}")
    return out

def usaspending():
    out=[]
    bodies=[
        {"filters":{"award_type_codes":["A","B","C","D"],"naics_codes":["541511"],"award_amounts":[{"lower_bound":1000}]},"fields":["Award ID","Recipient Name","Description","Award Amount","Recipient Email","Recipient Phone"],"limit":15},
        {"filters":{"award_type_codes":["A","B","C","D"],"naics_codes":["541512"],"award_amounts":[{"lower_bound":1000}]},"fields":["Award ID","Recipient Name","Description","Award Amount"],"limit":15},
        {"filters":{"award_type_codes":["A","B","C","D"],"naics_codes":["541519"],"award_amounts":[{"lower_bound":1000}]},"fields":["Award ID","Recipient Name","Description","Award Amount"],"limit":15},
    ]
    for body in bodies:
        try:
            r=requests.post("https://api.usaspending.gov/api/v2/search/spending_by_award/", json=body, headers={"Content-Type":"application/json"}, timeout=12)
            for hit in r.json().get("results",[]) :
                out.append({"source":"usaspending","company":hit.get("Recipient Name",""),"title":(hit.get("Description","") or hit.get("Award ID",""))[:200],"url":f"https://www.usaspending.gov/award/{hit.get('Award ID','')}","snippet":f"Award {hit.get('Award ID','')} ${hit.get('Award Amount',''):,}"[:200] if isinstance(hit.get("Award Amount"),int) else str(hit.get("Award ID","")),"emails_page":hit.get("Recipient Email","") or "","phones_page":hit.get("Recipient Phone","") or "","dork":body["filters"]["naics_codes"][0]})
        except Exception as e: print(f"  [usaspending {body['filters']['naics_codes']} ERR] {e}")
        time.sleep(0.4)
    print(f"  [usaspending] {len(out)}")
    return out

def ddg_lite(q):
    try:
        r=requests.get(f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote_plus(q)}", headers=H, timeout=15)
        if r.status_code!=200: return []
        soup=BeautifulSoup(r.text,"html.parser")
        res=[]
        for a in soup.select("a[href]"):
            href=a.get("href","")
            if "duckduckgo.com/l/?uddg=" in href:
                real=urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
                t=a.get_text(strip=True)
                if len(t)>=6 and real.startswith("http"):
                    res.append({"title":t[:250],"url":real,"dork":q})
            if len(res)>=10: break
        return res
    except: return []

def ddg_fetch():
    prov_kw=["we provide","we offer","our services","managed services provider","certified partner","request a demo","get a quote","top rated","pricing","best rated"]
    def is_provider(txt): return sum(1 for s in prov_kw if s in txt.lower())>=2
    dorks=[
        "request for proposal IT services filetype:pdf",
        "government tender IT services AMC 2024 2025",
        "RFP managed IT services pdf",
        "hiring IT support small company",
        "need managed IT OR need MSP contact",
        "IT support for small business contact email phone",
        "looking for cloud migration small business",
        "need cybersecurity small company contact",
        "outsourcing IT help small business",
        "need help with IT small business",
        "IT infrastructure RFP pdf 2025",
        "helpdesk RFP government 2025",
        "AMC IT tender india pdf",
    ]
    seen_doms=set()
    results=[]
    for i,d in enumerate(dorks):
        print(f"    ddg [{i+1}/{len(dorks)}] {d[:42]:42}", end=" ")
        res=ddg_lite(d)
        print(f"{len(res)} hits")
        for r in res:
            dom=urllib.parse.urlparse(r["url"]).netloc.lower()
            if dom in seen_doms: continue
            seen_doms.add(dom)
            # fetch page + extract contacts
            try:
                pr=requests.get(r["url"], headers=H, timeout=10, allow_redirects=True)
                if pr.status_code!=200: continue
                txt=pr.text[:15000]
                if is_provider(txt): continue
                e,p=contacts(txt)
                if not e and not p: continue
                title=""
                m=re.search(r"<title[^>]*>([^<]+)</title>", txt or "", re.I)
                if m: title=m.group(1).strip()[:200]
                results.append({"source":"ddg","company":"","title":title or r["title"][:200],"url":r["url"],"snippet":"","emails_page":", ".join(e),"phones_page":", ".join(p),"dork":d})
            except: pass
        time.sleep(random.uniform(1,2))
    print(f"  [ddg] {len(results)}")
    return results

def jina_communities():
    """Spiceworks, freecodecamp etc via jina — slower, small batch"""
    out=[]
    candidates=[
        ("https://community.spiceworks.com/search?q=need%20IT%20support", "spiceworks"),
        ("https://community.spiceworks.com/search?q=looking%20for%20MSP", "spiceworks"),
    ]
    for url,src in candidates:
        txt=jina(url)
        if txt:
            e,p=contacts(txt)
            # grab titles
            for line in txt.split("\n"):
                if any(k in line.lower() for k in ["need it","looking for","help with it","recommend"]):
                    out.append({"source":src,"company":"","title":line.strip()[:200],"url":url,"snippet":line.strip()[:400],"emails_page":", ".join(e),"phones_page":", ".join(p),"dork":url})
        time.sleep(0.8)
    print(f"  [communities] {len(out)}")
    return out

def main():
    all_leads=[]
    print("=== HN Algolia ===");  all_leads.extend(hn_algolia())
    print("=== Remotive ===");    all_leads.extend(remotive_it())
    print("=== Arbeitnow ===");   all_leads.extend(arbeitnow())
    print("=== USAspending ==="); all_leads.extend(usaspending())
    print("=== DDG lite RFPs ==="); all_leads.extend(ddg_fetch())
    print("=== Communities (jina) ==="); all_leads.extend(jina_communities())

    # dedup
    seen=set(); final=[]
    for l in all_leads:
        k=l["url"].rstrip("/").lower()
        if k not in seen:
            seen.add(k); final.append(l)

    fields=["source","company","title","url","snippet","emails_page","phones_page","dork"]
    with open(f"{OUT}.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for l in final: w.writerow({k:l.get(k,"") for k in fields})
    with open(f"{OUT}.jsonl","w",encoding="utf-8") as f:
        for l in final: f.write(json.dumps(l,ensure_ascii=False)+"\n")

    with_email=sum(1 for l in final if l.get("emails_page"))
    with_phone=sum(1 for l in final if l.get("phones_page"))
    sources={}
    for l in final: sources[l["source"]] = sources.get(l["source"],0)+1
    print("\n"+"="*55)
    print(f"[+] DONE: {len(final)} leads | email {with_email} | phone {with_phone}")
    for s,c in sorted(sources.items()): print(f"    {s:15} {c}")
    print(f"    -> {OUT}.csv / {OUT}.jsonl")
    print("="*55)
    for l in final:
        if "@" in l.get("emails_page",""):
            print(f"  {l['title'][:52]:52} | {l['emails_page'][:30]} | {l['url'][:48]}")

if __name__=="__main__": main()
