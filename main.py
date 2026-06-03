"""
Orchestratore principale.
Esegue i tre agenti in sequenza, gestisce la convergenza e invia i report.

Esecuzione manuale:
    python main.py

    # Solo un agente specifico:
    python main.py --agent value
    python main.py --agent growth
    python main.py --agent quality

    # Dry run (genera report ma non invia email):
    python main.py --dry-run
"""

import argparse
import logging
import sys
from datetime import date

import config
from data_fetcher  import (get_us_stock_universe, get_european_stock_universe,
                            get_etf_tickers, build_stock_data, build_etf_data)
from screeners     import screen_value, screen_growth, screen_quality, screen_etf
from claude_analyzer import generate_report
from email_sender    import send_report
from data_exporter   import save_report_data

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Screening ─────────────────────────────────────────────────────────────────

def run_stock_screening(tickers: list[str],
                        screen_fn) -> list[dict]:
    """
    Applica fetch + screening su ogni ticker.
    Restituisce la lista dei candidati ordinata per score (desc).
    """
    candidates = []
    total = len(tickers)

    for i, ticker in enumerate(tickers, 1):
        if i % 50 == 0:
            logger.info(f"  Screening azioni: {i}/{total}...")

        data = build_stock_data(ticker)
        if not data:
            continue

        passed, score, notes = screen_fn(data)
        if passed:
            candidates.append({**data, "screen_score": score, "screen_notes": notes})

    candidates.sort(key=lambda x: x["screen_score"], reverse=True)
    logger.info(f"  → {len(candidates)} azioni qualificate su {total}")
    return candidates


def run_etf_screening(tickers: list[str],
                      region: str) -> list[dict]:
    """Applica fetch + screening su ogni ETF."""
    candidates = []
    for ticker in tickers:
        data = build_etf_data(ticker)
        if not data:
            continue
        passed, score, notes = screen_etf(data, region)
        if passed:
            candidates.append({**data, "screen_score": score, "screen_notes": notes})

    candidates.sort(key=lambda x: x["screen_score"], reverse=True)
    logger.info(f"  → {len(candidates)} ETF qualificati su {len(tickers)}")
    return candidates


# ── Agente singolo ────────────────────────────────────────────────────────────

def run_agent(agent_type: str,
              all_stock_candidates: dict,    # {ticker: data} già fetchati
              etf_eu_candidates:    list,
              etf_us_candidates:    list,
              convergence_tickers:  list[str],
              dry_run:              bool = False) -> list[str]:
    """
    Esegue un singolo agente:
    1. Screening degli stock pre-fetchati
    2. Generazione report via Claude
    3. Invio email

    Restituisce i ticker dei top picks (per calcolo convergenza).
    """
    logger.info(f"\n{'='*50}")
    logger.info(f"  Avvio {agent_type.upper()} AGENT")
    logger.info(f"{'='*50}")

    # Scegli la funzione di screening
    screen_fns = {
        "value":   screen_value,
        "growth":  screen_growth,
        "quality": screen_quality,
    }
    screen_fn = screen_fns[agent_type]

    # Screening azioni
    logger.info("  Screening azioni...")
    stock_candidates = []
    for ticker, data in all_stock_candidates.items():
        passed, score, notes = screen_fn(data)
        if passed:
            stock_candidates.append({**data, "screen_score": score, "screen_notes": notes})
    stock_candidates.sort(key=lambda x: x["screen_score"], reverse=True)
    logger.info(f"  → {len(stock_candidates)} azioni qualificate")

    # ETF (stessa lista per tutti gli agenti — filtro base per AUM/TER)
    etf_candidates = (etf_eu_candidates + etf_us_candidates)[:20]

    # Bond (solo per value agent — placeholder: da espandere con sorgente dedicata)
    bond_candidates = None
    if agent_type == "value":
        bond_candidates = []   # TODO: integrare FRED/MTS per bond data

    # Genera report
    logger.info("  Generazione report con Claude...")
    report_text = generate_report(
        agent_type      = agent_type,
        stock_candidates= stock_candidates[:30],   # top 30 allo screener, Claude seleziona
        etf_candidates  = etf_candidates,
        bond_candidates = bond_candidates,
        convergence     = convergence_tickers,
    )

    # Estrai i ticker dei top picks dal report (per convergenza negli altri agenti)
    top_pick_tickers = [c["ticker"] for c in stock_candidates[:config.MAX_TOP_PICKS_STOCKS]]

    # Output
    # Salva dati per la dashboard
    save_report_data(agent_type, stock_candidates[:5], etf_candidates[:3], report_text)

    if dry_run:
        logger.info(f"\n[DRY RUN] Report {agent_type}:\n{report_text[:500]}...\n")
    else:
        success = send_report(agent_type, report_text)
        if not success:
            logger.error(f"Invio email fallito per {agent_type}")

    return top_pick_tickers


