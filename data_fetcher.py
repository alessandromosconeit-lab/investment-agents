"""
Modulo di fetch dei dati fondamentali.
Fonti:
  - financedatabase: lista ticker europei
  - FMP stable API: dati fondamentali (quote, ratios, income statement)
  - yfinance: fallback per ticker non coperti da FMP + dati ETF
"""

import time
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import logging
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import yfinance as yf
from typing import Optional

import config
from universe import get_financedatabase_tickers, UNIVERSE_CONFIG

logger   = logging.getLogger(__name__)
FMP_BASE = "https://financialmodelingprep.com/stable"
DELAY    = 0.25


def _safe_float(value, default=None) -> Optional[float]:
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _fmp_get(endpoint: str, params: dict = {}) -> Optional[list | dict]:
    """Chiama FMP stable API e restituisce il JSON."""
    params["apikey"] = config.FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=15, verify=False)
        r.raise_for_status()
        data = r.json()
        time.sleep(DELAY)
        return data
    except Exception as e:
        logger.debug(f"FMP error [{endpoint}]: {e}")
        return None


# ── Universo USA ──────────────────────────────────────────────────────────────

def get_sp500_tickers() -> list[str]:
    tickers = [
        "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","A","APD","ABNB",
        "AKAM","ALB","ARE","ALGN","ALLE","LNT","ALL","GOOGL","GOOG","MO","AMZN",
        "AMCR","AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP","AME","AMGN",
        "APH","ADI","ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET",
        "AJG","AIZ","T","ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL",
        "BAC","BK","BBWI","BAX","BDX","WRB","BBY","BIO","TECH","BIIB","BLK","BX",
        "BA","BMY","AVGO","BR","BRO","BF-B","BLDR","BXP","CHRW","CDNS","CZR",
        "CPT","CPB","COF","CAH","KMX","CCL","CARR","CAT","CBOE","CBRE","CDW",
        "CE","COR","CNC","CNP","CF","CHTR","CVX","CMG","CB","CHD","CI","CINF",
        "CTAS","CSCO","C","CFG","CLX","CME","CMS","KO","CTSH","CL","CMCSA",
        "CMA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CTVA","CSGP",
        "COST","CTRA","CCI","CSX","CMI","CVS","DHI","DHR","DRI","DVA","DAY",
        "DE","DAL","XRAY","DVN","DXCM","FANG","DLR","DFS","DG","DLTR","D",
        "DPZ","DOV","DOW","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX","EW",
        "EA","ELV","LLY","EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX",
        "EQR","ESS","EL","ETSY","EG","EVRG","ES","EXC","EXPE","EXPD","EXR",
        "XOM","FFIV","FDS","FICO","FAST","FRT","FDX","FIS","FITB","FSLR","FE",
        "FI","FLT","FMC","F","FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT",
        "GE","GEHC","GEV","GEN","GNRC","GD","GIS","GM","GPC","GILD","GS","HAL",
        "HIG","HAS","HCA","DOC","HSIC","HSY","HES","HPE","HLT","HOLX","HD",
        "HON","HRL","HST","HWM","HPQ","HUBB","HUM","HBAN","HII","IBM","IEX",
        "IDXX","ITW","INCY","IR","PODD","INTC","ICE","IFF","IP","IPG","INTU",
        "ISRG","IVZ","INVH","IQV","IRM","JBHT","JBL","JKHY","J","JNJ","JCI",
        "JPM","JNPR","K","KVUE","KDP","KEY","KEYS","KMB","KIM","KMI","KLAC",
        "KHC","KR","LHX","LH","LRCX","LW","LVS","LDOS","LEN","LIN","LYV",
        "LKQ","LMT","L","LOW","LULU","LYB","MTB","MRO","MPC","MKTX","MAR",
        "MMC","MLM","MAS","MA","MTCH","MKC","MCD","MCK","MDT","MRK","META",
        "MET","MTD","MGM","MCHP","MU","MSFT","MAA","MRNA","MHK","MOH","TAP",
        "MDLZ","MPWR","MNST","MCO","MS","MOS","MSI","MSCI","NDAQ","NTAP",
        "NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC","NTRS","NOC",
        "NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY","OXY","ODFL","OMC","ON",
        "OKE","ORCL","OTIS","PCAR","PKG","PANW","PARA","PH","PAYX","PAYC",
        "PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC","POOL","PPG",
        "PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","QRVO",
        "PWR","QCOM","DGX","RL","RJF","RTX","O","REG","REGN","RF","RSG","RMD",
        "RVTY","ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SBAC","SLB","STX",
        "SRE","NOW","SHW","SPG","SWKS","SJM","SNA","SOLV","SO","LUV","SWK",
        "SBUX","STT","STLD","STE","SYK","SMCI","SYF","SNPS","SYY","TMUS",
        "TROW","TTWO","TPR","TRGP","TGT","TEL","TDY","TFX","TER","TSLA","TXN",
        "TXT","TMO","TJX","TSCO","TT","TDG","TRV","TRMB","TFC","TYL","TSN",
        "USB","UBER","UDR","ULTA","UNP","UAL","UPS","URI","UNH","UHS","VLO",
        "VTR","VLTO","VRSN","VRSK","VZ","VRTX","VTRS","VICI","V","VST","VMC",
        "WAB","WBA","WMT","DIS","WBD","WM","WAT","WEC","WFC","WELL","WST",
        "WDC","WY","WHR","WMB","WTW","GWW","WYNN","XEL","XYL","YUM","ZBRA",
        "ZBH","ZTS",
    ]
    logger.info(f"  S&P 500: {len(tickers)} ticker")
    return list(dict.fromkeys(tickers))


