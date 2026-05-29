"""
Modulo di invio email via Gmail SMTP.
Usa una Gmail App Password (non la password dell'account).
Come configurarla: https://myaccount.google.com/apppasswords
"""

import smtplib
import logging
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText

import config

logger = logging.getLogger(__name__)

AGENT_SUBJECTS = {
    "value":   "🔵 Value Report",
    "growth":  "🟢 Growth Report",
    "quality": "🟡 Quality Report",
}

AGENT_COLORS = {
    "value":   "#1a56db",   # blu
    "growth":  "#057a55",   # verde
    "quality": "#c27803",   # giallo/oro
}


def _build_html(agent_type: str, report_text: str) -> str:
    """
    Avvolge il testo del report in un template HTML leggibile via email.
    Il testo usa caratteri ASCII (═ ─ •) che renderizzano bene in tutti i client.
    """
    today       = date.today().strftime("%d %B %Y")
    color       = AGENT_COLORS.get(agent_type, "#333")
    agent_label = AGENT_SUBJECTS.get(agent_type, "Investment Report")

    # Converte newline in <br> e preserva la formattazione monospace
    formatted = (report_text
                 .replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace("\n", "<br>"))

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{agent_label} — {today}</title>
</head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="680" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:{color};padding:24px 32px;">
              <p style="margin:0;color:#ffffff;font-size:11px;
                        text-transform:uppercase;letter-spacing:1px;">
                Investment Agent System
              </p>
              <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;font-weight:700;">
                {agent_label} &mdash; {today}
              </h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;color:#1a1a1a;font-size:14px;line-height:1.7;">
              <div style="font-family:'Courier New',Courier,monospace;
                          font-size:13px;line-height:1.65;
                          white-space:pre-wrap;word-break:break-word;">
                {formatted}
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8f8f8;padding:16px 32px;
                       border-top:1px solid #e8e8e8;">
              <p style="margin:0;color:#888;font-size:11px;line-height:1.5;">
                Questo report è generato automaticamente da un sistema AI a scopo
                informativo. Non costituisce consulenza finanziaria.
                Le decisioni di investimento rimangono di esclusiva responsabilità
                dell'utente.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def send_report(agent_type: str, report_text: str) -> bool:
    """
    Invia il report via Gmail SMTP.

    Args:
        agent_type:  "value" | "growth" | "quality"
        report_text: testo del report generato da Claude

    Returns:
        True se inviato con successo, False altrimenti
    """
    today   = date.today().strftime("%d %B %Y")
    subject = f"{AGENT_SUBJECTS.get(agent_type, 'Report')} — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.GMAIL_USER
    msg["To"]      = config.RECIPIENT_EMAIL

    # Versione plain text (fallback)
    part_text = MIMEText(report_text, "plain", "utf-8")

    # Versione HTML
    html_body = _build_html(agent_type, report_text)
    part_html = MIMEText(html_body, "html", "utf-8")

    msg.attach(part_text)
    msg.attach(part_html)   # HTML sovrascrive il plain nei client moderni

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_USER, config.RECIPIENT_EMAIL, msg.as_string())
        logger.info(f"✅ Email {agent_type} inviata a {config.RECIPIENT_EMAIL}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ Autenticazione Gmail fallita — controlla GMAIL_APP_PASSWORD")
        return False
    except Exception as e:
        logger.error(f"❌ Errore invio email [{agent_type}]: {e}")
        return False
