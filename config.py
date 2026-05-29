"""
Configuration — legge le variabili d'ambiente.
In locale usa un file .env, su GitHub Actions usa i Secrets.
"""
import os

# ── API Keys ────────────────────────────────────────────────
FMP_API_KEY        = os.environ.get("FMP_API_KEY", "")           # Financial Modeling Prep
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")     # Claude API

# ── Email ───────────────────────────────────────────────────
GMAIL_USER         = os.environ.get("GMAIL_USER", "")            # es. tuoindirizzo@gmail.com
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")    # App Password Gmail (non la password normale)
RECIPIENT_EMAIL    = "alessandromoscone.it@gmail.com"

# ── Filtri universo ─────────────────────────────────────────
MIN_MARKET_CAP_USD = 1_000_000_000   # 1 miliardo USD — filtro trasversale su tutte le azioni
ETF_MIN_AUM_EUR    = 100_000_000     # 100M EUR — ETF europei
ETF_MIN_AUM_USD    = 500_000_000     # 500M USD — ETF americani

# ── Claude model ────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_MAX_TOKENS  = 8096

# ── Criteri di screening ─────────────────────────────────────

VALUE_CRITERIA = {
    "pe_ratio_max":          15.0,    # P/E assoluto max (si usa anche confronto settoriale)
    "pb_ratio_max":           1.5,    # Price/Book max
    "ev_ebitda_max":         10.0,    # EV/EBITDA max
    "debt_equity_max":        1.0,    # Debt/Equity max
    "require_positive_earnings": True,
    "require_positive_fcf":  True,    # FCF positivo almeno nell'ultimo anno
    "dividend_as_info":      True,    # Dividendo riportato ma non usato come filtro
}

GROWTH_CRITERIA = {
    "revenue_growth_min":    0.15,    # +15% YoY minimo
    "revenue_growth_high":   0.25,    # +25% → tollera perdita netta
    "eps_growth_min":        0.10,    # +10% EPS se profittevole
    "gross_margin_min":      0.40,    # 40% margine lordo minimo
    "debt_equity_max":        2.0,
    "allow_loss_if_high_growth": True,
}

QUALITY_CRITERIA = {
    "roe_min":               0.15,    # ROE > 15%
    "roic_min":              0.12,    # ROIC > 12%
    "operating_margin_min":  0.15,    # Margine operativo > 15%
    "debt_equity_max":        0.8,
    "require_positive_earnings": True,
    "min_years_revenue_growth":  3,   # Crescita positiva almeno 3 anni su 5
}

# ── Limiti report ────────────────────────────────────────────
MAX_TOP_PICKS_STOCKS = 5
MAX_TOP_PICKS_ETF    = 3
MAX_TOP_PICKS_BONDS  = 3   # Solo Value Agent
MAX_WATCHLIST        = 5