def get_russell1000_tickers() -> list[str]:
    tickers = [
        "AXTA","AZPN","COLD","FND","HALO","HXL","INGR","LEVI","LITE","LSTR",
        "MANH","MEDP","NOVT","OGN","OMCL","ONTO","OSK","PFGC","PI","PLNT",
        "PRGO","RBC","RGEN","RRX","SAIC","SITE","SKX","SLM","SMG","SRCL",
        "SSD","STAG","TNET","TREX","UFPI","WEX","WMS","WSO","ZI","ACM","ADNT",
        "AIT","ALG","ALKS","AMKR","APAM","APOG","APPF","ARW","ASH","ASGN",
        "ATI","AVAV","AWI","AX","BCO","BFH","BOOT","BOX","BRC","BRKR","CABO",
        "CAKE","CALM","CASY","CBSH","CELH","CHCO","CHE","CHRD","CHWY","CIR",
        "CIVI","CLB","CNM","CNX","COHU","COLM","COOP","CPRI","CRC","CROX",
        "CRS","CSL","CSWI","CW","CWST","DDS","DDOG","DFIN","DKS","DORM",
        "DXC","DOCS","DRH","DY","EAT","EBC","EGP","ENOV","EPRT","ESNT",
        "EVTC","EXP","EXTR","FCNCA","FFIN","FIVN","FRPT","GFF","GHC","GKOS",
        "GTLS","HAE","HAYW","HCC","HELE","HIMS","HLMN","HRI","HTH","IBP",
        "ICFI","IPGP","IRT","ITRI","JACK","JAZZ","KFY","KMPR","KTOS","KVYO",
        "LBRT","LC","LCII","LEA","LGND","LIVN","LMAT","LNC","LNTH","LGIH",
        "LPLA","LUMN","MGNI","MMSI","MODV","MRCY","MSGS","MTH","NARI","NEO",
        "NMIH","NPO","NTGR","NTRA","NUS","NVT","OFIX","OGS","OII","OMAB",
        "OUT","PARR","PATK","PCRX","PDCO","PENN","PGNY","PINC","PIPR","PLAB",
        "PLAY","PLXS","PMT","PNM","POWL","PPBI","PSMT","PTEN","PVH","QLYS",
        "RAMP","RARE","RBA","RCKT","RDNT","REZI","RGP","RMBS","ROCK","RPD",
        "RXO","SAFE","SAIA","SANM","SCI","SIGI","SITM","SJW","SKT","SMPL",
        "SNV","SPNT","SPSC","STC","STRA","SUM","SUPN","TALO","TCMD","TDS",
        "TGTX","THG","THRM","TKR","TMHC","TOWN","TRNO","TRUP","TTEC","TTGT",
        "TWI","UCTT","UDMY","UMBF","UNF","UPBD","USPH","VBTX","VCYT","VGR",
        "VLY","VSCO","VSTO","VVV","WABC","WAFD","WASH","WD","WDFC","WERN",
        "WKC","WLK","WOLF","WRLD","WU","WWD",
    ]
    logger.info(f"  Russell 1000 extra: {len(tickers)} ticker")
    return list(dict.fromkeys(tickers))


