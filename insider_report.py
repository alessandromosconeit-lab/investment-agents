"""
Script principale per il report insider.
Eseguibile standalone: python insider_report.py [--dry-run]
"""

import argparse
import logging
import sys
from datetime import date

import config
from insider_agent    import run_insider_agent
from data_fetcher     import get_us_stock_universe, get_european_stock_universe
from claude_analyzer  import _get_client
from email_sender     import send_report

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger("insider_report")


def _fmt_value(val, currency="USD") -> str:
    if val is None: return "N/A"
    symbol = "$" if currency == "USD" else "€"
    if abs(val) >= 1_000_000:
        return f"{symbol}{abs(val)/1_000_000:.1f}M"
    return f"{symbol}{abs(val)/1_000:.0f}K"


def generate_insider_report(transactions: list[dict]) -> str:
    """Genera il report insider tramite Claude."""

    buys  = [t for t in transactions if t["transaction_code"] == "P"][:20]
    sells = [t for t in transactions if t["transaction_code"] == "S"][:20]
    today = date.today().strftime("%d %B %Y")

    import json
    buys_json  = json.dumps(buys,  ensure_ascii=False, indent=2, default=str)
    sells_json = json.dumps(sells, ensure_ascii=False, indent=2, default=str)

    prompt = f"""Sei un analista finanziario specializzato nel monitoraggio delle
operazioni degli insider aziendali (Form 4 SEC per USA, dati regolatori per Europa).

Data: {today}
Filtro applicato: solo operazioni con valore > $100.000 / €100.000
Periodo monitorato: ultimi 14 giorni

Hai ricevuto i seguenti dati sulle transazioni degli insider.

ACQUISTI (insider che comprano azioni della propria azienda):
{buys_json}

VENDITE (insider che vendono azioni della propria azienda):
{sells_json}

Produci un report strutturato in italiano con questo formato esatto:

═══════════════════════════════════════════════════
🔍 INSIDER REPORT | {today}
═══════════════════════════════════════════════════

📊 EXECUTIVE SUMMARY
[3-4 righe: sintesi delle operazioni più significative del periodo,
temi ricorrenti (es. settori con più acquisti, cluster di vendite)]

Totale operazioni monitorate: [N acquisti + N vendite]
Valore totale acquisti: [somma]
Valore totale vendite: [somma]

───────────────────────────────────────────────────
🟢 ACQUISTI SIGNIFICATIVI (insider che comprano)
───────────────────────────────────────────────────

Per ogni acquisto rilevante usa questo formato:

[N]. [TICKER] — [Nome Azienda]
     Insider: [Nome] — [Ruolo]
     Data: [data] | Azioni: [N] | Prezzo: [prezzo] | Valore: [totale]
     
     Interpretazione: [2-3 righe — perché questo acquisto è significativo,
     contesto aziendale, cosa segnala sulla visione del management]
     ⚡ Segnale: [FORTE ⭐⭐⭐ / MODERATO ⭐⭐ / DA MONITORARE ⭐]

───────────────────────────────────────────────────
🔴 VENDITE SIGNIFICATIVE (insider che vendono)
───────────────────────────────────────────────────

[Stesso formato degli acquisti]

     Interpretazione: [considera che le vendite possono avere molte ragioni
     — diversificazione, necessità personali, piano 10b5-1 — sii equilibrato]
     ⚡ Segnale: [ATTENZIONE ⚠️ / NEUTRO ➖ / TECNICO (piano 10b5-1) 🔧]

───────────────────────────────────────────────────
📈 CLUSTER & PATTERN
───────────────────────────────────────────────────

[Identifica pattern interessanti:
- Settori con concentrazione di acquisti/vendite
- Aziende con operazioni multiple di insider diversi
- Timing rispetto a eventi aziendali noti]

───────────────────────────────────────────────────
⚠️ DISCLAIMER
───────────────────────────────────────────────────
Le operazioni degli insider sono informazioni pubbliche obbligatoriamente
dichiarate. Non costituiscono indicazioni di attività illegale.
Le vendite insider hanno spesso motivazioni personali non legate
alle prospettive aziendali. Questo report è a scopo informativo.
═══════════════════════════════════════════════════

Regole:
- Scrivi in italiano professionale
- Sii specifico sui valori in dollari/euro
- Per le vendite, mantieni un tono equilibrato
- Evidenzia gli acquisti di CEO/CFO/COO come più significativi
- Se i dati sono scarsi, dillo chiaramente
"""

    client = _get_client()
    message = client.messages.create(
        model      = config.CLAUDE_MODEL,
        max_tokens = config.CLAUDE_MAX_TOKENS,
        messages   = [{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def main(dry_run: bool = False):
    logger.info(f"\n🔍 Insider Agent — {date.today()}")

    if not config.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY non configurata.")
        sys.exit(1)

    # Recupera universo
    logger.info("Recupero universo...")
    us_tickers = get_us_stock_universe()
    eu_tickers = get_european_stock_universe()

    # Esegui agent
    transactions = run_insider_agent(us_tickers, eu_tickers)

    if not transactions:
        logger.warning("Nessuna transazione trovata sopra soglia.")
        return

    # Genera report
    logger.info("Generazione report con Claude...")
    report_text = generate_insider_report(transactions)

    if dry_run:
        logger.info(f"\n[DRY RUN] Report insider:\n{report_text[:800]}...\n")
    else:
        # Usa email_sender con tipo "insider"
        from email_sender import _build_html
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text      import MIMEText

        today   = date.today().strftime("%d %B %Y")
        subject = f"🔍 Insider Report — {today}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = config.GMAIL_USER
        msg["To"]      = config.RECIPIENT_EMAIL

        # Crea versione HTML con colore viola per insider
        html_body = f"""
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
    <tr><td align="center">
      <table width="680" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08)">
        <tr><td style="background:#7c3aed;padding:24px 32px;">
          <p style="margin:0;color:#ffffff;font-size:11px;text-transform:uppercase;letter-spacing:1px">
            Investment Agent System</p>
          <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700">
            🔍 Insider Report — {today}</h1>
        </td></tr>
        <tr><td style="padding:32px;color:#1a1a1a;font-size:14px;line-height:1.7">
          <div style="font-family:'Courier New',monospace;font-size:13px;
                      line-height:1.65;white-space:pre-wrap;word-break:break-word">
{report_text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")}
          </div>
        </td></tr>
        <tr><td style="background:#f8f8f8;padding:16px 32px;border-top:1px solid #e8e8e8">
          <p style="margin:0;color:#888;font-size:11px">
            Report generato automaticamente. Non costituisce consulenza finanziaria.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

        msg.attach(MIMEText(report_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body,   "html",  "utf-8"))

        try:
            import smtplib
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
                server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
                server.sendmail(config.GMAIL_USER, config.RECIPIENT_EMAIL,
                               msg.as_string())
            logger.info(f"✅ Insider Report inviato a {config.RECIPIENT_EMAIL}")
        except Exception as e:
            logger.error(f"❌ Errore invio email: {e}")

    logger.info("✅ Insider Agent completato")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
