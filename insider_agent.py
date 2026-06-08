"""
Insider Agent — monitora le operazioni di acquisto/vendita
dei manager aziendali su S&P 500, Russell 1000 e principali
indici europei (FTSE MIB, DAX, CAC 40, Euro Stoxx 600).

Fonti:
  - USA: SEC EDGAR submissions API (gratuito, per-company)
  - Europa: yfinance insider_transactions (copertura parziale)

Filtro: solo operazioni con valore > $100.000 / €100.000
"""

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import time
import logging
import requests
import urllib3
import xml.etree.ElementTree as ET
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import date, datetime, timedelta
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)

SEC_TICKERS     = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES    = "https://www.sec.gov/Archives/edgar/data"
USER_AGENT      = "InvestmentAgents contact@investment-agents.com"
MIN_VALUE_USD   = 100_000
MIN_VALUE_EUR   = 100_000
DELAY           = 0.12

BUY_CODES  = {"P"}
SELL_CODES = {"S"}
SKIP_CODES = {"A","M","F","G","D","X","C","W","J","K","L","U","Z"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _get(url: str, params: dict = {}, timeout: int = 15) -> Optional[dict]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    try:
        r = requests.get(url, params=params, headers=headers,
                         timeout=timeout, verify=False)
        r.raise_for_status()
        time.sleep(DELAY)
        return r.json()
    except Exception as e:
        logger.debug(f"HTTP error [{url}]: {e}")
        return None


def _safe_float(val) -> Optional[float]:
    try:
        return float(val) if val not in (None, "", "None", "nan") else None
    except Exception:
        return None


# ── Mapping CIK ↔ Ticker ──────────────────────────────────────────────────────

_cik_to_ticker: dict = {}
_ticker_to_cik: dict = {}


def _load_sec_tickers():
    global _cik_to_ticker, _ticker_to_cik
    if _cik_to_ticker:
        return
    data = _get(SEC_TICKERS)
    if not data:
        logger.warning("Impossibile caricare mapping CIK dalla SEC")
        return
    for entry in data.values():
        cik    = str(entry.get("cik_str", "")).zfill(10)
        ticker = entry.get("ticker", "").upper()
        if cik and ticker:
            _cik_to_ticker[cik] = ticker
            _ticker_to_cik[ticker] = cik
    logger.info(f"  Mapping SEC: {len(_cik_to_ticker)} ticker caricati")


# ── Fetch Form 4 per singola azienda ─────────────────────────────────────────

def _get_recent_form4_info(cik: str,
                            days_back: int = 14) -> list[tuple[str,str,str]]:
    """
    Recupera i Form 4 recenti per un'azienda dalla submissions API.
    Restituisce lista di (accn_clean, filer_cik_folder, primary_doc).
    La submissions API include già il nome del file XML primario —
    evitiamo così di cercare l'indice del filing.
    """
    url  = SEC_SUBMISSIONS.format(cik=cik)
    data = _get(url)
    if not data:
        return []

    recent       = data.get("filings", {}).get("recent", {})
    forms        = recent.get("form",            [])
    dates        = recent.get("filingDate",       [])
    accns        = recent.get("accessionNumber",  [])
    primary_docs = recent.get("primaryDocument",  [])

    cutoff = date.today() - timedelta(days=days_back)
    result = []

    for form, d, accn, pdoc in zip(forms, dates, accns, primary_docs):
        if form not in ("4", "4/A"):
            continue
        try:
            filing_date = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue

        if filing_date >= cutoff:
            accn_clean  = accn.replace("-", "")
            # Il CIK folder è ricavato dall'accession number (= CIK del filer)
            filer_folder = accn_clean[:10].lstrip("0") or "0"
            result.append((accn_clean, filer_folder, pdoc or ""))
        elif filing_date < cutoff - timedelta(days=2):
            # I filing sono in ordine decrescente — possiamo fermarci
            break

    return result


# ── Download e parsing XML ────────────────────────────────────────────────────

def _xml_find_text(root: ET.Element, tag: str) -> str:
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == tag:
            for child in elem:
                ct = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if ct == "value" and child.text:
                    return child.text.strip()
            return (elem.text or "").strip()
    return ""


def _xml_findall(root: ET.Element, tag: str) -> list[ET.Element]:
    return [e for e in root.iter()
            if (e.tag.split("}")[-1] if "}" in e.tag else e.tag) == tag]


def _download_form4_xml(filer_folder: str, accn_clean: str,
                         primary_doc: str) -> Optional[str]:
    """
    Scarica il contenuto XML del Form 4.
    Prova prima il primaryDocument dalla submissions API,
    poi fallback su nomi comuni.
    """
    headers  = {"User-Agent": USER_AGENT}
    base_url = f"{SEC_ARCHIVES}/{filer_folder}/{accn_clean}"

    candidates = []
    if primary_doc and primary_doc.endswith(".xml"):
        candidates.append(primary_doc)
    candidates += ["form4.xml", "form4.htm"]

    # Fallback: lista la directory
    for filename in candidates:
        url = f"{base_url}/{filename}"
        try:
            r = requests.get(url, headers=headers, timeout=10, verify=False)
            if r.status_code == 200 and "<ownershipDocument" in r.text:
                time.sleep(DELAY)
                return r.text
        except Exception:
            pass

    # Ultimo fallback: scarica l'indice HTML e cerca il file XML
    try:
        idx_url = f"{base_url}/{accn_clean[:10]}-{accn_clean[10:12]}-{accn_clean[12:]}-index.htm"
        r = requests.get(idx_url, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            import re
            xmls = re.findall(r'href="([^"]+\.xml)"', r.text)
            for xml_file in xmls:
                xml_url = f"{base_url}/{xml_file.split('/')[-1]}"
                r2 = requests.get(xml_url, headers=headers, timeout=10, verify=False)
                if r2.status_code == 200 and "<ownershipDocument" in r2.text:
                    time.sleep(DELAY)
                    return r2.text
    except Exception:
        pass

    return None


def _extract_transactions(xml_text: str, ticker: str) -> list[dict]:
    transactions = []
    try:
        root = ET.fromstring(xml_text)

        owner_name = _xml_find_text(root, "rptOwnerName")
        role_parts = []
        for tag in ["isOfficer","isDirector","isTenPercentOwner"]:
            if _xml_find_text(root, tag) in ("1","true","True"):
                role_parts.append(tag.replace("is",""))
        title = _xml_find_text(root, "officerTitle")
        if title:
            role_parts.append(title)
        owner_role   = ", ".join(role_parts)
        company_name = _xml_find_text(root, "issuerName")

        for tx_el in _xml_findall(root, "nonDerivativeTransaction"):
            code      = _xml_find_text(tx_el, "transactionCode")
            shares    = _safe_float(_xml_find_text(tx_el, "transactionShares"))
            price     = _safe_float(_xml_find_text(tx_el, "transactionPricePerShare"))
            tx_date   = _xml_find_text(tx_el, "transactionDate")
            sec_title = _xml_find_text(tx_el, "securityTitle") or "Common Stock"

            if not code or code in SKIP_CODES:
                continue
            if code not in (BUY_CODES | SELL_CODES):
                continue
            if code in BUY_CODES and (price is None or price == 0):
                continue

            value = (shares * price) if shares and price else None

            transactions.append({
                "ticker":           ticker,
                "company_name":     company_name or ticker,
                "insider_name":     owner_name,
                "insider_role":     owner_role,
                "transaction_code": code,
                "transaction_type": "ACQUISTO" if code in BUY_CODES else "VENDITA",
                "security_title":   sec_title,
                "shares":           shares,
                "price":            price,
                "value_usd":        value,
                "date":             tx_date,
                "currency":         "USD",
                "market":           "US",
            })

    except ET.ParseError as e:
        logger.debug(f"XML parse error: {e}")
    except Exception as e:
        logger.debug(f"Extraction error: {e}")

    return transactions


# ── Fetch USA ─────────────────────────────────────────────────────────────────

def _fetch_us_insider_transactions(us_tickers: list[str],
                                    days_back: int = 14) -> list[dict]:
    all_transactions = []
    processed = 0

    for ticker in us_tickers:
        cik = _ticker_to_cik.get(ticker.upper())
        if not cik:
            processed += 1
            continue

        form4_list = _get_recent_form4_info(cik, days_back)

        for accn_clean, filer_folder, primary_doc in form4_list:
            xml_text = _download_form4_xml(filer_folder, accn_clean, primary_doc)
            if not xml_text:
                continue
            txs = _extract_transactions(xml_text, ticker)
            for tx in txs:
                val = tx.get("value_usd") or 0
                if abs(val) >= MIN_VALUE_USD:
                    all_transactions.append(tx)

        processed += 1
        if processed % 50 == 0:
            logger.info(f"  Aziende processate: {processed}/{len(us_tickers)}")

    logger.info(f"  Transazioni USA qualificate: {len(all_transactions)}")
    return all_transactions


# ── Fetch Europa ──────────────────────────────────────────────────────────────

def _fetch_eu_insider_transactions(tickers: list[str]) -> list[dict]:
    transactions = []
    cutoff = date.today() - timedelta(days=14)

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            df    = stock.insider_transactions
            if df is None or df.empty:
                continue

            df.columns = [c.lower().replace(" ", "_") for c in df.columns]

            for _, row in df.iterrows():
                tx_date = None
                for col in ("start_date","date","transaction_date"):
                    raw = row.get(col)
                    if raw is not None:
                        try:
                            tx_date = (raw.date() if hasattr(raw, "date")
                                       else datetime.strptime(str(raw)[:10],
                                                              "%Y-%m-%d").date())
                            break
                        except Exception:
                            pass
                if tx_date and tx_date < cutoff:
                    continue

                value = _safe_float(row.get("value") or row.get("transaction_value"))
                if not value:
                    shares = _safe_float(row.get("shares"))
                    price  = _safe_float(row.get("pricepershare") or
                                         row.get("price_per_share"))
                    value  = (shares * price) if shares and price else None

                if not value or abs(value) < MIN_VALUE_EUR:
                    continue

                text    = str(row.get("text","") or row.get("transaction","")).lower()
                tx_type = ("ACQUISTO"
                           if any(w in text for w in ["purchase","buy","acqui"])
                           else "VENDITA")

                transactions.append({
                    "ticker":           ticker,
                    "company_name":     ticker,
                    "insider_name":     str(row.get("insider","") or row.get("name","")),
                    "insider_role":     str(row.get("relation","") or row.get("position","")),
                    "transaction_code": "P" if tx_type == "ACQUISTO" else "S",
                    "transaction_type": tx_type,
                    "security_title":   "Common Stock",
                    "shares":           _safe_float(row.get("shares")),
                    "price":            _safe_float(row.get("pricepershare") or
                                                    row.get("price_per_share")),
                    "value_usd":        value,
                    "date":             str(tx_date) if tx_date else "",
                    "currency":         "EUR",
                    "market":           "EU",
                })

            time.sleep(DELAY)

        except Exception as e:
            logger.debug(f"yfinance insider error [{ticker}]: {e}")

    logger.info(f"  Transazioni EU trovate: {len(transactions)}")
    return transactions


# ── Pipeline principale ───────────────────────────────────────────────────────

def run_insider_agent(us_tickers: list[str],
                      eu_tickers: list[str]) -> list[dict]:
    logger.info("\n" + "="*50)
    logger.info("  Avvio INSIDER AGENT")
    logger.info("="*50)

    _load_sec_tickers()

    logger.info(f"  Fetch Form 4 USA per {len(us_tickers)} aziende...")
    us_transactions = _fetch_us_insider_transactions(us_tickers, days_back=14)

    logger.info("  Fetch insider Europa (yfinance)...")
    eu_transactions = _fetch_eu_insider_transactions(eu_tickers[:200])

    all_tx = us_transactions + eu_transactions
    all_tx.sort(key=lambda x: abs(x.get("value_usd") or 0), reverse=True)

    buys  = [t for t in all_tx if t["transaction_code"] in BUY_CODES]
    sells = [t for t in all_tx if t["transaction_code"] in SELL_CODES]

    logger.info(f"  Acquisti qualificati: {len(buys)}")
    logger.info(f"  Vendite qualificate:  {len(sells)}")

    return all_tx