def get_us_stock_universe() -> list[str]:
    sp500    = get_sp500_tickers()
    russell  = get_russell1000_tickers()
    combined = list(dict.fromkeys(sp500 + russell))
    logger.info(f"Universo US totale: {len(combined)} ticker")
    return combined


def get_european_stock_universe() -> list[str]:
    cfg       = UNIVERSE_CONFIG["stocks"]["europe"]
    countries = cfg.get("countries", [])
    tickers   = get_financedatabase_tickers(countries=countries)
    if not tickers:
        logger.warning("financedatabase vuoto — uso fallback hardcoded")
        from universe import _get_european_hardcoded
        tickers = _get_european_hardcoded()
    logger.info(f"Universo EU: {len(tickers)} ticker")
    return tickers


def get_etf_tickers(region: str) -> list[str]:
    if region == "europe":
        return [
            "VWCE.DE","IWDA.AS","CSPX.AS","EQQQ.DE","SWDA.AS","IUSQ.DE",
            "XDWD.DE","VEUR.AS","IEMA.AS","IUSE.AS","EXS1.DE","EXSA.DE",
            "DBXD.DE","LYPS.DE","IQQH.DE","IUSN.DE","ZPRV.DE","ZPRX.DE",
            "XDEM.DE","SPPW.DE","HMWO.AS","IEAG.AS","IBCI.AS","EUNH.DE",
            "EUN2.DE","IBGS.AS","IQQD.DE","WTAI.SW",
        ]
    else:
        return [
            "SPY","IVV","VOO","QQQ","VTI","IWM","EFA","VEA","VWO","GLD",
            "IWF","IWD","SCHD","VIG","DGRO","NOBL","XLK","XLF","XLV","XLE",
            "XLI","XLY","XLP","XLU","XLRE","AGG","BND","TLT","IEF","SHY",
            "LQD","HYG","MUB","ARKK","BOTZ","ROBO","ICLN","ESGU","DRIV",
        ]


# ── Dati fondamentali via FMP stable ─────────────────────────────────────────

