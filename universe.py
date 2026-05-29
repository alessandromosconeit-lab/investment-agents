"""
Definizione dell'universo di asset.
- USA: S&P 500 + Russell 1000 hardcoded (in data_fetcher.py)
- Europa: financedatabase — recupera dinamicamente tutti i titoli
  per paese e exchange, filtrati per market cap > 1B USD
- ETF: liste curate hardcoded
"""

import logging
logger = logging.getLogger(__name__)


# ── Configurazione exchange per FMP screener ETF ─────────────────────────────

UNIVERSE_CONFIG = {
    "stocks": {
        "europe": {
            "source": "financedatabase",
            "countries": ["Italy", "Germany", "France", "Netherlands",
                          "Belgium", "Spain", "Switzerland", "Sweden",
                          "Denmark", "Finland", "Norway"],
        },
        "us": {
            "source": "hardcoded",  # gestito in data_fetcher.py
        },
    },
    "etf": {
        "europe": {
            "source": "hardcoded",
            "exchanges": ["EURONEXT", "XETRA"],
        },
        "us": {
            "source": "hardcoded",
            "exchanges": ["NYSE ARCA", "NASDAQ"],
        },
    },
}


def get_financedatabase_tickers(countries: list[str] | None = None,
                                 exchanges: list[str] | None = None) -> list[str]:
    """
    Recupera i ticker europei da financedatabase.
    Filtra per paese e/o exchange.
    Restituisce una lista di ticker in formato Yahoo Finance.
    """
    try:
        import financedatabase as fd

        equities = fd.Equities()

        all_tickers = []

        if countries:
            for country in countries:
                try:
                    result = equities.select(country=country)
                    if result is not None and not result.empty:
                        tickers = result.index.tolist()
                        # Filtra ticker validi (no spazi, lunghezza ragionevole)
                        tickers = [t for t in tickers
                                   if isinstance(t, str)
                                   and len(t) <= 15
                                   and " " not in t
                                   and t != ""]
                        all_tickers += tickers
                        logger.info(f"  financedatabase {country}: {len(tickers)} ticker")
                except Exception as e:
                    logger.warning(f"  financedatabase error [{country}]: {e}")

        elif exchanges:
            for exchange in exchanges:
                try:
                    result = equities.select(exchange=exchange)
                    if result is not None and not result.empty:
                        tickers = result.index.tolist()
                        tickers = [t for t in tickers
                                   if isinstance(t, str)
                                   and len(t) <= 15
                                   and " " not in t]
                        all_tickers += tickers
                        logger.info(f"  financedatabase {exchange}: {len(tickers)} ticker")
                except Exception as e:
                    logger.warning(f"  financedatabase error [{exchange}]: {e}")

        unique = list(dict.fromkeys(all_tickers))
        logger.info(f"  Totale financedatabase: {len(unique)} ticker unici")
        return unique

    except ImportError:
        logger.warning("financedatabase non installato — uso lista hardcoded europea")
        return _get_european_hardcoded()
    except Exception as e:
        logger.warning(f"financedatabase errore generale: {e} — uso lista hardcoded")
        return _get_european_hardcoded()


def _get_european_hardcoded() -> list[str]:
    """Fallback hardcoded se financedatabase non è disponibile."""
    FTSE_MIB = [
        "A2A.MI","ATL.MI","AZM.MI","BAMI.MI","CPR.MI","ENEL.MI","ENI.MI",
        "EXO.MI","G.MI","HER.MI","ISP.MI","LDO.MI","MB.MI","MONC.MI",
        "NEXI.MI","RACE.MI","SRG.MI","STM.MI","TEN.MI","TIT.MI","UCG.MI",
        "UNI.MI","PRY.MI","AMP.MI","BZU.MI","FCA.MI","PST.MI","REC.MI",
        "SPM.MI","TRN.MI","US.MI","WDB.MI",
    ]
    FTSE_STAR = [
        "ACEA.MI","ERG.MI","FILA.MI","GVS.MI","IGD.MI","LES.MI","LUVE.MI",
        "MCE.MI","OVS.MI","PIR.MI","TFI.MI","UNI.MI","IEN.MI","EMAK.MI",
    ]
    DAX = [
        "ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BEI.DE","BMW.DE",
        "CON.DE","DHL.DE","DTE.DE","EOAN.DE","FRE.DE","HEI.DE","HEN3.DE",
        "IFX.DE","MBG.DE","MRK.DE","MUV2.DE","RWE.DE","SAP.DE","SHL.DE",
        "SIE.DE","VOW3.DE","VNA.DE","ZAL.DE","DBK.DE","DB1.DE","BNR.DE",
        "MTX.DE","P911.DE",
    ]
    MDAX = [
        "AIXA.DE","BOSS.DE","EVT.DE","GBF.DE","HAB.DE","HMB.DE","HOT.DE",
        "KGX.DE","LEI.DE","PSM.DE","QIA.DE","RHM.DE","RTL.DE","SDF.DE",
        "SFQ.DE","SMHN.DE","TEG.DE","TKA.DE","TUI1.DE","VBK.DE","VIB3.DE",
    ]
    CAC40 = [
        "AC.PA","ACA.PA","AI.PA","AIR.PA","ALO.PA","ATO.PA","BN.PA","BNP.PA",
        "CA.PA","CAP.PA","CS.PA","DG.PA","DSY.PA","ENGI.PA","EL.PA","GLE.PA",
        "HO.PA","KER.PA","LR.PA","MC.PA","ML.PA","MT.AS","ORA.PA","PUB.PA",
        "RI.PA","RMS.PA","RNO.PA","SAF.PA","SAN.PA","SGO.PA","SU.PA","TTE.PA",
        "URW.PA","VIE.PA","VIV.PA","WLN.PA",
    ]
    EURO_STOXX = [
        "ASML.AS","PHIA.AS","NN.AS","WKL.AS","ABN.AS","RAND.AS","HEIA.AS",
        "INGA.AS","ADYEN.AS","WDP.BR","SOLB.BR","GBLB.BR","KBC.BR","UCB.BR",
        "FER.MC","ITX.MC","SAN.MC","BBVA.MC","TEF.MC","REP.MC","IBE.MC",
        "NOVN.SW","NESN.SW","ROG.SW","ABBN.SW","CSGN.SW","ZURN.SW",
        "VOLV-B.ST","ERIC-B.ST","SEB-A.ST","SWED-A.ST","NDA-SE.ST",
    ]
    return list(dict.fromkeys(
        FTSE_MIB + FTSE_STAR + DAX + MDAX + CAC40 + EURO_STOXX
    ))
