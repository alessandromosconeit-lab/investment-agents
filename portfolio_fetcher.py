"""
Portfolio Price Fetcher — aggiorna i prezzi live di tutti gli asset
del portafoglio ISP e UCG, salva in data/portfolio_prices.json.
"""
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import json, logging, time, os
from datetime import datetime
import yfinance as yf
import urllib3
urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("portfolio_fetcher")
os.makedirs("data", exist_ok=True)

ISP_EQUITY = [
    {"id":"SL_ISP",    "ticker":"SL.MI",    "name":"Sanlorenzo",        "qty":5000,  "refValue":180900.00,  "sector":"Luxury / Nautica",           "ptf":"ISP"},
    {"id":"SPM_ISP",   "ticker":"SPM.MI",   "name":"Saipem",            "qty":33350, "refValue":144338.80,  "sector":"Oil & Gas Services",         "ptf":"ISP"},
    {"id":"NVDA_ISP",  "ticker":"NVDA",     "name":"NVIDIA",            "qty":670,   "refValue":114010.21,  "sector":"Semiconduttori / AI",         "ptf":"ISP"},
    {"id":"AGS_ISP",   "ticker":"AGS.BR",   "name":"Ageas",             "qty":1200,  "refValue":84660.00,   "sector":"Assicurazioni",              "ptf":"ISP"},
    {"id":"RACE1_ISP", "ticker":"RACE.MI",  "name":"Ferrari (lotto 1)", "qty":250,   "refValue":83325.00,   "sector":"Luxury Vehicles",            "ptf":"ISP"},
    {"id":"AMZN_ISP",  "ticker":"AMZN",     "name":"Amazon",            "qty":300,   "refValue":63584.38,   "sector":"E-commerce / Cloud",         "ptf":"ISP"},
    {"id":"AAPL_ISP",  "ticker":"AAPL",     "name":"Apple",             "qty":150,   "refValue":40433.61,   "sector":"Consumer Tech",              "ptf":"ISP"},
    {"id":"ASML_ISP",  "ticker":"ASML.AS",  "name":"ASML",              "qty":25,    "refValue":40370.00,   "sector":"Semicond. Equipment",        "ptf":"ISP"},
    {"id":"RACE2_ISP", "ticker":"RACE.MI",  "name":"Ferrari (lotto 2)", "qty":110,   "refValue":36985.60,   "sector":"Luxury Vehicles",            "ptf":"ISP"},
    {"id":"TIT_ISP",   "ticker":"TIT.MI",   "name":"Telecom Italia",    "qty":4000,  "refValue":32520.00,   "sector":"Telecomunicazioni",          "ptf":"ISP"},
    {"id":"BABA_ISP",  "ticker":"BABA",     "name":"Alibaba",           "qty":300,   "refValue":25190.60,   "sector":"Tech / E-comm. Cina",        "ptf":"ISP"},
    {"id":"META_ISP",  "ticker":"META",     "name":"Meta Platforms",    "qty":45,    "refValue":22909.71,   "sector":"Social Media",              "ptf":"ISP"},
    {"id":"STLA1_ISP", "ticker":"STLAM.MI", "name":"Stellantis (l.1)",  "qty":2500,  "refValue":12620.00,   "sector":"Automobile",                "ptf":"ISP"},
    {"id":"BFF_ISP",   "ticker":"BFF.MI",   "name":"BFF Bank",          "qty":4000,  "refValue":12384.00,   "sector":"Bancario / Factoring",       "ptf":"ISP"},
    {"id":"DAL_ISP",   "ticker":"DAL",      "name":"Delta Air Lines",   "qty":150,   "refValue":12151.18,   "sector":"Compagnie Aeree",           "ptf":"ISP"},
    {"id":"FCT_ISP",   "ticker":"FCT.MI",   "name":"Fincantieri",       "qty":1000,  "refValue":10880.00,   "sector":"Cantieristica Nav.",         "ptf":"ISP"},
    {"id":"BA_ISP",    "ticker":"BA",       "name":"Boeing",            "qty":50,    "refValue":9890.82,    "sector":"Aerospazio / Difesa",        "ptf":"ISP"},
    {"id":"MSFT_ISP",  "ticker":"MSFT",     "name":"Microsoft",         "qty":25,    "refValue":8526.35,    "sector":"Software / Cloud",           "ptf":"ISP"},
    {"id":"XOM_ISP",   "ticker":"XOM",      "name":"Exxon Mobil",       "qty":60,    "refValue":7189.14,    "sector":"Petrolio & Gas",             "ptf":"ISP"},
    {"id":"NU_ISP",    "ticker":"NU",       "name":"Nu Holdings",       "qty":500,   "refValue":5943.49,    "sector":"Fintech",                   "ptf":"ISP"},
    {"id":"CPRI_ISP",  "ticker":"CPRI",     "name":"Capri Holdings",    "qty":250,   "refValue":4139.92,    "sector":"Moda / Lusso",               "ptf":"ISP"},
    {"id":"DHER_ISP",  "ticker":"DHER.DE",  "name":"Delivery Hero",     "qty":100,   "refValue":3607.00,    "sector":"Food Delivery Tech",         "ptf":"ISP"},
    {"id":"ABNB_ISP",  "ticker":"ABNB",     "name":"Airbnb",            "qty":25,    "refValue":3251.89,    "sector":"Hospitality Tech",           "ptf":"ISP"},
    {"id":"STLA2_ISP", "ticker":"STLAM.MI", "name":"Stellantis (l.2)",  "qty":409,   "refValue":2060.13,    "sector":"Automobile",                "ptf":"ISP"},
    {"id":"CNHI_ISP",  "ticker":"CNHI.MI",  "name":"CNH Industrial",    "qty":191,   "refValue":1788.30,    "sector":"Macchinari Industriali",     "ptf":"ISP"},
    {"id":"JUVE_ISP",  "ticker":"JUVE.MI",  "name":"Juventus FC",       "qty":580,   "refValue":1208.72,    "sector":"Sport / Intrattenimento",    "ptf":"ISP"},
    {"id":"IVG_ISP",   "ticker":"IVG.MI",   "name":"Iveco Group",       "qty":38,    "refValue":530.10,     "sector":"Veicoli Commerciali",        "ptf":"ISP"},
    {"id":"RCS_ISP",   "ticker":"RCS.MI",   "name":"RCS Mediagroup",    "qty":169,   "refValue":159.20,     "sector":"Media",                     "ptf":"ISP"},
    {"id":"FRVIA_ISP", "ticker":"FRVIA.PA", "name":"Forvia",            "qty":6,     "refValue":53.64,      "sector":"Componenti Automotive",      "ptf":"ISP"},
]

