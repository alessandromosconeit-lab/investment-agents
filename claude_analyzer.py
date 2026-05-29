"""
Modulo di analisi AI — usa Claude per:
  1. Analizzare i candidati selezionati dallo screener
  2. Produrre il testo del report in italiano
"""

import json
import logging
import httpx
import anthropic

_http_client = httpx.Client(verify=False)
from datetime import date

import config

logger   = logging.getLogger(__name__)
_client  = None   # lazy init


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, http_client=_http_client)
    return _client


# ── Prompt per ogni agente ────────────────────────────────────────────────────

AGENT_PERSONAS = {
    "value": {
        "name":        "🔵 Value Agent",
        "strategy":    "value investing",
        "focus":       ("aziende sottovalutate rispetto ai fondamentali, con "
                        "P/E basso, bilancio solido, free cash flow positivo "
                        "e un gap significativo tra prezzo di mercato e fair value"),
        "risk":        "basso",
        "horizon":     "12-24 mesi",
        "extra_asset": "obbligazioni",
    },
    "growth": {
        "name":        "🟢 Growth Agent",
        "strategy":    "growth investing",
        "focus":       ("aziende con crescita di ricavi ed EPS superiore alla media, "
                        "margini lordi elevati e forte pricing power"),
        "risk":        "alto",
        "horizon":     "6-18 mesi",
        "extra_asset": None,
    },
    "quality": {
        "name":        "🟡 Quality Agent",
        "strategy":    "quality/GARP investing",
        "focus":       ("aziende strutturalmente superiori alla media — ROE e ROIC elevati, "
                        "margini stabili, bilancio conservativo — a un prezzo ragionevole"),
        "risk":        "medio",
        "horizon":     "12-36 mesi",
        "extra_asset": None,
    },
}