def build_stock_data(ticker: str) -> Optional[dict]:
    """
    Recupera dati fondamentali via FMP stable API.
    Fallback su yfinance se FMP non copre il ticker.
    """
    # ── 1. Quote (prezzo + market cap) ───────────────────────────────────────
    quote_data = _fmp_get("quote", {"symbol": ticker})
    if not quote_data or not isinstance(quote_data, list) or len(quote_data) == 0:
        return _build_stock_data_yfinance(ticker)   # fallback

    q = quote_data[0]
    market_cap = _safe_float(q.get("marketCap"), 0)
    if market_cap < config.MIN_MARKET_CAP_USD:
        return None

    price    = _safe_float(q.get("price"))
    exchange = q.get("exchange", "N/A")
    name     = q.get("name", ticker)

    # ── 2. Ratios (P/E, P/B, ROE, ROIC, margini ecc.) ────────────────────────
    ratios_data = _fmp_get("ratios", {"symbol": ticker, "limit": 5})
    r0 = ratios_data[0] if ratios_data and isinstance(ratios_data, list) else {}

    pe_ratio         = _safe_float(r0.get("priceEarningsRatio"))
    pb_ratio         = _safe_float(r0.get("priceToBookRatio"))
    ev_ebitda        = _safe_float(r0.get("enterpriseValueMultiple"))
    roe              = _safe_float(r0.get("returnOnEquity"))
    roic             = _safe_float(r0.get("returnOnInvestedCapital") or
                                   r0.get("returnOnCapitalEmployed"))
    gross_margin     = _safe_float(r0.get("grossProfitMargin"))
    operating_margin = _safe_float(r0.get("operatingProfitMargin"))
    net_margin       = _safe_float(r0.get("netProfitMargin"))
    debt_equity      = _safe_float(r0.get("debtEquityRatio"))
    current_ratio    = _safe_float(r0.get("currentRatio"))
    dividend_yield   = _safe_float(r0.get("dividendYield"), 0)
    price_to_fcf     = _safe_float(r0.get("priceToFreeCashFlowsRatio"))

    # ── 3. Income Statement (ricavi, utili, EPS) ──────────────────────────────
    income_data = _fmp_get("income-statement", {"symbol": ticker, "limit": 5})
    i0 = income_data[0] if income_data and isinstance(income_data, list) else {}
    i1 = income_data[1] if income_data and len(income_data) > 1 else {}
    i2 = income_data[2] if income_data and len(income_data) > 2 else {}

    revenue    = _safe_float(i0.get("revenue"))
    net_income = _safe_float(i0.get("netIncome"))
    eps        = _safe_float(i0.get("eps"))
    fcf        = _safe_float(i0.get("freeCashFlow"))

    # Crescita ricavi
    rev_0 = revenue
    rev_1 = _safe_float(i1.get("revenue"))
    rev_2 = _safe_float(i2.get("revenue"))
    revenue_growth_1y = ((rev_0 - rev_1) / abs(rev_1)
                         if rev_0 and rev_1 and rev_1 != 0 else None)
    revenue_growth_2y = ((rev_1 - rev_2) / abs(rev_2)
                         if rev_1 and rev_2 and rev_2 != 0 else None)

    # Crescita EPS
    eps_1 = _safe_float(i1.get("eps"))
    eps_growth = ((eps - eps_1) / abs(eps_1)
                  if eps and eps_1 and eps_1 != 0 else None)

    # Anni crescita positiva (su 5 anni)
    revenues = [_safe_float((income_data[i] if i < len(income_data) else {}).get("revenue"))
                for i in range(5)]
    years_positive_growth = sum(
        1 for i in range(len(revenues) - 1)
        if revenues[i] and revenues[i+1] and revenues[i] > revenues[i+1]
    )

    # ── 4. Profile (settore, paese, descrizione) ──────────────────────────────
    profile_data = _fmp_get("profile", {"symbol": ticker})
    p0 = profile_data[0] if profile_data and isinstance(profile_data, list) else {}

    sector      = p0.get("sector", q.get("sector", "N/A"))
    industry    = p0.get("industry", "N/A")
    country     = p0.get("country", "N/A")
    currency    = p0.get("currency", "USD")
    description = p0.get("description", "")[:500]

    return {
        "ticker":                ticker,
        "name":                  name,
        "sector":                sector,
        "industry":              industry,
        "exchange":              exchange,
        "country":               country,
        "currency":              currency,
        "market_cap":            market_cap,
        "price":                 price,
        "description":           description,
        "pe_ratio":              pe_ratio,
        "pb_ratio":              pb_ratio,
        "ev_ebitda":             ev_ebitda,
        "price_to_fcf":          price_to_fcf,
        "roe":                   roe,
        "roic":                  roic,
        "gross_margin":          gross_margin,
        "operating_margin":      operating_margin,
        "net_margin":            net_margin,
        "revenue_growth_1y":     revenue_growth_1y,
        "revenue_growth_2y":     revenue_growth_2y,
        "eps_growth_1y":         eps_growth,
        "years_positive_growth": years_positive_growth,
        "debt_equity":           debt_equity,
        "current_ratio":         current_ratio,
        "fcf":                   fcf,
        "fcf_positive":          (fcf is not None and fcf > 0),
        "net_income":            net_income,
        "eps":                   eps,
        "earnings_positive":     (net_income is not None and net_income > 0),
        "dividend_yield":        dividend_yield,
        "revenue":               revenue,
    }


