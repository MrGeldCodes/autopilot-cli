"""SEC EDGAR 13F filings fetcher."""

import re
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from autopilot_cli.models import Filing13F, Position13F, HedgeFundManager


# Known hedge fund managers for quick access
KNOWN_MANAGERS = {
    "burry": HedgeFundManager(name="SCION ASSET MANAGEMENT LLC", cik="0001649339"),
    "buffett": HedgeFundManager(name="BERKSHIRE HATHAWAY INC", cik="0001067983"),
    "ackman": HedgeFundManager(name="PERSHING SQUARE CAPITAL MANAGEMENT", cik="0001336528"),
    "dalio": HedgeFundManager(name="BRIDGEWATER ASSOCIATES LP", cik="0001350694"),
    "druckenmiller": HedgeFundManager(name="DUQUESNE FAMILY OFFICE LLC", cik="0001536411"),
}


def fetch_13f_filings(manager_slug: str) -> Optional[Filing13F]:
    """
    Fetch the latest 13F filing for a hedge fund manager.

    Args:
        manager_slug: Manager identifier (e.g., 'burry', 'buffett') or CIK number

    Returns:
        Filing13F object with positions
    """
    # Check if it's a known manager
    manager = KNOWN_MANAGERS.get(manager_slug.lower())

    if not manager:
        # Try to use it as a CIK directly
        if manager_slug.isdigit():
            cik = manager_slug.zfill(10)  # CIKs are 10 digits with leading zeros
            manager = HedgeFundManager(name="Unknown", cik=cik)
        else:
            raise ValueError(f"Unknown manager: {manager_slug}. Try 'burry', 'buffett', 'ackman', 'dalio', or provide a CIK number.")

    headers = {
        "User-Agent": "AutopilotCLI/0.1.0 educational@example.com",
        "Accept": "application/json",
    }

    try:
        # Use the SEC EDGAR data API to search for submissions
        submissions_url = f"https://data.sec.gov/submissions/CIK{manager.cik}.json"

        response = httpx.get(submissions_url, headers=headers, timeout=30.0)
        response.raise_for_status()

        data = response.json()

        # Extract company name
        filer_name = data.get("name", manager.name)

        # Find the most recent 13F-HR filing
        filings = data.get("filings", {}).get("recent", {})

        if not filings:
            raise Exception(f"No filings found for {manager.name}")

        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        report_dates = filings.get("reportDate", [])

        # Find the first 13F-HR
        filing_index = None
        for i, form in enumerate(forms):
            if form == "13F-HR":
                filing_index = i
                break

        if filing_index is None:
            raise Exception(f"No 13F-HR filings found for {manager.name}")

        accession_number = accession_numbers[filing_index]
        filing_date = datetime.strptime(filing_dates[filing_index], "%Y-%m-%d").date()
        period_of_report = datetime.strptime(report_dates[filing_index], "%Y-%m-%d").date()

        # Now fetch the filing details to get the information table XML
        cik_no_zeros = str(int(manager.cik))
        accession_no_dashes = accession_number.replace("-", "")

        # Try common XML filename patterns
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_no_dashes}"

        xml_filenames = [
            "form13fInfoTable.xml",
            "infotable.xml",
            "primary_doc.xml",
            "form13f_infotable.xml",
        ]

        xml_content = None

        for filename in xml_filenames:
            try:
                info_table_url = f"{base_url}/{filename}"
                xml_response = httpx.get(info_table_url, headers=headers, timeout=30.0)

                if xml_response.status_code == 200:
                    xml_content = xml_response.text
                    break
            except:
                continue

        if not xml_content:
            # Try the index page
            filing_index_url = f"{base_url}/{accession_number}-index.htm"

            headers_html = {
                "User-Agent": "AutopilotCLI/0.1.0 educational@example.com",
                "Accept": "text/html",
            }

            try:
                index_response = httpx.get(filing_index_url, headers=headers_html, timeout=30.0)
                index_soup = BeautifulSoup(index_response.text, "lxml")

                # Find XML file link
                for link in index_soup.find_all("a"):
                    href = link.get("href", "")

                    if ".xml" in href.lower() and ("info" in href.lower() or "13f" in href.lower()):
                        if href.startswith("/"):
                            info_table_url = f"https://www.sec.gov{href}"
                        else:
                            info_table_url = f"{base_url}/{href}"

                        xml_response = httpx.get(info_table_url, headers=headers, timeout=30.0)
                        xml_content = xml_response.text
                        break
            except:
                pass

        if not xml_content:
            raise Exception("Could not find information table XML")

        # Parse the XML
        xml_soup = BeautifulSoup(xml_content, "lxml-xml")

        positions = []

        # Find all <infoTable> entries
        info_tables = xml_soup.find_all("infoTable")

        for table in info_tables:
            name_of_issuer = table.find("nameOfIssuer")
            title_of_class = table.find("titleOfClass")
            cusip = table.find("cusip")
            value = table.find("value")
            shares = table.find("sshPrnamt")

            if name_of_issuer and cusip and value:
                position = Position13F(
                    name_of_issuer=name_of_issuer.get_text(strip=True),
                    title_of_class=title_of_class.get_text(strip=True) if title_of_class else "COM",
                    cusip=cusip.get_text(strip=True),
                    value=int(value.get_text(strip=True)) * 1000,  # Value is in thousands
                    shares=int(shares.get_text(strip=True)) if shares else 0,
                )

                positions.append(position)

        filing = Filing13F(
            filer_name=filer_name,
            filing_date=filing_date,
            period_of_report=period_of_report,
            cik=manager.cik,
            accession_number=accession_number,
            positions=positions,
        )

        return filing

    except Exception as e:
        raise Exception(f"Failed to fetch 13F for {manager_slug}: {str(e)}")


def list_hedge_fund_managers() -> list[HedgeFundManager]:
    """
    List known hedge fund managers with 13F filings.

    Returns:
        List of HedgeFundManager objects
    """
    return list(KNOWN_MANAGERS.values())
