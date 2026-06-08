"""Test per verificare la struttura dei CIK nei Form 4 SEC."""
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import requests, urllib3
urllib3.disable_warnings()

headers = {"User-Agent": "InvestmentAgents contact@investment-agents.com"}

# Fetch 5 Form 4 recenti
r = requests.get(
    "https://efts.sec.gov/LATEST/search-index",
    params={"forms":"4","dateRange":"custom",
            "startdt":"2026-05-24","enddt":"2026-06-07",
            "from":0,"size":5},
    headers=headers, verify=False
)
data = r.json()
hits = data["hits"]["hits"]

print(f"Form 4 trovati: {data['hits']['total']['value']}\n")
print("Struttura CIK nei primi 5 filing:")
print("-"*60)
for h in hits:
    src = h["_source"]
    print(f"Nomi:  {src.get('display_names')}")
    print(f"CIKs:  {src.get('ciks')}")
    print(f"ADSH:  {src.get('adsh')}")
    print()

# Carica mapping CIK -> ticker dalla SEC
print("Carico mapping CIK dalla SEC...")
r2 = requests.get("https://www.sec.gov/files/company_tickers.json",
                  headers=headers, verify=False)
mapping = r2.json()
# Crea dizionario CIK -> ticker
cik_map = {str(v["cik_str"]).zfill(10): v["ticker"].upper()
           for v in mapping.values()}
print(f"Mapping caricato: {len(cik_map)} ticker\n")

# Verifica se i CIK dei Form 4 matchano
print("Match CIK -> Ticker per i primi 5 filing:")
print("-"*60)
for h in hits:
    src  = h["_source"]
    ciks = src.get("ciks", [])
    names = src.get("display_names", [])
    for cik, name in zip(ciks, names):
        cik_padded = str(cik).zfill(10)
        ticker = cik_map.get(cik_padded, "NON TROVATO")
        print(f"  CIK {cik_padded} | {name[:40]} -> {ticker}")
    print()
