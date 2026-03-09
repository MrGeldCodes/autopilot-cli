"""Capitol Trades data fetcher."""

import re
import time
import asyncio
from datetime import datetime, date
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from autopilot_cli.models import CongressionalTrade, Politician

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


def _get_with_retry(url: str, headers: dict, retries: int = 3, timeout: float = 30.0):
    """HTTP GET with basic retry on transient errors."""
    last_err = None
    for attempt in range(retries):
        try:
            response = httpx.get(url, headers=headers, follow_redirects=True, timeout=timeout)
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
    raise last_err


def _resolve_bioguide_id(slug: str) -> Optional[str]:
    """Resolve a politician slug (e.g. 'nancy-pelosi') to a bioguide ID (e.g. 'P000197').
    
    Scrapes the Capitol Trades politicians listing and matches by slug.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    slug_lower = slug.lower().strip()
    
    for page_num in range(1, 20):
        try:
            response = _get_with_retry(
                f"https://www.capitoltrades.com/politicians?page={page_num}&pageSize=100",
                headers,
            )
        except Exception:
            break
        
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", href=re.compile(r"/politicians/[A-Z]"))
        
        if not links:
            break
        
        for link in links:
            href = link.get("href", "")
            bioguide = href.split("/")[-1]
            text = link.get_text(strip=True)
            # Extract name (everything before party)
            m = re.match(r"^(.+?)(Democrat|Republican|Independent)", text)
            name = m.group(1).strip() if m else text[:60].strip()
            candidate_slug = _name_to_slug(name)
            if candidate_slug == slug_lower:
                return bioguide
        
        if len(links) < 100:
            break
    
    return None


# Common slug -> bioguide cache for fast lookup
_BIOGUIDE_CACHE: dict[str, str] = {
    "nancy-pelosi": "P000197",
    "tommy-tuberville": "T000278",
    "dan-crenshaw": "C001120",
    "marjorie-taylor-greene": "G000596",
    "ro-khanna": "K000389",
    "michael-mccaul": "M001157",
    "josh-gottheimer": "G000583",
    "mark-green": "G000590",
    "austin-scott": "S001189",
    "pat-fallon": "F000246",
    "kevin-hern": "H001082",
    "john-boozman": "B001236",
    # Short name aliases for better UX
    "pelosi": "P000197",
    "tuberville": "T000278",
    "crenshaw": "C001120",
    "greene": "G000596",
    "khanna": "K000389",
    "mccaul": "M001157",
    "gottheimer": "G000583",
    "boozman": "B001236",
    "fallon": "F000246",
    "hern": "H001082",
}


def _slug_to_bioguide(slug: str) -> Optional[str]:
    """Convert slug to bioguide ID, using cache then dynamic lookup."""
    slug_lower = slug.lower().strip()
    if slug_lower in _BIOGUIDE_CACHE:
        return _BIOGUIDE_CACHE[slug_lower]
    
    bioguide = _resolve_bioguide_id(slug_lower)
    if bioguide:
        _BIOGUIDE_CACHE[slug_lower] = bioguide
    return bioguide


async def _block_non_essential_resources(page) -> None:
    """Block images, fonts, CSS, and media to speed up page loads.

    Capitol Trades data is pure JS-rendered JSON — we only need
    scripts and XHR/fetch. Everything else is wasted bandwidth.
    """
    await page.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in {"image", "stylesheet", "font", "media"}
        else route.continue_(),
    )


async def _extract_rows(page) -> list[dict]:
    """Extract table rows from a loaded Capitol Trades page."""
    return await page.evaluate('''() => {
        const rows = document.querySelectorAll('tbody tr');
        return Array.from(rows).map(tr => ({
            cells: Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
        }));
    }''')


def _parse_rows_to_trades(rows_data: list[dict], fallback_name: str) -> list[CongressionalTrade]:
    """Parse raw table row data into CongressionalTrade objects.

    Shared by both the politician and ticker fetch paths.
    """
    trades = []
    for row_data in rows_data:
        cells = row_data["cells"]
        if len(cells) < 7 or "No results" in cells[0]:
            continue

        politician_text = cells[0]
        politician_name = politician_text.split("\n")[0].strip()

        party = None
        chamber = None
        if "Republican" in politician_text:
            party = "Republican"
        elif "Democrat" in politician_text:
            party = "Democrat"
        if "Senate" in politician_text:
            chamber = "Senate"
        elif "House" in politician_text:
            chamber = "House"

        asset_text = cells[1]
        asset_description = asset_text.split("\n")[0].strip()
        ticker_match = re.search(r"([A-Z]{1,5}):US", asset_text)
        ticker = ticker_match.group(1) if ticker_match else None

        disc_date_str = cells[2].replace("\n", " ").strip()
        disclosure_date = parse_date(disc_date_str)

        trans_date_str = cells[3].replace("\n", " ").strip()
        transaction_date = parse_date(trans_date_str)

        trade_type_text = cells[6].lower().strip()
        trade_type = (
            "Purchase" if trade_type_text == "buy"
            else "Sale" if trade_type_text == "sell"
            else trade_type_text.capitalize()
        )

        amount = cells[7] if len(cells) > 7 else ""

        trades.append(CongressionalTrade(
            politician=politician_name or fallback_name,
            transaction_date=transaction_date,
            disclosure_date=disclosure_date,
            ticker=ticker,
            asset_description=asset_description,
            trade_type=trade_type,
            amount=amount,
            party=party,
            chamber=chamber,
        ))
    return trades


async def _fetch_politician_with_browser(
    browser, politician_slug: str, page_size: int = 20
) -> list[CongressionalTrade]:
    """Fetch one politician's trades using an *existing* browser instance.

    Each call opens a new page on the shared browser and closes it when done.
    This avoids the 1-2s browser startup cost on every request.
    """
    bioguide = _slug_to_bioguide(politician_slug)
    if not bioguide:
        return []

    page = await browser.new_page()
    await _block_non_essential_resources(page)

    url = f"https://www.capitoltrades.com/trades?politician={bioguide}&pageSize={page_size}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            await page.wait_for_selector("tbody tr", timeout=10000)
        except Exception:
            pass
        rows_data = await _extract_rows(page)
        return _parse_rows_to_trades(rows_data, politician_slug.replace("-", " ").title())
    finally:
        await page.close()


async def _fetch_many_politicians_playwright(
    politician_slugs: list[str], page_size: int = 20
) -> dict[str, list[CongressionalTrade]]:
    """Fetch multiple politicians concurrently using a single browser.

    Spins up one Chromium instance, opens N pages in parallel, closes browser
    when all are done. This is the fastest possible approach when fetching
    more than one politician in a single session.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            tasks = [
                _fetch_politician_with_browser(browser, slug, page_size)
                for slug in politician_slugs
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return {
                slug: (result if not isinstance(result, Exception) else [])
                for slug, result in zip(politician_slugs, results)
            }
        finally:
            await browser.close()


async def _fetch_politician_trades_playwright(politician_slug: str, page_size: int = 20) -> list[CongressionalTrade]:
    """Single-politician fetch. Uses its own browser (for standalone calls)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            return await _fetch_politician_with_browser(browser, politician_slug, page_size)
        finally:
            await browser.close()


def fetch_politician_trades(politician_slug: str, page_size: int = 20) -> list[CongressionalTrade]:
    """
    Fetch recent trades for a specific politician from Capitol Trades.

    Args:
        politician_slug: URL-friendly name (e.g., 'nancy-pelosi', 'tommy-tuberville')
        page_size: Number of trades to fetch

    Returns:
        List of CongressionalTrade objects
    """
    # Try Playwright first (handles client-side rendering)
    if PLAYWRIGHT_AVAILABLE:
        try:
            return asyncio.run(_fetch_politician_trades_playwright(politician_slug, page_size))
        except Exception as e:
            print(f"Warning: Playwright fetch failed, falling back to HTTP: {e}")
    
    # Fallback to HTTP-based approach
    bioguide = _slug_to_bioguide(politician_slug)
    if not bioguide:
        return []
    url = f"https://www.capitoltrades.com/trades?politician={bioguide}&pageSize={page_size}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = _get_with_retry(url, headers)

        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")

        trades = []

        # Find the trades table - Capitol Trades uses a table with class 'q-table'
        table = soup.find("table", class_="q-table")

        if not table:
            # Try alternative table selectors
            table = soup.find("table")

        if table:
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else []

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                # Column structure from Capitol Trades:
                # 0: Politician, 1: Asset/Ticker, 2: Disclosure Date, 3: Transaction Date,
                # 4: Days, 5: Owner, 6: Type, 7: Amount, 8: Price

                # Politician
                politician_name = cells[0].get_text(strip=True)

                # Extract party and chamber from politician cell
                politician_text = cells[0].get_text()
                party = None
                chamber = None
                if "Republican" in politician_text:
                    party = "Republican"
                elif "Democrat" in politician_text:
                    party = "Democrat"
                if "Senate" in politician_text:
                    chamber = "Senate"
                elif "House" in politician_text:
                    chamber = "House"

                # Clean politician name (remove party/chamber info)
                politician_name = re.split(r'(Republican|Democrat|Senate|House)', politician_name)[0].strip()

                # Asset and ticker
                asset_text = cells[1].get_text(strip=True)
                asset_description = asset_text

                # Extract ticker (format is usually "Company NameTICKER:US")
                ticker_match = re.search(r'([A-Z]{1,5}):US', asset_text)
                ticker = ticker_match.group(1) if ticker_match else None

                # Disclosure date (column 2)
                disc_date_str = cells[2].get_text(strip=True)
                disclosure_date = parse_date(disc_date_str)

                # Transaction date (column 3)
                trans_date_str = cells[3].get_text(strip=True)
                transaction_date = parse_date(trans_date_str)

                # Trade type (column 6 - "buy" or "sell")
                trade_type_text = cells[6].get_text(strip=True).lower()
                trade_type = "Purchase" if trade_type_text == "buy" else "Sale" if trade_type_text == "sell" else trade_type_text.capitalize()

                # Amount (column 7)
                amount = cells[7].get_text(strip=True) if len(cells) > 7 else ""

                trade = CongressionalTrade(
                    politician=politician_name or politician_slug.replace("-", " ").title(),
                    transaction_date=transaction_date,
                    disclosure_date=disclosure_date,
                    ticker=ticker,
                    asset_description=asset_description,
                    trade_type=trade_type,
                    amount=amount,
                    party=party,
                    chamber=chamber,
                )

                trades.append(trade)

        return trades

    except Exception as e:
        raise Exception(f"Failed to fetch trades for {politician_slug}: {str(e)}")


def fetch_multiple_politicians(
    politician_slugs: list[str], page_size: int = 20
) -> dict[str, list[CongressionalTrade]]:
    """Fetch trades for multiple politicians in one shot — fastest production method.

    Spins up a single Chromium browser, opens all politician pages concurrently,
    and closes the browser when done. Compared to calling fetch_politician_trades()
    N times, this saves (N-1) * browser startup time (~1-2s each).

    Args:
        politician_slugs: List of URL-friendly names (e.g., ['nancy-pelosi', 'tuberville'])
        page_size: Number of trades per politician

    Returns:
        Dict mapping slug -> list of CongressionalTrade objects.
        Failed slugs return an empty list (no exception raised).

    Example:
        results = fetch_multiple_politicians(['nancy-pelosi', 'tommy-tuberville', 'dan-crenshaw'])
        pelosi_trades = results['nancy-pelosi']
    """
    if not politician_slugs:
        return {}
    if PLAYWRIGHT_AVAILABLE:
        try:
            return asyncio.run(_fetch_many_politicians_playwright(politician_slugs, page_size))
        except Exception as e:
            print(f"Warning: concurrent Playwright fetch failed, falling back to serial: {e}")
    # Fallback: serial single fetches
    return {slug: fetch_politician_trades(slug, page_size) for slug in politician_slugs}


async def _resolve_issuer_id(ticker: str) -> str | None:
    """
    Resolve a stock ticker to a Capitol Trades issuer ID by searching the issuers page.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA')
        
    Returns:
        Issuer ID string or None if not found
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await _block_non_essential_resources(page)
        try:
            url = f"https://www.capitoltrades.com/issuers?search={ticker.upper()}"
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector('a[href*="/issuers/"]', timeout=8000)
            except Exception:
                pass
            link = await page.query_selector('a[href*="/issuers/"]')
            if link:
                href = await link.get_attribute("href")
                if href:
                    return href.split("/")[-1]
            return None
        finally:
            await browser.close()


async def _fetch_trades_by_ticker_playwright(ticker: str, page_size: int = 20) -> list[CongressionalTrade]:
    """
    Fetch trades by ticker using Playwright for client-side rendering.
    
    First resolves the ticker to a Capitol Trades issuer ID, then fetches
    trades filtered by that issuer.
    
    Args:
        ticker: Stock ticker symbol
        page_size: Number of trades to fetch
        
    Returns:
        List of CongressionalTrade objects
    """
    # Resolve ticker to issuer ID first
    issuer_id = await _resolve_issuer_id(ticker)
    if not issuer_id:
        return []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await _block_non_essential_resources(page)
        
        url = f"https://www.capitoltrades.com/trades?issuer={issuer_id}&pageSize={page_size}"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_selector("tbody tr", timeout=10000)
            except Exception:
                pass
            rows_data = await _extract_rows(page)
            trades = _parse_rows_to_trades(rows_data, ticker.upper())
            # For ticker-filtered pages, fall back to the searched ticker when
            # the :US pattern didn't match (e.g. ETFs, unusual formats)
            for t in trades:
                if t.ticker is None:
                    t.ticker = ticker.upper()
            return trades
        finally:
            await browser.close()


def fetch_trades_by_ticker(ticker: str, page_size: int = 20) -> list[CongressionalTrade]:
    """
    Fetch recent Congressional trades for a specific ticker.

    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA', 'AAPL')
        page_size: Number of trades to fetch

    Returns:
        List of CongressionalTrade objects
    """
    # Try Playwright first (handles client-side rendering)
    if PLAYWRIGHT_AVAILABLE:
        try:
            return asyncio.run(_fetch_trades_by_ticker_playwright(ticker, page_size))
        except Exception as e:
            print(f"Warning: Playwright fetch failed, falling back to HTTP: {e}")
    
    # Fallback to HTTP-based approach (note: this likely won't work well since
    # Capitol Trades is a client-side rendered SPA, but we try anyway)
    # We can't resolve issuer ID without Playwright, so fall back to generic URL
    url = f"https://www.capitoltrades.com/trades?pageSize={page_size}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = _get_with_retry(url, headers)

        soup = BeautifulSoup(response.text, "lxml")

        trades = []

        table = soup.find("table", class_="q-table")
        if not table:
            table = soup.find("table")

        if table:
            rows = table.find("tbody").find_all("tr") if table.find("tbody") else []

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 7:
                    continue

                # Same column structure as fetch_politician_trades
                politician_text = cells[0].get_text()
                politician_name = cells[0].get_text(strip=True)

                # Extract party and chamber
                party = None
                chamber = None
                if "Republican" in politician_text:
                    party = "Republican"
                elif "Democrat" in politician_text:
                    party = "Democrat"
                if "Senate" in politician_text:
                    chamber = "Senate"
                elif "House" in politician_text:
                    chamber = "House"

                politician_name = re.split(r'(Republican|Democrat|Senate|House)', politician_name)[0].strip()

                # Asset
                asset_text = cells[1].get_text(strip=True)
                asset_description = asset_text

                ticker_match = re.search(r'([A-Z]{1,5}):US', asset_text)
                extracted_ticker = ticker_match.group(1) if ticker_match else ticker.upper()

                # Dates
                disc_date_str = cells[2].get_text(strip=True)
                disclosure_date = parse_date(disc_date_str)

                trans_date_str = cells[3].get_text(strip=True)
                transaction_date = parse_date(trans_date_str)

                # Type and amount
                trade_type_text = cells[6].get_text(strip=True).lower()
                trade_type = "Purchase" if trade_type_text == "buy" else "Sale" if trade_type_text == "sell" else trade_type_text.capitalize()

                amount = cells[7].get_text(strip=True) if len(cells) > 7 else ""

                trade = CongressionalTrade(
                    politician=politician_name,
                    transaction_date=transaction_date,
                    disclosure_date=disclosure_date,
                    ticker=extracted_ticker,
                    asset_description=asset_description,
                    trade_type=trade_type,
                    amount=amount,
                    party=party,
                    chamber=chamber,
                )

                trades.append(trade)

        return trades

    except Exception as e:
        raise Exception(f"Failed to fetch trades for ticker {ticker}: {str(e)}")


def _name_to_slug(name: str) -> str:
    """Convert a politician name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _fetch_politicians_dynamic() -> list[Politician]:
    """Fetch the full politician list from Capitol Trades (paginated).

    Queries senate and house chamber filters separately so each politician
    is tagged with the correct chamber.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    politicians: list[Politician] = []
    seen_ids: set[str] = set()

    for chamber_value, chamber_label in [("senate", "Senate"), ("house", "House")]:
        for page in range(1, 20):  # safety cap
            try:
                response = _get_with_retry(
                    f"https://www.capitoltrades.com/politicians?chamber={chamber_value}&page={page}&pageSize=100",
                    headers,
                )
            except Exception:
                break

            soup = BeautifulSoup(response.text, "lxml")
            links = soup.find_all("a", href=re.compile(r"/politicians/[A-Z]"))

            if not links:
                break

            for link in links:
                href = link.get("href", "")
                bioguide = href.split("/")[-1]
                if bioguide in seen_ids:
                    continue
                seen_ids.add(bioguide)

                text = link.get_text(strip=True)
                # Pattern: NamePartyState...
                m = re.match(
                    r"^(.+?)(Democrat|Republican|Independent)(.+?)(?:Trades?\d|$)", text
                )
                if m:
                    name = m.group(1).strip()
                    party = m.group(2).strip()
                else:
                    name = text[:60].strip()
                    party = None

                # Extract trade count if present
                tc = re.search(r"Trades?(\d+)", text)
                trade_count = int(tc.group(1)) if tc else 0

                slug = _name_to_slug(name)

                politicians.append(
                    Politician(
                        name=name,
                        slug=slug,
                        party=party,
                        chamber=chamber_label,
                        trade_count=trade_count,
                    )
                )

            if len(links) < 100:
                break

    return politicians


# Hardcoded fallback list (kept for resilience)
_FALLBACK_POLITICIANS = [
    Politician(name="Nancy Pelosi", slug="nancy-pelosi", party="Democrat", chamber="House"),
    Politician(name="Tommy Tuberville", slug="tommy-tuberville", party="Republican", chamber="Senate"),
    Politician(name="Dan Crenshaw", slug="dan-crenshaw", party="Republican", chamber="House"),
    Politician(name="Austin Scott", slug="austin-scott", party="Republican", chamber="House"),
    Politician(name="Josh Gottheimer", slug="josh-gottheimer", party="Democrat", chamber="House"),
    Politician(name="Marjorie Taylor Greene", slug="marjorie-taylor-greene", party="Republican", chamber="House"),
    Politician(name="Mark Green", slug="mark-green", party="Republican", chamber="House"),
    Politician(name="Brian Higgins", slug="brian-higgins", party="Democrat", chamber="House"),
    Politician(name="Garret Graves", slug="garret-graves", party="Republican", chamber="House"),
    Politician(name="John Boozman", slug="john-boozman", party="Republican", chamber="Senate"),
    Politician(name="Ro Khanna", slug="ro-khanna", party="Democrat", chamber="House"),
    Politician(name="Michael McCaul", slug="michael-mccaul", party="Republican", chamber="House"),
    Politician(name="Kevin Hern", slug="kevin-hern", party="Republican", chamber="House"),
    Politician(name="Debbie Wasserman Schultz", slug="debbie-wasserman-schultz", party="Democrat", chamber="House"),
    Politician(name="Pat Fallon", slug="pat-fallon", party="Republican", chamber="House"),
]


def list_politicians() -> list[Politician]:
    """
    Fetch list of politicians with trade tracking from Capitol Trades.

    Dynamically scrapes all politicians (~200+) from the Capitol Trades
    website. Falls back to a hardcoded list of 15 if the fetch fails.

    Returns:
        List of Politician objects
    """
    try:
        politicians = _fetch_politicians_dynamic()
        if politicians:
            return politicians
    except Exception:
        pass

    return list(_FALLBACK_POLITICIANS)


def parse_date(date_str: str) -> Optional[date]:
    """Parse date string to datetime object."""
    if not date_str:
        return None

    # Capitol Trades format: "6 Mar2026" or "27 Feb2026"
    # Extract using regex
    match = re.match(r'(\d+)\s*([A-Za-z]+)(\d{4})', date_str)
    if match:
        day = match.group(1)
        month = match.group(2)
        year = match.group(3)
        # Reconstruct as "6 Mar 2026"
        reformatted = f"{day} {month} {year}"

        try:
            return datetime.strptime(reformatted, "%d %b %Y").date()
        except ValueError:
            pass

    # Try common date formats
    formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None
