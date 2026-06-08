import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import requests, urllib3
urllib3.disable_warnings()
HEADERS = {"User-Agent": "InvestmentAgents contact@investment-agents.com"}
adsh = "0001968243-26-000034"
adsh_clean = adsh.replace("-", "")
filer_cik = adsh_clean[:10].lstrip("0") or "0"
print("Filer CIK:", filer_cik)
index_url = f"https://www.sec.gov/Archives/edgar/data/{filer_cik}/{adsh_clean}/{adsh}-index.json"
print("URL:", index_url)
r = requests.get(index_url, headers=HEADERS, timeout=15, verify=False)
print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    files = data.get("directory", {}).get("item", [])
    for f in files:
        print(" ", f.get("name"), f.get("type"))
else:
    print(r.text[:200])