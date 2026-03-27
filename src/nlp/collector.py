"""
Text data collector for NLP sentiment analysis (Aula 4).

Collects news and regulatory texts for each ticker from:
  A) CVM — Fatos Relevantes / Comunicados ao Mercado (HTML scraping)
  B) Google News RSS — headlines and snippets in Portuguese

Outputs one JSON file per ticker in data/raw/texts_{ticker}.json.
Files are cached: if the JSON already exists it is not re-downloaded.
"""

import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from html import unescape
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# ── Universe with company names (for news search) ─────────────────────────
TICKER_NAMES = {
    "ITUB4":  "Itaú Unibanco",
    "BBDC4":  "Bradesco",
    "BBAS3":  "Banco do Brasil",
    "SANB11": "Santander Brasil",
    "ABCB4":  "Banco ABC Brasil",
    "EGIE3":  "Engie Brasil",
    "EQTL3":  "Equatorial Energia",
    "CPFE3":  "CPFL Energia",
    "TAEE11": "Taesa",
    "CMIG4":  "Cemig",
}

# CVM CNPJ mapping (digits only) for filtering CVM results
TICKER_CNPJ = {
    "ITUB4":  "60872504000123",
    "BBDC4":  "60746948000112",
    "BBAS3":  "00000000000191",
    "SANB11": "90400888000142",
    "ABCB4":  "28195667000106",
    "EGIE3":  "02474103000119",
    "EQTL3":  "03220438000173",
    "CPFE3":  "02429144000193",
    "TAEE11": "07859971000130",
    "CMIG4":  "17155730000164",
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.load_default_certs()

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _http_get(url: str, timeout: int = 20) -> str | None:
    """Fetch URL and return decoded text, or None on any error."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        resp = urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout)
        raw = resp.read()
        # Try utf-8 first, fall back to latin-1
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1")
    except Exception as e:
        print(f"[{datetime.now()}] WARNING: HTTP GET failed for {url[:100]}... — {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Source A — CVM Fatos Relevantes
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_cvm_texts(ticker: str, max_docs: int = 20) -> list[dict]:
    """
    Fetch Fatos Relevantes and Comunicados ao Mercado from CVM open data.

    Uses the CVM open-data CSV endpoint which is more reliable than scraping
    the ENET ASP.NET form.
    """
    docs = []
    cnpj = TICKER_CNPJ.get(ticker)
    if not cnpj:
        return docs

    # CVM publishes a CSV of relevant facts:
    # https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FATO_RELEVANTE/DADOS/
    # But these are large ZIPs. Instead, try the structured search API.
    # The ENET search is ASP.NET with ViewState — unreliable to scrape.
    # We'll use the CVM Dados Abertos RSS feed as an alternative.

    # Try CVM consulta externa (structured URL for IPE documents)
    for category in ["21", "22"]:  # 21=Fato Relevante, 22=Comunicado ao Mercado
        url = (
            f"https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx/ListarDocumentos"
        )
        # The CVM ENET API is SOAP/ViewState-based and very hard to call directly.
        # Instead, try the dados abertos search feed.
        search_url = (
            f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/"
        )
        # This approach won't easily yield individual docs.
        # Fall through to the alternative CVM approach below.

    # Alternative: search CVM via their consultation page with direct parameters
    try:
        search_url = (
            f"https://www.rad.cvm.gov.br/ENET/frmConsultaExternaCVM.aspx?"
            f"codigoCVM=&ESSION=&numProtocolo=&dataInicial=01/01/2023"
            f"&dataFinal=31/12/2024&razaoSocial=&cnpj={cnpj}"
            f"&tipoParticipante=1&categoriaDocumento=21"  # Fato Relevante
        )
        html = _http_get(search_url)
        if html:
            # Try to extract document links and titles from the response
            # Pattern: grdDocumentos rows with links
            title_pattern = re.compile(
                r'<td[^>]*>(\d{2}/\d{2}/\d{4})</td>.*?'
                r'<td[^>]*>(.*?)</td>',
                re.DOTALL
            )
            links = re.findall(
                r"OpenPopUpVer\('([^']+)'\)", html
            )
            dates = re.findall(
                r'(\d{2}/\d{2}/\d{4})', html
            )
            titles = re.findall(
                r'(?:Fato Relevante|Comunicado ao Mercado)[^<]*', html
            )

            for i, link in enumerate(links[:max_docs]):
                doc_url = f"https://www.rad.cvm.gov.br/ENET/{link}" if not link.startswith("http") else link
                doc_text = _http_get(doc_url)
                if doc_text:
                    # Strip HTML tags for plain text
                    clean = re.sub(r'<[^>]+>', ' ', doc_text)
                    clean = re.sub(r'\s+', ' ', clean).strip()[:2000]
                    date_str = dates[i] if i < len(dates) else ""
                    docs.append({
                        "ticker": ticker,
                        "source": "CVM",
                        "date": date_str,
                        "title": titles[i] if i < len(titles) else "Fato Relevante",
                        "text": clean,
                    })
    except Exception as e:
        print(f"[{datetime.now()}] WARNING: CVM scraping failed for {ticker} — {e}")

    return docs


# ═══════════════════════════════════════════════════════════════════════════
# Source B — Google News RSS
# ═══════════════════════════════════════════════════════════════════════════

def _clean_html(text: str) -> str:
    """Strip HTML tags and decode entities."""
    text = unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _fetch_google_news(ticker: str, max_items: int = 30) -> list[dict]:
    """
    Fetch news headlines from Google News RSS feed.

    Returns a list of dicts with date, title, snippet.
    """
    company = TICKER_NAMES.get(ticker, ticker)
    query = urllib.parse.quote(f"{ticker} {company}")
    url = (
        f"https://news.google.com/rss/search?"
        f"q={query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    )

    xml_text = _http_get(url)
    if not xml_text:
        return []

    docs = []
    try:
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")
        for item in items[:max_items]:
            title = item.findtext("title", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")

            # Parse RSS date: "Mon, 25 Mar 2024 12:00:00 GMT"
            date_str = ""
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(pub_date)
                    date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    date_str = pub_date

            clean_title = _clean_html(title)
            clean_desc = _clean_html(description)
            text = f"{clean_title}. {clean_desc}".strip()

            if text:
                docs.append({
                    "ticker": ticker,
                    "source": "GoogleNews",
                    "date": date_str,
                    "title": clean_title,
                    "text": text[:2000],
                })
    except ET.ParseError as e:
        print(f"[{datetime.now()}] WARNING: XML parse error for {ticker} Google News — {e}")

    return docs


# ═══════════════════════════════════════════════════════════════════════════
# Main collection pipeline
# ═══════════════════════════════════════════════════════════════════════════

def collect_texts(ticker: str, force: bool = False) -> list[dict]:
    """
    Collect texts for a single ticker from all sources.

    Results are cached to data/raw/texts_{ticker}.json.
    Set force=True to re-download even if cached.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / f"texts_{ticker}.json"

    if cache_path.exists() and not force:
        print(f"[{datetime.now()}] {ticker}: cached — loading {cache_path.name}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[{datetime.now()}] {ticker}: collecting texts ...")
    all_docs = []

    # Source A: CVM
    cvm_docs = _fetch_cvm_texts(ticker)
    print(f"[{datetime.now()}]   CVM: {len(cvm_docs)} documents")
    all_docs.extend(cvm_docs)

    # Source B: Google News
    news_docs = _fetch_google_news(ticker)
    print(f"[{datetime.now()}]   Google News: {len(news_docs)} articles")
    all_docs.extend(news_docs)

    if not all_docs:
        print(f"[{datetime.now()}] WARNING: No texts collected for {ticker}")

    # Cache
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_docs, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now()}]   Saved {cache_path.name} — {len(all_docs)} total docs")

    return all_docs


def collect_all(force: bool = False) -> dict[str, list[dict]]:
    """
    Collect texts for all tickers in the universe.

    Returns {ticker: [docs]}.
    """
    print(f"[{datetime.now()}] === Text Collection Start ===")
    result = {}
    for ticker in TICKER_NAMES:
        result[ticker] = collect_texts(ticker, force=force)
    print(f"[{datetime.now()}] === Text Collection Complete ===")
    return result


def run(force: bool = False):
    """Entry point."""
    return collect_all(force=force)


if __name__ == "__main__":
    run()