# ── Main ──────────────────────────────────────────────────────────────────────

def main(agent_filter: str | None = None, dry_run: bool = False):
    logger.info(f"\n🚀 Investment Agent System — {date.today()}")
    logger.info(f"   Agenti: {agent_filter or 'tutti'} | Dry run: {dry_run}\n")

    # Controlla API keys
    if not config.FMP_API_KEY:
        logger.error("FMP_API_KEY non configurata. Imposta la variabile d'ambiente.")
        sys.exit(1)
    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY non configurata.")
        sys.exit(1)
    if not dry_run and not config.GMAIL_USER:
        logger.error("GMAIL_USER non configurata.")
        sys.exit(1)

    # ── 1. Recupero universo ─────────────────────────────────────────────────
    logger.info("📥 Recupero universo di asset...")

    logger.info("  Tickers USA (S&P 500 + Russell 1000)...")
    us_tickers = get_us_stock_universe()

    logger.info("  Tickers europei...")
    eu_tickers = get_european_stock_universe()

    all_tickers = list(dict.fromkeys(us_tickers + eu_tickers))
    logger.info(f"  Universo totale: {len(all_tickers)} azioni\n")

    # ── 2. Fetch dati fondamentali (una sola volta per tutti e tre gli agenti)
    logger.info("📊 Fetch dati fondamentali azioni...")
    all_stock_data = {}
    for i, ticker in enumerate(all_tickers, 1):
        if i % 100 == 0:
            logger.info(f"  Fetch: {i}/{len(all_tickers)}...")
        data = build_stock_data(ticker)
        if data:
            all_stock_data[ticker] = data
    logger.info(f"  → {len(all_stock_data)} azioni con dati validi\n")

    # ── 3. Fetch ETF ─────────────────────────────────────────────────────────
    logger.info("📦 Fetch e screening ETF...")
    etf_eu_tickers = get_etf_tickers("europe")
    etf_us_tickers = get_etf_tickers("us")

    etf_eu_candidates = run_etf_screening(etf_eu_tickers[:200], "eu")[:20]
    etf_us_candidates = run_etf_screening(etf_us_tickers[:200], "us")[:20]
    logger.info(f"  ETF EU qualificati: {len(etf_eu_candidates)}")
    logger.info(f"  ETF US qualificati: {len(etf_us_candidates)}\n")

    # ── 4. Esecuzione agenti ──────────────────────────────────────────────────
    agents_to_run = (["value", "growth", "quality"] if not agent_filter
                     else [agent_filter])

    top_picks_by_agent: dict[str, list[str]] = {}

    for agent_type in agents_to_run:
        # Calcola convergenza: ticker top picks degli agenti già eseguiti
        convergence = []
        for other_agent, picks in top_picks_by_agent.items():
            convergence += picks
        # Conta quante volte ogni ticker appare
        from collections import Counter
        conv_counts = Counter(convergence)
        convergence_tickers = [t for t, c in conv_counts.items() if c >= 1]

        top_picks = run_agent(
            agent_type           = agent_type,
            all_stock_candidates = all_stock_data,
            etf_eu_candidates    = etf_eu_candidates,
            etf_us_candidates    = etf_us_candidates,
            convergence_tickers  = convergence_tickers,
            dry_run              = dry_run,
        )
        top_picks_by_agent[agent_type] = top_picks

    logger.info(f"\n✅ Completato — {len(agents_to_run)} agenti eseguiti")

    # Riepilogo convergenza finale
    from collections import Counter
    all_picks = [t for picks in top_picks_by_agent.values() for t in picks]
    multi = [t for t, c in Counter(all_picks).items() if c >= 2]
    if multi:
        logger.info(f"⭐ Asset in convergenza (≥2 agenti): {', '.join(multi)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Investment Agent System")
    parser.add_argument(
        "--agent",
        choices=["value", "growth", "quality"],
        default=None,
        help="Esegui solo un agente specifico (default: tutti e tre)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Genera i report ma non inviare email"
    )
    args = parser.parse_args()
    main(agent_filter=args.agent, dry_run=args.dry_run)
