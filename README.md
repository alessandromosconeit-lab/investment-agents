# 🤖 Investment Agent System

Sistema di analisi e screening fondamentale automatizzato.
Tre agenti AI (Value, Growth, Quality) che analizzano ~2.800 asset
e inviano un report bisettimanale via email.

---

## Agenti

| Agente | Strategia | Universo | Frequenza |
|--------|-----------|----------|-----------|
| 🔵 Value | P/E basso, FCF positivo, bilancio solido | Azioni + Bond | Lun + Gio |
| 🟢 Growth | Crescita ricavi >15%, margini elevati | Azioni + ETF | Lun + Gio |
| 🟡 Quality | ROE/ROIC alti, margini stabili, basso debito | Azioni + ETF | Lun + Gio |

---

## Universo

- **USA**: S&P 500 + Russell 1000
- **Italia**: FTSE MIB + FTSE Star
- **Germania**: DAX + MDAX
- **Francia**: CAC 40 + CAC Next 20
- **Europa**: Euro Stoxx 600
- **ETF europei**: AUM >100M EUR (Euronext, Xetra, LSE)
- **ETF americani**: AUM >500M USD (NYSE Arca, NASDAQ)
- **Filtro trasversale**: Market cap >1B USD su tutte le azioni

---

## Setup

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/investment-agents.git
cd investment-agents
```

### 2. Crea un virtualenv e installa le dipendenze

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
# oppure: venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. Configura le API keys

Copia `.env.example` in `.env` e compila i valori:

```bash
cp .env.example .env
```

Poi modifica `.env`:

```
FMP_API_KEY=...         # https://financialmodelingprep.com (piano Starter ~$29/mese)
ANTHROPIC_API_KEY=...   # https://console.anthropic.com
GMAIL_USER=...          # il tuo indirizzo Gmail
GMAIL_APP_PASSWORD=...  # App Password Gmail (vedi sotto)
```

#### Come creare una Gmail App Password

1. Vai su https://myaccount.google.com/security
2. Attiva la Verifica in due passaggi (se non già attiva)
3. Vai su https://myaccount.google.com/apppasswords
4. Crea una nuova App Password con nome "Investment Agents"
5. Copia la password di 16 caratteri nel file `.env`

### 4. Test locale (dry run)

```bash
# Carica le variabili dal file .env
export $(cat .env | xargs)

# Esegui tutti gli agenti senza inviare email
python main.py --dry-run

# Esegui solo un agente
python main.py --agent value --dry-run
python main.py --agent growth --dry-run
python main.py --agent quality --dry-run
```

### 5. Deploy su GitHub Actions (automazione bisettimanale)

1. Crea un repository privato su GitHub
2. Fai push del codice:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/tuo-username/investment-agents.git
   git push -u origin main
   ```

3. Aggiungi i Secrets su GitHub:
   - Vai su **Settings → Secrets and variables → Actions**
   - Aggiungi questi 4 secrets:
     - `FMP_API_KEY`
     - `ANTHROPIC_API_KEY`
     - `GMAIL_USER`
     - `GMAIL_APP_PASSWORD`

4. Il workflow si attiverà automaticamente ogni **lunedì e giovedì alle 07:00 CET**.
   Puoi anche avviarlo manualmente dalla tab **Actions → Run workflow**.

---

## Struttura del progetto

```
investment-agents/
├── main.py              ← Orchestratore principale
├── config.py            ← Configurazione e criteri di screening
├── universe.py          ← Definizione universo (ticker per indice)
├── data_fetcher.py      ← Fetch dati da FMP e yfinance
├── screeners.py         ← Logica di screening per ogni agente
├── claude_analyzer.py   ← Generazione report via Claude API
├── email_sender.py      ← Invio email via Gmail SMTP
├── requirements.txt
├── .env.example
└── .github/
    └── workflows/
        └── run_agents.yml  ← GitHub Actions scheduler
```

---

## Costi stimati

| Servizio | Piano | Costo |
|----------|-------|-------|
| Financial Modeling Prep | Starter | ~$29/mese |
| Anthropic Claude API | Pay-as-you-go | ~$5-15/mese |
| GitHub Actions | Free tier | Gratuito |
| Gmail SMTP | — | Gratuito |
| **Totale** | | **~$35-45/mese** |

---

## Personalizzazione

Per modificare i criteri di screening, edita `config.py`:

```python
VALUE_CRITERIA = {
    "pe_ratio_max": 15.0,    # abbassa per essere più selettivo
    "pb_ratio_max": 1.5,
    "ev_ebitda_max": 10.0,
    ...
}
```

Per aggiungere/rimuovere ticker dall'universo europeo, edita `universe.py`.

---

## Disclaimer

Questo sistema è a scopo **informativo**. Non costituisce consulenza
finanziaria. Le decisioni di investimento sono di esclusiva responsabilità
dell'utente. Verifica sempre i dati prima di prendere qualsiasi decisione.
