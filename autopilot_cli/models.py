"""Pydantic models for Congressional trades and 13F filings."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class CongressionalTrade(BaseModel):
    """A single Congressional stock trade disclosure."""

    politician: str
    transaction_date: Optional[date] = None
    disclosure_date: Optional[date] = None
    ticker: Optional[str] = None
    asset_description: str
    trade_type: str  # Purchase, Sale, Exchange
    amount: str  # Range like "$1,001 - $15,000"
    party: Optional[str] = None
    chamber: Optional[str] = None  # House or Senate

    class Config:
        json_schema_extra = {
            "example": {
                "politician": "Nancy Pelosi",
                "transaction_date": "2024-01-15",
                "disclosure_date": "2024-02-01",
                "ticker": "NVDA",
                "asset_description": "NVIDIA Corporation",
                "trade_type": "Purchase",
                "amount": "$50,001 - $100,000",
                "party": "Democrat",
                "chamber": "House"
            }
        }


class Position13F(BaseModel):
    """A single position from a 13F filing."""

    name_of_issuer: str
    title_of_class: str
    cusip: str
    value: int  # Market value in dollars
    shares: int  # Number of shares

    class Config:
        json_schema_extra = {
            "example": {
                "name_of_issuer": "NVIDIA CORP",
                "title_of_class": "COM",
                "cusip": "67066G104",
                "value": 15000000,
                "shares": 250000
            }
        }


class Filing13F(BaseModel):
    """A complete 13F filing."""

    filer_name: str
    filing_date: date
    period_of_report: date
    cik: str
    accession_number: str
    positions: list[Position13F] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "filer_name": "SCION ASSET MANAGEMENT LLC",
                "filing_date": "2024-02-14",
                "period_of_report": "2023-12-31",
                "cik": "0001649339",
                "accession_number": "0001649339-24-000001",
                "positions": []
            }
        }


class Politician(BaseModel):
    """A politician with trade tracking available."""

    name: str
    slug: str
    party: Optional[str] = None
    chamber: Optional[str] = None
    trade_count: int = 0


class HedgeFundManager(BaseModel):
    """A hedge fund manager with 13F filings."""

    name: str
    cik: str
    filing_count: int = 0
