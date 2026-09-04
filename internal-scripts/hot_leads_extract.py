#!/usr/bin/env python3
"""
hot_leads_extract.py — extract real contacts from RFP PDFs + pages
"""
import re, csv, json, requests, html as html_mod
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
E=re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-z]{2,}")
P=re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{3,4}")
BLK={"example.com","sentry.io","wixpress","schema.org","gravatar.com","googleapis.com"}

rfps=[
    ("Grand Isle VT","https://grandislevt.org/wp-content/uploads/2026/09/RFP_-IT_Services_Town_of_Grand_Isle.pdf","Govt IT Services RFP","2026-10-16"),
    ("City of Peosta IA","https://www.cityofpeosta.org/uploads/documents/IT_Services_RFP.pdf","Managed IT Services RFP",""),
    ("Stevenson WA","https://www.ci.stevenson.wa.us/sites/default/files/fileattachments/city_attachments/2025/Stevenson_RFP_Managed_IT.pdf","Managed IT Services RFP",""),
    ("CLASP","https://www.clasp.org/wp-content/uploads/2026/08/CLASP-IT-RFP-2026-Final.pdf","Technology Services RFP",""),
    ("CAP St Joseph","https://www.capstjoe.org/wp-content/uploads/2026/02/IT-Service-RFP.pdf","Contractual IT Managed Services",""),
    ("Indiana Afterschool","https://www.indianaafterschool.org/wp-content/uploads/2025/03/Managed-IT-Services-RFP.pdf","Managed IT Services",""),
    ("OCAC Odisha","https://www.ocac.in/sites/default/files/2024-12/AMC%20EMPANELMENT%20RFP.pdf","AMC IT Assets",""),
    ("Wlfea","https://www.wlfea.org/wp-content/uploads/2025/03/2025-IT-Services-RFP.pdf","IT Services RFP",""),
    ("CAG India","https://cag.gov.in/uploads/tenders/tenders-AMC-for-IT-Assets-0657670c1be9839-202814256.pdf","AMC IT Assets",""),
]
leads=[]
for buyer,url,title,deadline in rfps:
    print(f"[{buyer}] {url[:50]}")
    try:
        r=requests.get(f"https://r.jina.ai/http://{url}",headers=H,timeout=15)
        if r.status_code!=200: print("  -> status",r.status_code); continue
        txt=r.text[:15000]
        emails=list(set(E.findall(txt)))
        emails=[e for e in emails if not any(b in e.lower() for b in BLK) and not e.endswith((".png",".jpg",".gif",".svg"))]
        phones=[p.strip() for p in list(set(P.findall(txt))) if 7<=len(re.sub(r"\D","",p))<=15]
        # contact person
        contact_person=""
        for line in txt.split("\n"):
            if "@" in line or "contact" in line.lower():
                contact_person=line.strip()[:150]
                break
        print(f"  -> {emails[:2]} | {phones[:3]}")
        # only keep if real contact
        if emails or phones:
            leads.append({"buyer":buyer,"title":title,"url":url,"contact_person":contact_person[:150],
                         "emails":", ".join(emails[:5]),"phones":", ".join(phones[:5]),"deadline":deadline})
    except Exception as e:
        print(f"  ERR {e}")
# also add remotive + ddg non-RFP buyers
import json as js
for l in open("stealth_buyers.jsonl"):
    j=js.loads(l)
    if j["source"] in ("ddg","remotive") and "@" in j.get("emails_page",""):
        if j["url"] not in [x["url"] for x in leads]:
            # check not provider
            if not any(s in j.get("title","").lower() for s in ["we provide","we offer","pricing"]):
                leads.append({"buyer":j.get("company","") or j["title"][:30],"title":j["title"][:80],
                              "url":j["url"],"contact_person":"","emails":j.get("emails_page",""),
                              "phones":j.get("phones_page",""),"deadline":""})
# write
fields=["buyer","title","contact_person","emails","phones","deadline","url"]
with open("HOT_BUYER_RFPS.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields)
    w.writeheader()
    for l in leads:
        w.writerow({k:l.get(k,"") for k in fields})
with open("HOT_BUYER_RFPS.jsonl","w",encoding="utf-8") as f:
    for l in leads:
        f.write(json.dumps(l,ensure_ascii=False)+"\n")
print(f"\n[+] DONE: {len(leads)} hot buyer leads -> HOT_BUYER_RFPS.csv")
for l in leads:
    print(f"  {l['buyer']:20} | {l['title'][:40]:40} | {l['emails'][:35]:35} | {l['phones'][:20]}")
