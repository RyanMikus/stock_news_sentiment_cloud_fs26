from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


MIN_SALIENCE = 0.03
_ENTITY_TYPES_FOR_STOCKS = {"ORGANIZATION", "OTHER"}

_NAME_TO_TICKER: dict[str, str] = {
    # Tech
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "netflix": "NFLX",
    "intel": "INTC",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "qualcomm": "QCOM",
    "broadcom": "AVGO",
    "salesforce": "CRM",
    "oracle": "ORCL",
    "ibm": "IBM",
    "cisco": "CSCO",
    "adobe": "ADBE",
    "paypal": "PYPL",
    "spotify": "SPOT",
    "uber": "UBER",
    "lyft": "LYFT",
    "airbnb": "ABNB",
    "snap": "SNAP",
    "twitter": "X",
    "palantir": "PLTR",
    "shopify": "SHOP",
    "snowflake": "SNOW",
    "crowdstrike": "CRWD",
    "datadog": "DDOG",
    "arm": "ARM",
    "arm holdings": "ARM",
    "amd": "AMD",
    "asml": "ASML",
    # Finance
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "goldman sachs": "GS",
    "bank of america": "BAC",
    "wells fargo": "WFC",
    "morgan stanley": "MS",
    "citigroup": "C",
    "berkshire hathaway": "BRK-B",
    "blackrock": "BLK",
    "visa": "V",
    "mastercard": "MA",
    "american express": "AXP",
    # Healthcare
    "johnson & johnson": "JNJ",
    "johnson and johnson": "JNJ",
    "pfizer": "PFE",
    "moderna": "MRNA",
    "unitedhealth": "UNH",
    "abbvie": "ABBV",
    "eli lilly": "LLY",
    "merck": "MRK",
    "bristol-myers squibb": "BMY",
    # Consumer
    "walmart": "WMT",
    "target": "TGT",
    "home depot": "HD",
    "costco": "COST",
    "nike": "NKE",
    "coca-cola": "KO",
    "coca cola": "KO",
    "pepsi": "PEP",
    "pepsico": "PEP",
    "mcdonald's": "MCD",
    "mcdonalds": "MCD",
    "starbucks": "SBUX",
    "procter & gamble": "PG",
    "procter and gamble": "PG",
    # Energy
    "exxonmobil": "XOM",
    "exxon": "XOM",
    "chevron": "CVX",
    "shell": "SHEL",
    "bp": "BP",
    # Industrial / Other
    "boeing": "BA",
    "lockheed martin": "LMT",
    "general electric": "GE",
    "3m": "MMM",
    "at&t": "T",
    "verizon": "VZ",
    "disney": "DIS",
    "comcast": "CMCSA",
    "spacex": "SPCE",
    # Indices
    "s&p 500": "^GSPC",
    "s&p500": "^GSPC",
    "s&p": "^GSPC",
    "sp500": "^GSPC",
    "dow jones": "^DJI",
    "dow": "^DJI",
    "nasdaq": "^IXIC",
    "russell 2000": "^RUT",
    "vix": "^VIX",
}

TIME_WINDOWS: list[dict[str, str]] = [
    {"label": "1D",  "period": "1d",   "interval": "5m"},
    {"label": "5D",  "period": "5d",   "interval": "30m"},
    {"label": "1M",  "period": "1mo",  "interval": "1d"},
    {"label": "3M",  "period": "3mo",  "interval": "1d"},
    {"label": "6M",  "period": "6mo",  "interval": "1d"},
    {"label": "1Y",  "period": "1y",   "interval": "1wk"},
    {"label": "5Y",  "period": "5y",   "interval": "1wk"},
]

DEFAULT_WINDOW_LABEL = "1M"


def _resolve_ticker(name: str) -> str | None:
    normalized = name.strip().lower()

    if normalized in _NAME_TO_TICKER:
        return _NAME_TO_TICKER[normalized]

    # Direct ticker guess: all-caps alphabetic string, 1–5 chars
    stripped = name.strip()
    if stripped == stripped.upper() and stripped.isalpha() and 1 <= len(stripped) <= 5:
        return stripped

    return None