UCG_EQUITY = [
    {"id":"P911_UCG",  "ticker":"P911.DE",  "name":"Porsche AG",        "qty":250,   "refValue":11637.50,   "sector":"Luxury Vehicles",           "ptf":"UCG"},
    {"id":"FRVIA_UCG", "ticker":"FRVIA.PA", "name":"Forvia",            "qty":34,    "refValue":302.80,     "sector":"Componenti Automotive",     "ptf":"UCG"},
    {"id":"MB_UCG",    "ticker":"MB.MI",    "name":"Mediobanca",        "qty":2000,  "refValue":53200.00,   "sector":"Bancario / Invest.",         "ptf":"UCG"},
    {"id":"ISP_UCG",   "ticker":"ISP.MI",   "name":"Intesa Sanpaolo",   "qty":4500,  "refValue":27589.50,   "sector":"Bancario / Retail",          "ptf":"UCG"},
    {"id":"IRE_UCG",   "ticker":"IRE.MI",   "name":"Iren",              "qty":3250,  "refValue":8320.00,    "sector":"Utility Multi-Servizi",      "ptf":"UCG"},
    {"id":"ENI_UCG",   "ticker":"ENI.MI",   "name":"Eni",               "qty":1600,  "refValue":32568.00,   "sector":"Petrolio & Gas",             "ptf":"UCG"},
    {"id":"IF_UCG",    "ticker":"IF.MI",    "name":"Banca Ifis",        "qty":849,   "refValue":11775.63,   "sector":"Bancario / Factoring",       "ptf":"UCG"},
    {"id":"UCG_UCG",   "ticker":"UCG.MI",   "name":"UniCredit",         "qty":490,   "refValue":39959.50,   "sector":"Bancario",                  "ptf":"UCG"},
    {"id":"BFF_UCG",   "ticker":"BFF.MI",   "name":"BFF Bank",          "qty":4500,  "refValue":13914.00,   "sector":"Bancario / Factoring",       "ptf":"UCG"},
    {"id":"SPM_UCG",   "ticker":"SPM.MI",   "name":"Saipem",            "qty":10000, "refValue":43660.00,   "sector":"Oil & Gas Services",         "ptf":"UCG"},
    {"id":"BMPS_UCG",  "ticker":"BMPS.MI",  "name":"MPS",               "qty":32,    "refValue":354.56,     "sector":"Bancario",                  "ptf":"UCG"},
    {"id":"JUVE_UCG",  "ticker":"JUVE.MI",  "name":"Juventus FC",       "qty":500,   "refValue":1042.00,    "sector":"Sport / Intrattenimento",    "ptf":"UCG"},
    {"id":"AIR_UCG",   "ticker":"AIR.PA",   "name":"Airbus",            "qty":40,    "refValue":8220.00,    "sector":"Aerospazio / Difesa",        "ptf":"UCG"},
    {"id":"STLA_UCG",  "ticker":"STLAM.MI", "name":"Stellantis",        "qty":2000,  "refValue":10058.00,   "sector":"Automobile",                "ptf":"UCG"},
    {"id":"BRE_UCG",   "ticker":"BRE.MI",   "name":"Brembo",            "qty":1000,  "refValue":10610.00,   "sector":"Componenti Automotive",      "ptf":"UCG"},
]

