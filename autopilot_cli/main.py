#!/usr/bin/env python3
"""Autopilot CLI - Query Congressional trades and hedge fund 13F filings."""

import json
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from autopilot_cli.sources.capitol_trades import (
    fetch_politician_trades,
    fetch_trades_by_ticker,
    list_politicians,
)
from autopilot_cli.sources.sec_edgar import fetch_13f_filings, list_hedge_fund_managers

app = typer.Typer(
    name="autopilot",
    help="Query Congressional trades and hedge fund 13F filings",
    no_args_is_help=True,
)
console = Console()


@app.command("politician")
def politician_command(
    name: Optional[str] = typer.Argument(None, help="Politician name or slug (e.g., 'pelosi', 'tuberville')"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all trackable politicians"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    page_size: int = typer.Option(20, "--limit", help="Number of trades to fetch"),
):
    """
    Query Congressional trades for a specific politician or list all politicians.
    """
    if list_all:
        politicians = list_politicians()

        if json_output:
            data = [p.model_dump() for p in politicians]
            typer.echo(json.dumps(data, indent=2, default=str))
            return

        table = Table(title="Trackable Politicians")
        table.add_column("Name", style="cyan")
        table.add_column("Slug", style="yellow")
        table.add_column("Party", style="magenta")
        table.add_column("Chamber", style="green")

        for p in politicians:
            table.add_row(
                p.name,
                p.slug,
                p.party or "N/A",
                p.chamber or "N/A",
            )

        console.print(table)
        return

    if not name:
        console.print("[red]Error:[/red] Provide a politician name or use --list to see all politicians")
        raise typer.Exit(1)

    # Convert common name formats to slugs
    slug = name.lower().replace(" ", "-")

    try:
        trades = fetch_politician_trades(slug, page_size=page_size)

        if not trades:
            console.print(f"[yellow]No trades found for {name}[/yellow]")
            return

        if json_output:
            data = [t.model_dump() for t in trades]
            typer.echo(json.dumps(data, indent=2, default=str))
            return

        table = Table(title=f"Recent Trades - {name.title()}")
        table.add_column("Date", style="cyan")
        table.add_column("Ticker", style="yellow")
        table.add_column("Asset", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Amount", style="green")
        table.add_column("Party", style="blue")

        for trade in trades:
            trade_type_color = "green" if trade.trade_type == "Purchase" else "red"
            table.add_row(
                str(trade.transaction_date) if trade.transaction_date else "N/A",
                trade.ticker or "N/A",
                trade.asset_description[:40] if trade.asset_description else "N/A",
                f"[{trade_type_color}]{trade.trade_type}[/{trade_type_color}]",
                trade.amount,
                trade.party or "N/A",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(trades)} trades[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("trades")
def trades_command(
    ticker: str = typer.Option(..., "--ticker", "-t", help="Stock ticker symbol (e.g., NVDA, AAPL)"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    page_size: int = typer.Option(20, "--limit", help="Number of trades to fetch"),
):
    """
    Query Congressional trades for a specific stock ticker.
    """
    try:
        trades = fetch_trades_by_ticker(ticker, page_size=page_size)

        if not trades:
            console.print(f"[yellow]No trades found for ticker {ticker}[/yellow]")
            return

        if json_output:
            data = [t.model_dump() for t in trades]
            typer.echo(json.dumps(data, indent=2, default=str))
            return

        table = Table(title=f"Congressional Trades - {ticker.upper()}")
        table.add_column("Politician", style="cyan")
        table.add_column("Date", style="yellow")
        table.add_column("Type", style="magenta")
        table.add_column("Amount", style="green")
        table.add_column("Party", style="blue")
        table.add_column("Chamber", style="white")

        for trade in trades:
            trade_type_color = "green" if trade.trade_type == "Purchase" else "red"
            table.add_row(
                trade.politician,
                str(trade.transaction_date) if trade.transaction_date else "N/A",
                f"[{trade_type_color}]{trade.trade_type}[/{trade_type_color}]",
                trade.amount,
                trade.party or "N/A",
                trade.chamber or "N/A",
            )

        console.print(table)
        console.print(f"\n[dim]Showing {len(trades)} trades[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("pilot")
def pilot_command(
    name: Optional[str] = typer.Argument(None, help="Hedge fund manager (e.g., 'burry', 'buffett', 'ackman')"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all trackable hedge fund managers"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
    top: int = typer.Option(10, "--top", "-n", help="Number of top positions to show"),
):
    """
    Query 13F filings for hedge fund managers.
    """
    if list_all:
        managers = list_hedge_fund_managers()

        if json_output:
            data = [m.model_dump() for m in managers]
            typer.echo(json.dumps(data, indent=2, default=str))
            return

        table = Table(title="Trackable Hedge Fund Managers")
        table.add_column("Name", style="cyan")
        table.add_column("CIK", style="yellow")

        for m in managers:
            table.add_row(m.name, m.cik)

        console.print(table)
        return

    if not name:
        console.print("[red]Error:[/red] Provide a manager name or use --list to see all managers")
        raise typer.Exit(1)

    try:
        filing = fetch_13f_filings(name)

        if json_output:
            data = filing.model_dump()
            typer.echo(json.dumps(data, indent=2, default=str))
            return

        console.print(f"\n[bold cyan]{filing.filer_name}[/bold cyan]")
        console.print(f"Filing Date: {filing.filing_date}")
        console.print(f"Period: {filing.period_of_report}")
        console.print(f"Total Positions: {len(filing.positions)}\n")

        if filing.positions:
            # Sort by value descending
            sorted_positions = sorted(filing.positions, key=lambda p: p.value, reverse=True)

            table = Table(title=f"Top {min(top, len(sorted_positions))} Positions by Value")
            table.add_column("#", style="dim", justify="right")
            table.add_column("Company", style="cyan")
            table.add_column("CUSIP", style="yellow")
            table.add_column("Shares", style="white", justify="right")
            table.add_column("Value", style="green", justify="right")

            for i, pos in enumerate(sorted_positions[:top], 1):
                table.add_row(
                    str(i),
                    pos.name_of_issuer[:50],
                    pos.cusip,
                    f"{pos.shares:,}",
                    f"${pos.value:,}",
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
