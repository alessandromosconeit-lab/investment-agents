"""
Modulo di export dati per la dashboard.
Salva i risultati di ogni run come JSON in data/reports/
per essere visualizzati sulla dashboard GitHub Pages.
"""

import json
import logging
import os
from datetime import date, datetime

logger = logging.getLogger(__name__)

DATA_DIR    = "data/reports"
LATEST_DIR  = "data/latest"


def _ensure_dirs():
    os.makedirs(DATA_DIR,   exist_ok=True)
    os.makedirs(LATEST_DIR, exist_ok=True)


def save_report_data(agent_type: str,
                     stock_candidates: list[dict],
                     etf_candidates:   list[dict],
                     report_text:      str):
    """
    Salva i dati del report come JSON.
    Crea due file:
      - data/reports/YYYY-MM-DD_{agent}.json  (storico)
      - data/latest/{agent}.json              (ultimo run)
    """
    _ensure_dirs()
    today = date.today().isoformat()
    now   = datetime.now().isoformat()

    # Prepara i top picks (max 5 azioni + 3 ETF)
    top_stocks = []
    for s in stock_candidates[:5]:
        top_stocks.append({
            "ticker":           s.get("ticker"),
            "name":             s.get("name"),
            "sector":           s.get("sector"),
            "country":          s.get("country"),
            "exchange":         s.get("exchange"),
            "price":            s.get("price"),
            "market_cap":       s.get("market_cap"),
            "pe_ratio":         s.get("pe_ratio"),
            "pb_ratio":         s.get("pb_ratio"),
            "ev_ebitda":        s.get("ev_ebitda"),
            "roe":              s.get("roe"),
            "roic":             s.get("roic"),
            "operating_margin": s.get("operating_margin"),
            "debt_equity":      s.get("debt_equity"),
            "revenue_growth_1y":s.get("revenue_growth_1y"),
            "dividend_yield":   s.get("dividend_yield"),
            "earnings_positive":s.get("earnings_positive"),
            "score":            s.get("screen_score"),
        })

    top_etf = []
    for e in etf_candidates[:3]:
        top_etf.append({
            "ticker":        e.get("ticker"),
            "name":          e.get("name"),
            "category":      e.get("category"),
            "total_assets":  e.get("total_assets"),
            "expense_ratio": e.get("expense_ratio"),
            "return_1y":     e.get("return_1y"),
            "score":         e.get("screen_score"),
        })

    payload = {
        "agent":       agent_type,
        "date":        today,
        "timestamp":   now,
        "stats": {
            "total_candidates": len(stock_candidates),
            "total_etf":        len(etf_candidates),
        },
        "top_stocks":  top_stocks,
        "top_etf":     top_etf,
        "report_text": report_text,
    }

    # Salva storico
    hist_path = f"{DATA_DIR}/{today}_{agent_type}.json"
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"  Dati salvati: {hist_path}")

    # Salva latest
    latest_path = f"{LATEST_DIR}/{agent_type}.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"  Latest aggiornato: {latest_path}")

    # Aggiorna indice dei report
    _update_index(agent_type, today, hist_path)


def _update_index(agent_type: str, date_str: str, path: str):
    """Aggiorna data/index.json con la lista di tutti i report disponibili."""
    index_path = "data/index.json"
    try:
        with open(index_path, "r") as f:
            index = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        index = {"reports": []}

    # Aggiungi entry se non esiste già
    entry = {"date": date_str, "agent": agent_type, "path": path}
    existing = [r for r in index["reports"]
                if r["date"] == date_str and r["agent"] == agent_type]
    if not existing:
        index["reports"].append(entry)

    # Ordina per data decrescente
    index["reports"].sort(key=lambda x: x["date"], reverse=True)
    index["updated"] = datetime.now().isoformat()

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
