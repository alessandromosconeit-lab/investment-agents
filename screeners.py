"""
Modulo di screening — applica i criteri fondamentali di ogni agente.
Ogni funzione riceve un dizionario di dati e restituisce:
  - (True, score, notes) se l'asset passa il filtro
  - (False, 0, notes) se non passa
Lo score serve per ordinare i candidati prima di passarli a Claude.
"""

from typing import Optional
import config


# ── Helpers ───────────────────────────────────────────────────────────────────

def _v(d: dict, key: str) -> Optional[float]:
    """Restituisce il valore float da un dict, o None."""
    val = d.get(key)
    return float(val) if val is not None else None


def _pct(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"{val * 100:.1f}%"


def _fmt(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}"


# ── VALUE SCREENER ─────────────────────────────────────────────────────────────

def screen_value(data: dict) -> tuple[bool, float, list[str]]:
    """
    Criteri:
      - P/E < 15 (assoluto) — o indicazione settoriale nel report
      - P/B < 1.5
      - EV/EBITDA < 10
      - Debt/Equity < 1
      - Utile netto positivo
      - FCF positivo
    Score: somma di quante soglie sono rispettate + bonus per distanza dalla soglia.
    """
    c     = config.VALUE_CRITERIA
    notes = []
    score = 0.0
    passed_checks = 0
    total_checks  = 5   # numero di criteri hard

    pe  = _v(data, "pe_ratio")
    pb  = _v(data, "pb_ratio")
    ev  = _v(data, "ev_ebitda")
    de  = _v(data, "debt_equity")
    pos = data.get("earnings_positive", False)
    fcf = data.get("fcf_positive", False)

    # Hard filter: earnings positivi
    if c["require_positive_earnings"] and not pos:
        return False, 0.0, ["❌ Utile netto negativo"]

    # Hard filter: FCF positivo
    if c["require_positive_fcf"] and not fcf:
        return False, 0.0, ["❌ Free Cash Flow negativo"]

    # P/E
    if pe is not None:
        if pe <= 0:
            return False, 0.0, ["❌ P/E negativo (perdita)"]
        if pe < c["pe_ratio_max"]:
            score += (c["pe_ratio_max"] - pe) / c["pe_ratio_max"]
            passed_checks += 1
            notes.append(f"✅ P/E {_fmt(pe)} < {c['pe_ratio_max']}")
        else:
            notes.append(f"⚠️ P/E {_fmt(pe)} > {c['pe_ratio_max']}")
    else:
        notes.append("ℹ️ P/E non disponibile")

    # P/B
    if pb is not None:
        if pb < c["pb_ratio_max"]:
            score += (c["pb_ratio_max"] - pb) / c["pb_ratio_max"]
            passed_checks += 1
            notes.append(f"✅ P/B {_fmt(pb)} < {c['pb_ratio_max']}")
        else:
            notes.append(f"⚠️ P/B {_fmt(pb)} > {c['pb_ratio_max']}")
    else:
        notes.append("ℹ️ P/B non disponibile")

    # EV/EBITDA
    if ev is not None and ev > 0:
        if ev < c["ev_ebitda_max"]:
            score += (c["ev_ebitda_max"] - ev) / c["ev_ebitda_max"]
            passed_checks += 1
            notes.append(f"✅ EV/EBITDA {_fmt(ev)} < {c['ev_ebitda_max']}")
        else:
            notes.append(f"⚠️ EV/EBITDA {_fmt(ev)} > {c['ev_ebitda_max']}")

    # Debt/Equity
    if de is not None:
        if de < c["debt_equity_max"]:
            score += (c["debt_equity_max"] - de) / c["debt_equity_max"]
            passed_checks += 1
            notes.append(f"✅ D/E {_fmt(de)} < {c['debt_equity_max']}")
        else:
            return False, 0.0, [f"❌ D/E {_fmt(de)} troppo elevato (>{c['debt_equity_max']})"]

    # Deve passare almeno 3 criteri su 4 (P/E, P/B, EV/EBITDA, D/E)
    if passed_checks < 3:
        return False, 0.0, [f"❌ Solo {passed_checks}/4 criteri value soddisfatti"]

    # Bonus dividendo (info, non filtro)
    div = _v(data, "dividend_yield")
    if div and div > 0:
        score += 0.1
        notes.append(f"ℹ️ Dividendo: {_pct(div)}")

    return True, round(score, 3), notes


# ── GROWTH SCREENER ───────────────────────────────────────────────────────────

def screen_growth(data: dict) -> tuple[bool, float, list[str]]:
    """
    Criteri:
      - Crescita ricavi YoY > 15% (ultimi 2 anni)
      - EPS growth > 10% se profittevole, oppure ricavi > 25% se in perdita
      - Gross margin > 40%
      - Debt/Equity < 2
    """
    c     = config.GROWTH_CRITERIA
    notes = []
    score = 0.0

    rg1 = _v(data, "revenue_growth_1y")
    rg2 = _v(data, "revenue_growth_2y")
    eg  = _v(data, "eps_growth_1y")
    gm  = _v(data, "gross_margin")
    de  = _v(data, "debt_equity")
    pos = data.get("earnings_positive", False)

    # Crescita ricavi: 1 anno
    if rg1 is None:
        return False, 0.0, ["❌ Dati crescita ricavi non disponibili"]

    if rg1 < c["revenue_growth_min"]:
        # Tollera perdita se crescita molto alta
        if not (c["allow_loss_if_high_growth"] and rg1 >= c["revenue_growth_high"] and not pos):
            return False, 0.0, [f"❌ Crescita ricavi {_pct(rg1)} < {_pct(c['revenue_growth_min'])}"]

    score += min(rg1 / 0.5, 1.0)   # normalizzato su 50% come massimo
    notes.append(f"✅ Crescita ricavi 1Y: {_pct(rg1)}")

    # Crescita ricavi: 2 anni (bonus consistenza)
    if rg2 is not None and rg2 >= c["revenue_growth_min"]:
        score += 0.2
        notes.append(f"✅ Crescita ricavi 2Y: {_pct(rg2)} — consistente")
    elif rg2 is not None:
        notes.append(f"ℹ️ Crescita ricavi 2Y: {_pct(rg2)}")

    # EPS growth
    if pos:
        if eg is not None and eg >= c["eps_growth_min"]:
            score += 0.3
            notes.append(f"✅ EPS growth: {_pct(eg)}")
        elif eg is not None:
            notes.append(f"⚠️ EPS growth: {_pct(eg)} < {_pct(c['eps_growth_min'])}")
    else:
        if rg1 >= c["revenue_growth_high"]:
            notes.append(f"ℹ️ In perdita ma ricavi +{_pct(rg1)} — accettato come growth")
        else:
            return False, 0.0, [f"❌ In perdita e crescita ricavi insufficiente ({_pct(rg1)})"]

    # Gross margin
    if gm is not None:
        if gm < c["gross_margin_min"]:
            return False, 0.0, [f"❌ Gross margin {_pct(gm)} < {_pct(c['gross_margin_min'])}"]
        score += min(gm / 0.8, 0.5)
        notes.append(f"✅ Gross margin: {_pct(gm)}")
    else:
        notes.append("ℹ️ Gross margin non disponibile")

    # Debt/Equity
    if de is not None:
        if de > c["debt_equity_max"]:
            return False, 0.0, [f"❌ D/E {_fmt(de)} > {c['debt_equity_max']}"]
        notes.append(f"✅ D/E: {_fmt(de)}")

    return True, round(score, 3), notes


# ── QUALITY SCREENER ──────────────────────────────────────────────────────────

def screen_quality(data: dict) -> tuple[bool, float, list[str]]:
    """
    Criteri:
      - ROE > 15%
      - ROIC > 12%
      - Operating margin > 15%
      - Debt/Equity < 0.8
      - Utile positivo
      - Crescita ricavi positiva almeno 3 anni su 5
    """
    c     = config.QUALITY_CRITERIA
    notes = []
    score = 0.0

    roe  = _v(data, "roe")
    roic = _v(data, "roic")
    om   = _v(data, "operating_margin")
    de   = _v(data, "debt_equity")
    pos  = data.get("earnings_positive", False)
    yg   = data.get("years_positive_growth", 0)

    # Hard: utile positivo
    if c["require_positive_earnings"] and not pos:
        return False, 0.0, ["❌ Utile netto negativo"]

    # ROE
    if roe is None:
        return False, 0.0, ["❌ ROE non disponibile"]
    if roe < c["roe_min"]:
        return False, 0.0, [f"❌ ROE {_pct(roe)} < {_pct(c['roe_min'])}"]
    score += min(roe / 0.4, 1.0)
    notes.append(f"✅ ROE: {_pct(roe)}")

    # ROIC
    if roic is not None:
        if roic < c["roic_min"]:
            return False, 0.0, [f"❌ ROIC {_pct(roic)} < {_pct(c['roic_min'])}"]
        score += min(roic / 0.3, 0.8)
        notes.append(f"✅ ROIC: {_pct(roic)}")
    else:
        notes.append("ℹ️ ROIC non disponibile")

    # Operating margin
    if om is not None:
        if om < c["operating_margin_min"]:
            return False, 0.0, [f"❌ Op. margin {_pct(om)} < {_pct(c['operating_margin_min'])}"]
        score += min(om / 0.4, 0.8)
        notes.append(f"✅ Operating margin: {_pct(om)}")
    else:
        notes.append("ℹ️ Operating margin non disponibile")

    # Debt/Equity
    if de is not None:
        if de > c["debt_equity_max"]:
            return False, 0.0, [f"❌ D/E {_fmt(de)} > {c['debt_equity_max']}"]
        score += (c["debt_equity_max"] - de) / c["debt_equity_max"] * 0.5
        notes.append(f"✅ D/E: {_fmt(de)}")

    # Anni crescita ricavi
    if yg < c["min_years_revenue_growth"]:
        return False, 0.0, [f"❌ Crescita ricavi positiva solo {yg}/5 anni (min {c['min_years_revenue_growth']})"]
    score += yg / 5 * 0.5
    notes.append(f"✅ Crescita ricavi positiva {yg}/5 anni")

    # Dividendo (info aggiuntiva)
    div = _v(data, "dividend_yield")
    if div and div > 0:
        notes.append(f"ℹ️ Dividendo: {_pct(div)}")

    return True, round(score, 3), notes


# ── ETF SCREENER (condiviso) ──────────────────────────────────────────────────

def screen_etf(data: dict, region: str = "eu") -> tuple[bool, float, list[str]]:
    """
    Filtri base per ETF indipendenti dalla strategia:
      - AUM minimo (diverso per EU e US)
      - Expense ratio < 0.5% (ETF attivi esclusi se troppo costosi)
    """
    notes = []
    score = 0.0

    aum = data.get("total_assets", 0) or 0
    ter = data.get("expense_ratio")
    r1y = data.get("return_1y")

    min_aum = (config.ETF_MIN_AUM_EUR if region == "eu"
               else config.ETF_MIN_AUM_USD)

    if aum < min_aum:
        return False, 0.0, [f"❌ AUM {aum/1e6:.0f}M < minimo {min_aum/1e6:.0f}M"]

    score += min(aum / (min_aum * 10), 1.0)
    notes.append(f"✅ AUM: {aum/1e6:.0f}M")

    if ter is not None:
        if ter > 0.005:   # 0.5%
            notes.append(f"⚠️ TER elevato: {ter*100:.2f}%")
        else:
            score += (0.005 - ter) / 0.005 * 0.5
            notes.append(f"✅ TER: {ter*100:.2f}%")

    if r1y is not None:
        notes.append(f"ℹ️ Rendimento 1Y: {r1y*100:.1f}%")
        if r1y > 0:
            score += 0.2

    return True, round(score, 3), notes