def _build_stock_data_yfinance(ticker: str) -> Optional[dict]:
    """Fallback yfinance per ticker non coperti da FMP."""
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info
        if not info or (not info.get("regularMarketPrice") and
                        not info.get("currentPrice")):
            return None
        market_cap = _safe_float(info.get("marketCap"), 0)
        if market_cap < config.MIN_MARKET_CAP_USD:
            return None
        if info.get("quoteType") in ("ETF", "MUTUALFUND", "FUTURE", "INDEX"):
            return None

        debt_equity = _safe_float(info.get("debtToEquity"))
        if debt_equity:
            debt_equity = debt_equity / 100

        net_income = _safe_float(info.get("netIncomeToCommon"))
        fcf        = _safe_float(info.get("freeCashflow"))
        time.sleep(DELAY)

        return {
            "ticker":                ticker,
            "name":                  info.get("longName") or info.get("shortName", ticker),
            "sector":                info.get("sector", "N/A"),
            "industry":              info.get("industry", "N/A"),
            "exchange":              info.get("exchange", "N/A"),
            "country":               info.get("country", "N/A"),
            "currency":              info.get("currency", "USD"),
            "market_cap":            market_cap,
            "price":                 _safe_float(info.get("currentPrice") or
                                                 info.get("regularMarketPrice")),
            "description":           info.get("longBusinessSummary", "")[:500],
            "pe_ratio":              _safe_float(info.get("trailingPE")),
            "pb_ratio":              _safe_float(info.get("priceToBook")),
            "ev_ebitda":             _safe_float(info.get("enterpriseToEbitda")),
            "price_to_fcf":          None,
            "roe":                   _safe_float(info.get("returnOnEquity")),
            "roic":                  None,
            "gross_margin":          _safe_float(info.get("grossMargins")),
            "operating_margin":      _safe_float(info.get("operatingMargins")),
            "net_margin":            _safe_float(info.get("profitMargins")),
            "revenue_growth_1y":     _safe_float(info.get("revenueGrowth")),
            "revenue_growth_2y":     None,
            "eps_growth_1y":         _safe_float(info.get("earningsGrowth")),
            "years_positive_growth": 0,
            "debt_equity":           debt_equity,
            "current_ratio":         _safe_float(info.get("currentRatio")),
            "fcf":                   fcf,
            "fcf_positive":          (fcf is not None and fcf > 0),
            "net_income":            net_income,
            "eps":                   _safe_float(info.get("trailingEps")),
            "earnings_positive":     (net_income is not None and net_income > 0),
            "dividend_yield":        _safe_float(info.get("dividendYield"), 0),
            "revenue":               _safe_float(info.get("totalRevenue")),
        }
    except Exception as e:
        logger.debug(f"yfinance fallback error [{ticker}]: {e}")
        return None


def build_etf_data(ticker: str) -> Optional[dict]:
    """Dati ETF via yfinance."""
    try:
        etf  = yf.Ticker(ticker)
        info = etf.info
        if not info or info.get("quoteType") not in ("ETF", "MUTUALFUND"):
            return None

        total_assets  = _safe_float(info.get("totalAssets"), 0)
        expense_ratio = _safe_float(info.get("annualReportExpenseRatio") or
                                    info.get("expenseRatio"))
        hist  = etf.history(period="1y")
        ret_1y = None
        if not hist.empty:
            s, e = hist["Close"].iloc[0], hist["Close"].iloc[-1]
            ret_1y = (e - s) / s if s else None

        time.sleep(DELAY)

        return {
            "ticker":        ticker,
            "name":          info.get("longName") or info.get("shortName", ticker),
            "category":      info.get("category", "N/A"),
            "exchange":      info.get("exchange", "N/A"),
            "currency":      info.get("currency", "USD"),
            "total_assets":  total_assets,
            "expense_ratio": expense_ratio,
            "return_1y":     ret_1y,
            "description":   info.get("longBusinessSummary", "")[:300],
        }
    except Exception as e:
        logger.warning(f"ETF error [{ticker}]: {e}")
        return None
