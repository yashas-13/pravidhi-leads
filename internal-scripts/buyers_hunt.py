#!/usr/bin/env python3
"""
buyers_hunt.py — jina.ai + direct fetch, buyer intent only
ponytail: no proxy/JS render; add playwright + SERP API when Brave rate-limits hard
"""
import re, csv, json, time, random
from pathlib import Path
import requests
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
E=re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}")
P=re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}")
BLK={"example.com","sentry.io","wixpress","schema.org","w3.org","jquery.com","cloudflare.com","example.net","gravatar.com"}
PROV=["we provide","we offer","our services","managed services provider","IT consulting",
      "certified partner","pricing","case studies","we are an IT","our mission","get a quote",
      "request a demo","free consultation","award-winning"]
def is_provider(t):
    tl=t.lower()
    return sum(1 for s in PROV if s in tl)>=2
def fetch(url):
    u=url.rstrip("/")
    for reader in [f"https://r.jina.ai/http://{u}", f"https://localhost:20128/v1/chat"]:
        pass
    # try jina
    try:
        r=requests.get(f"https://r.jina.ai/http://{u}",timeout=12,headers=H)
        if r.status_code==200 and "blocked by network" not in r.text[:500].lower():
            txt=r.text[:15000]
            if is_provider(txt): return None,None,True
            emails=[e for e in list(set(E.findall(txt))) if not any(b in e.lower() for b in BLK) and not e.endswith((".png",".jpg",".gif",".svg",".webp",".woff",".css",".js"))]
            phones=[p.strip() for p in list(set(P.findall(txt))) if 7<=len(re.sub(r"\D","",p))<=15]
            return ", ".join(emails[:5]), ", ".join(phones[:5]), False
    except: pass
    # fallback direct
    try:
        r=requests.get(url,headers=H,timeout=10,allow_redirects=True)
        txt=r.text[:15000]
        if is_provider(txt): return None,None,True
        emails=[e for e in list(set(E.findall(txt))) if not any(b in e.lower() for b in BLK)]
        phones=[p.strip() for p in list(set(P.findall(txt))) if 7<=len(re.sub(r"\D","",p))<=15]
        return ", ".join(emails[:5]), ", ".join(phones[:5]), False
    except: return None,None,False

def brave(q):
    try:
        r=requests.get(f"https://search.brave.com/search?q={requests.utils.quote(q)}&source=web",headers=H,timeout=15)
        if r.status_code==200 and "anomaly" not in r.text[:600]:
            from bs4 import BeautifulSoup
            import html
            soup=BeautifulSoup(r.text,"html.parser")
            res=[]
            skip={"cdn.search","imgs.search","tiles.search","brave.com","hackerone","youtube","facebook","x.com","twitter","instagram","tiktok"}
            for a in soup.select("a[href]"):
                href=a.get("href","")
                if not href.startswith("http") or any(s in href for s in skip): continue
                t=a.get_text(strip=True)
                if len(t)<10: continue
                par=a.find_parent("div")
                snip=html.unescape(par.get_text(" ",strip=True)[:600]) if par else ""
                res.append({"title":t[:250],"url":href,"snippet":snip[:500],"dork":q})
                if len(res)>=8: break
            return res
    except: pass
    return []

def remotive():
    try:
        r=requests.get("https://remotive.com/api/remote-jobs",timeout=12)
        d=r.json()
        out=[]
        for j in d.get("jobs",[])[:100]:
            t=j.get("title","").lower()
            if any(k in t for k in ["it support","help desk","sysadmin","system admin","it manager","network","devops","infrastructure","security","cloud","admin"]):
                out.append({"source":"remotive","company":j.get("company_name",""),"title":j.get("title","")[:250],
                           "url":j.get("url",""),"snippet":j.get("description","")[:500].replace("\n"," "),
                           "dork":"remotive IT","emails_page":"","phones_page":""})
        return out[:20]
    except: return []

if __name__=="__main__":
    # 1) known buyers from previous discovery
    known=[l.strip() for l in open("all_buyer_urls.txt") if l.strip()] if Path("all_buyer_urls.txt").exists() else []
    print(f"known {len(known)} urls")
    leads=[]
    jobs=remotive()
    print(f"remotive {len(jobs)}")
    # brave buyers
    dorks=["small business hiring IT support contact email","SME looking for IT managed services","small business need IT help contact",
           "request for proposal IT services 2024 2025","government tender IT services AMC"]
    brave_leads=[]
    for d in dorks:
        print(f" brave {d[:40]}")
        res=brave(d)
        print(f"  -> {len(res)}")
        for r in res: brave_leads.append(r)
        time.sleep(random.uniform(5,9))
    # enrich known + brave
    all_urls=known + [r.get("url","") for r in brave_leads]
    # dedup preserving order
    seen=set()
    uniq_urls=[]
    for u in all_urls:
        k=u.rstrip("/").lower()
        if k not in seen and u:
            seen.add(k); uniq_urls.append(u)
    url_meta={r["url"]:r for r in brave_leads}
    final=[]
    for i,u in enumerate(uniq_urls[:40]):
        print(f" [{i+1}/{min(40,len(uniq_urls))}] {u[:60]}")
        meta=url_meta.get(u,{})
        e,p,prov=fetch(u)
        if prov:
            print("  -> provider skip"); continue
        has=e or p or any(s in u for s in ["remotive","remoteok","indeed","jobs","hiring"])
        if not (has or e or p):
            continue
        final.append({"source":meta.get("source","buyer_url") or "buyer_url",
                      "title":meta.get("title",u.split("/")[-1])[:250],
                      "url":u,"snippet":meta.get("snippet","")[:500],
                      "emails_page":e or "","phones_page":p or "","dork":meta.get("dork","")})
        time.sleep(random.uniform(1.2,2.5))
    # add remotive jobs directly (already with emails)
    for j in jobs: final.append(j)
    # write csv/jsonl
    fields=["source","title","url","snippet","emails_page","phones_page","dork"]
    with open("buyers_hot2.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for l in final: w.writerow({k:l.get(k,"") for k in fields})
    with open("buyers_hot2.jsonl","w",encoding="utf-8") as f:
        for l in final: f.write(json.dumps(l,ensure_ascii=False)+"\n")
    print(f"\n[+] DONE {len(final)} -> buyers_hot2.csv / jsonl")
# skipped: SERP API, proxy rotation, JS render. Add when rate-limit persists.