def collect_ranked_tickers(articles: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """
    Scan entity lists from analyzed articles, resolve to tickers, sum salience
    across all articles per ticker, and return sorted by total salience descending.
    """
    salience_by_ticker: dict[str, float] = {}

    for article in articles:
        if article.get("entity_extraction_status") != "success":
            continue

        for entity in article.get("entities") or []:
            if entity.get("type") not in _ENTITY_TYPES_FOR_STOCKS:
                continue

            salience = float(entity.get("salience") or 0.0)
            if salience < MIN_SALIENCE:
                continue

            ticker = _resolve_ticker(entity.get("name") or "")
            if ticker is None:
                continue

            salience_by_ticker[ticker] = salience_by_ticker.get(ticker, 0.0) + salience

    return sorted(salience_by_ticker.items(), key=lambda x: x[1], reverse=True)


_TICKER_TO_DISPLAY_NAME: dict[str, str] = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "INTC": "Intel",
    "AMD": "AMD",
    "QCOM": "Qualcomm",
    "AVGO": "Broadcom",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    "IBM": "IBM",
    "CSCO": "Cisco",
    "ADBE": "Adobe",
    "PYPL": "PayPal",
    "SPOT": "Spotify",
    "UBER": "Uber",
    "LYFT": "Lyft",
    "ABNB": "Airbnb",
    "SNAP": "Snap",
    "X": "X (Twitter)",
    "PLTR": "Palantir",
    "SHOP": "Shopify",
    "SNOW": "Snowflake",
    "CRWD": "CrowdStrike",
    "DDOG": "Datadog",
    "ARM": "Arm Holdings",
    "ASML": "ASML",
    "JPM": "JPMorgan Chase",
    "GS": "Goldman Sachs",
    "BAC": "Bank of America",
    "WFC": "Wells Fargo",
    "MS": "Morgan Stanley",
    "C": "Citigroup",
    "BRK-B": "Berkshire Hathaway",
    "BLK": "BlackRock",
    "V": "Visa",
    "MA": "Mastercard",
    "AXP": "American Express",
    "JNJ": "Johnson & Johnson",
    "PFE": "Pfizer",
    "MRNA": "Moderna",
    "UNH": "UnitedHealth",
    "ABBV": "AbbVie",
    "LLY": "Eli Lilly",
    "MRK": "Merck",
    "BMY": "Bristol-Myers Squibb",
    "WMT": "Walmart",
    "TGT": "Target",
    "HD": "Home Depot",
    "COST": "Costco",
    "NKE": "Nike",
    "KO": "Coca-Cola",
    "PEP": "PepsiCo",
    "MCD": "McDonald's",
    "SBUX": "Starbucks",
    "PG": "Procter & Gamble",
    "XOM": "ExxonMobil",
    "CVX": "Chevron",
    "SHEL": "Shell",
    "BP": "BP",
    "BA": "Boeing",
    "LMT": "Lockheed Martin",
    "GE": "General Electric",
    "MMM": "3M",
    "T": "AT&T",
    "VZ": "Verizon",
    "DIS": "Disney",
    "CMCSA": "Comcast",
    "SPCE": "Virgin Galactic",
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "NASDAQ",
    "^RUT": "Russell 2000",
    "^VIX": "VIX",
}


def get_ticker_display_name(ticker: str) -> str:
    return _TICKER_TO_DISPLAY_NAME.get(ticker, ticker)


def get_window_config(label: str) -> dict[str, str]:
    for w in TIME_WINDOWS:
        if w["label"] == label:
            return w
    return next(w for w in TIME_WINDOWS if w["label"] == DEFAULT_WINDOW_LABEL)


def fetch_stock_history(ticker: str, period: str, interval: str) -> pd.DataFrame | None:
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval)
        return df if not df.empty else None
    except Exception:
        return None


def validate_ticker(ticker: str) -> bool:
    """Return True if yfinance recognizes this as a valid tradeable ticker."""
    try:
        fi = yf.Ticker(ticker).fast_info
        return getattr(fi, "last_price", None) is not None
    except Exception:
        return False


def collect_ranked_tickers_with_resolver(
    articles: list[dict[str, Any]],
    resolver: dict[str, str],
) -> list[tuple[str, float]]:
    """
    Build ticker ranking from Gemini's resolver dict.
    All tickers from the resolver are always included. Entity salience is used for
    ordering where a name matches (exact case-insensitive or substring).
    """
    if not resolver:
        return []

    resolver_lower = {k.lower(): v for k, v in resolver.items()}
    salience_by_ticker: dict[str, float] = {t: 0.0 for t in resolver.values()}

    for article in articles:
        if article.get("entity_extraction_status") != "success":
            continue
        for entity in article.get("entities") or []:
            if entity.get("type") not in _ENTITY_TYPES_FOR_STOCKS:
                continue
            salience = float(entity.get("salience") or 0.0)
            if salience < MIN_SALIENCE:
                continue
            entity_lower = (entity.get("name") or "").strip().lower()

            ticker = resolver_lower.get(entity_lower)
            if ticker is None:
                for rname, rticker in resolver_lower.items():
                    if rname in entity_lower or entity_lower in rname:
                        ticker = rticker
                        break

            if ticker:
                salience_by_ticker[ticker] = salience_by_ticker.get(ticker, 0.0) + salience

    return sorted(salience_by_ticker.items(), key=lambda x: x[1], reverse=True)


def fetch_stock_info(ticker: str) -> dict:
    """Fetch key metrics via yfinance fast_info. Returns {} on failure."""
    try:
        fi = yf.Ticker(ticker).fast_info
        return {
            "market_cap": getattr(fi, "market_cap", None),
            "fifty_two_week_high": getattr(fi, "fifty_two_week_high", None),
            "fifty_two_week_low": getattr(fi, "fifty_two_week_low", None),
        }
    except Exception:
        return {}