def _build_prompt(agent_type: str, candidates: list[dict],
                  etf_candidates: list[dict],
                  bond_candidates: list[dict] | None,
                  convergence: list[str]) -> str:
    """Costruisce il prompt da inviare a Claude."""

    p = AGENT_PERSONAS[agent_type]
    today = date.today().strftime("%d %B %Y")

    candidates_json = json.dumps(candidates[:10], ensure_ascii=False, indent=2)
    etf_json          = json.dumps(etf_candidates[:10], ensure_ascii=False, indent=2)
    bond_json         = json.dumps(bond_candidates[:10], ensure_ascii=False, indent=2) if bond_candidates else "[]"
    convergence_str   = ", ".join(convergence) if convergence else "nessuno"

    max_stocks = config.MAX_TOP_PICKS_STOCKS
    max_etf    = config.MAX_TOP_PICKS_ETF
    max_bonds  = config.MAX_TOP_PICKS_BONDS
    max_watch  = config.MAX_WATCHLIST

    return f"""Sei {p['name']}, un agente di analisi finanziaria specializzato in {p['strategy']}.

Data odierna: {today}
Orizzonte temporale tipico: {p['horizon']}
Profilo di rischio: {p['risk']}
Focus: {p['focus']}

---

Hai ricevuto i seguenti candidati che hanno superato lo screening quantitativo fondamentale.
Il tuo compito è produrre un report di analisi professionale in italiano.

CANDIDATI AZIONI (ordinati per score):
{candidates_json}

CANDIDATI ETF:
{etf_json}

{"CANDIDATI OBBLIGAZIONI:" if bond_candidates else ""}
{bond_json if bond_candidates else ""}

ASSET IN CONVERGENZA (presenti anche negli altri report questa settimana):
{convergence_str}

---

Produci un report strutturato ESATTAMENTE con questo formato:

═══════════════════════════════════════════════════
{p['name'].upper()} | {today}
═══════════════════════════════════════════════════

📊 EXECUTIVE SUMMARY
[3-4 righe: sintesi del contesto macro attuale e dei principali temi che guidano le proposte di questa settimana]
Candidati analizzati: [N azioni + N ETF{"+ N bond" if bond_candidates else ""}] → Proposte finali: [N]

───────────────────────────────────────────────────
📈 TOP PICKS — AZIONI (max {max_stocks})
───────────────────────────────────────────────────

Per ogni azione selezionata usa questo formato esatto:

[N]. [TICKER] — [Nome Azienda]
     Settore: [settore] | Mercato: [exchange] | Paese: [paese]
     Prezzo: [valuta][prezzo] | Market Cap: [cap in B]
     
     Metriche chiave:
     • P/E: [valore] | P/B: [valore] | EV/EBITDA: [valore]
     • ROE: [valore] | Margine op.: [valore] | D/E: [valore]
     • Crescita ricavi 1Y: [valore] | Dividendo: [valore o N/A]
     
     Analisi: [3-4 righe di analisi qualitativa — perché questa azienda è
     interessante dal punto di vista {p['strategy']}, quali sono i driver
     di valore, il posizionamento competitivo]
     
     ⚠️ Rischi principali: [1-2 rischi specifici e concreti]
     
     Giudizio: [FORTE INTERESSE ⭐⭐⭐ / INTERESSANTE ⭐⭐ / DA MONITORARE ⭐]

───────────────────────────────────────────────────
🧩 TOP PICKS — ETF (max {max_etf})
───────────────────────────────────────────────────

[N]. [TICKER] — [Nome ETF]
     Categoria: [categoria] | Exchange: [exchange]
     AUM: [AUM] | TER: [TER] | Rendimento 1Y: [rend]
     
     Analisi: [2-3 righe — esposizione, efficienza costi, adeguatezza
     alla strategia {p['strategy']}]
     ⚠️ Rischi: [1 rischio principale]

{"" if not bond_candidates else f'''───────────────────────────────────────────────────
💰 TOP PICKS — OBBLIGAZIONI (max {max_bonds})
───────────────────────────────────────────────────

[N]. [Emittente] — [Scadenza]
     Rating: [rating] | YTM: [yield] | Duration: [dur]
     
     Analisi: [2-3 righe]
     ⚠️ Rischi: [1 rischio principale]'''}

───────────────────────────────────────────────────
👁 WATCHLIST — Da monitorare (max {max_watch})
───────────────────────────────────────────────────

[Elenca i candidati quasi qualificati con una riga di spiegazione ciascuno
— perché sono quasi pronti e cosa manca per promuoverli a top pick]

{"" if not convergence else f'''───────────────────────────────────────────────────
⭐ CONVERGENZA INTER-AGENTE
───────────────────────────────────────────────────

I seguenti asset appaiono anche nei report degli altri agenti questa settimana,
segnale di interesse multiplo:
{convergence_str}
[1-2 righe di commento sul perché questa convergenza è significativa]'''}

───────────────────────────────────────────────────

Regole:
- Scrivi in italiano professionale ma leggibile
- Sii specifico: usa i dati forniti, non genericità
- I giudizi devono essere motivati dai numeri
- Segnala sempre i rischi — non fare solo promozione
- Non inventare dati non presenti nel JSON fornito
"""


# ── Funzione principale ───────────────────────────────────────────────────────

def generate_report(agent_type: str,
                    stock_candidates: list[dict],
                    etf_candidates:   list[dict],
                    bond_candidates:  list[dict] | None = None,
                    convergence:      list[str]  = []) -> str:
    """
    Chiama Claude e restituisce il testo del report.

    Args:
        agent_type:       "value" | "growth" | "quality"
        stock_candidates: lista di dict con dati fondamentali (già screened)
        etf_candidates:   lista di dict ETF (già screened)
        bond_candidates:  lista di dict bond (solo per value agent)
        convergence:      ticker presenti anche negli altri report
    Returns:
        Testo del report formattato
    """
    client = _get_client()
    prompt = _build_prompt(agent_type, stock_candidates,
                           etf_candidates, bond_candidates, convergence)

    logger.info(f"Chiamata Claude per {agent_type} agent — "
                f"{len(stock_candidates)} azioni, {len(etf_candidates)} ETF")

    try:
        message = client.messages.create(
            model      = config.CLAUDE_MODEL,
            max_tokens = config.CLAUDE_MAX_TOKENS,
            messages   = [{"role": "user", "content": prompt}],
        )
        report_text = message.content[0].text
        logger.info(f"Report {agent_type} generato — "
                    f"{len(report_text)} caratteri")
        return report_text

    except Exception as e:
        logger.error(f"Errore Claude [{agent_type}]: {e}")
        raise