ALL_EQUITY = ISP_EQUITY + UCG_EQUITY
UNIQUE_TICKERS = list({p["ticker"] for p in ALL_EQUITY})


def fetch_prices(tickers):
    prices = {}
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            price = (info.get("currentPrice") or
                     info.get("regularMarketPrice") or
                     info.get("previousClose"))
            if price:
                prices[ticker] = float(price)
                logger.info(f"  {ticker}: {price:.2f}")
            time.sleep(0.15)
        except Exception as e:
            logger.warning(f"  {ticker}: {e}")
    return prices


def main():
    logger.info(f"Fetching {len(UNIQUE_TICKERS)} unique tickers...")
    prices = fetch_prices(UNIQUE_TICKERS)

    positions = []
    isp_ref = isp_cur = ucg_ref = ucg_cur = 0
    for pos in ALL_EQUITY:
        price = prices.get(pos["ticker"])
        cur = price * pos["qty"] if price else None
        ref = pos["refValue"]
        pnl = cur - ref if cur else None
        pnl_pct = pnl / ref * 100 if pnl is not None and ref else None
        positions.append({**pos, "currentPrice": price,
                          "currentValue": cur, "pnlAbs": pnl, "pnlPct": pnl_pct})
        if pos["ptf"] == "ISP":
            isp_ref += ref
            if cur: isp_cur += cur
        else:
            ucg_ref += ref
            if ucg_cur is not None and cur: ucg_cur += cur

    snapshot = {
        "updated": datetime.now().isoformat(),
        "prices": prices,
        "positions": positions,
        "summary": {
            "ispRefEquity":    round(isp_ref, 2),
            "ispCurEquity":    round(isp_cur, 2),
            "ucgRefEquity":    round(ucg_ref, 2),
            "ucgCurEquity":    round(ucg_cur, 2),
            "totalRefEquity":  round(isp_ref + ucg_ref, 2),
            "totalCurEquity":  round(isp_cur + ucg_cur, 2),
            "pnlEquity":       round((isp_cur + ucg_cur) - (isp_ref + ucg_ref), 2),
            "ispNonEquity":    64571.47,
            "ucgNonEquity":    181934.79,
            "ispCash":         2633.63,
            "grandTotalRef":   1487983.17,
        }
    }

    with open("data/portfolio_prices.json", "w") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, default=str)

    s = snapshot["summary"]
    logger.info(f"✅ Salvato in data/portfolio_prices.json")
    logger.info(f"   Equity totale ref:  €{s['totalRefEquity']:,.0f}")
    logger.info(f"   Equity totale live: €{s['totalCurEquity']:,.0f}")
    logger.info(f"   P&L equity: €{s['pnlEquity']:+,.0f}")


if __name__ == "__main__":
    main()
