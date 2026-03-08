# autopilot-cli

Ask Claude: "Which congressman bought NVDA this week?"

A Python CLI + MCP server that lets AI agents query Congressional trading disclosures and hedge fund 13F filings. No API keys required.

## Features

- **Congressional Trades**: Query stock trades by members of Congress from Capitol Trades
- **13F Filings**: Access hedge fund portfolio holdings from SEC EDGAR
- **Rich Terminal Output**: Beautiful tables powered by Rich
- **JSON Output**: Machine-readable format for AI agents
- **MCP Server**: Expose functionality as MCP tools for Claude Desktop and other AI agents

## Installation

```bash
git clone https://github.com/MrGeldCodes/autopilot-cli.git
cd autopilot-cli
pip install -e .
playwright install chromium
```

> **Note:** The `playwright install chromium` step downloads the browser used to fetch live Congressional trade data from Capitol Trades.

## Quick Start

### Query Congressional Trades

```bash
# List all trackable politicians
autopilot politician --list

# Get recent trades for a specific politician
autopilot politician pelosi
autopilot politician tommy-tuberville

# Find who in Congress traded a specific stock
autopilot trades --ticker NVDA
autopilot trades --ticker AAPL
```

### Query Hedge Fund 13F Filings

```bash
# List trackable hedge fund managers
autopilot pilot --list

# Get latest 13F positions for Michael Burry
autopilot pilot burry

# Other available managers
autopilot pilot buffett
autopilot pilot ackman
autopilot pilot dalio
autopilot pilot druckenmiller
```

### JSON Output for AI Agents

```bash
# Get JSON output for programmatic consumption
autopilot trades --ticker NVDA --json
autopilot pilot burry --json
```

## CLI Commands

### `autopilot politician [NAME]`

Query Congressional trades for a specific politician.

**Options:**
- `--list`, `-l`: List all trackable politicians
- `--json`, `-j`: Output as JSON
- `--limit N`: Number of trades to fetch (default: 20)

**Examples:**
```bash
autopilot politician nancy-pelosi
autopilot politician tuberville --limit 10
autopilot politician --list
```

### `autopilot trades --ticker TICKER`

Query Congressional trades for a specific stock ticker.

**Options:**
- `--ticker`, `-t`: Stock ticker symbol (required)
- `--json`, `-j`: Output as JSON
- `--limit N`: Number of trades to fetch (default: 20)

**Examples:**
```bash
autopilot trades --ticker NVDA
autopilot trades -t AAPL --limit 5
```

### `autopilot pilot [MANAGER]`

Query 13F filings for hedge fund managers.

**Options:**
- `--list`, `-l`: List all trackable managers
- `--json`, `-j`: Output as JSON
- `--top N`: Number of top positions to show (default: 10)

**Examples:**
```bash
autopilot pilot burry
autopilot pilot buffett --top 20
autopilot pilot --list
```

## MCP Server

Use autopilot-cli as an MCP server for Claude Desktop or other AI agents.

### Configuration

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "autopilot": {
      "command": "python3",
      "args": ["-m", "autopilot_cli.mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/autopilot-cli"
      }
    }
  }
}
```

### Available MCP Tools

1. **query_politician_trades**: Query Congressional trades for a politician
2. **query_trades_by_ticker**: Query Congressional trades by stock ticker
3. **list_politicians**: List all trackable politicians
4. **query_13f_filing**: Query latest 13F filing for a hedge fund manager
5. **list_hedge_fund_managers**: List all trackable hedge fund managers

### Example MCP Usage

Once configured, ask Claude:

- "Which congressman bought NVDA this week?"
- "What are Michael Burry's latest positions?"
- "Show me Nancy Pelosi's recent trades"
- "Who in Congress is trading Tesla?"

## Data Sources

### Capitol Trades
Fetches data by scraping https://www.capitoltrades.com. No API key required.

**Available Politicians:**
- Nancy Pelosi, Tommy Tuberville, Dan Crenshaw, Austin Scott
- Josh Gottheimer, Marjorie Taylor Greene, Mark Green, Brian Higgins
- Garret Graves, John Boozman, Ro Khanna, Michael McCaul
- Kevin Hern, Debbie Wasserman Schultz, Pat Fallon

### SEC EDGAR
Fetches 13F filings via the SEC EDGAR data API. No API key required.

**Available Managers:**
- Michael Burry (Scion Asset Management)
- Warren Buffett (Berkshire Hathaway)
- Bill Ackman (Pershing Square Capital Management)
- Ray Dalio (Bridgewater Associates)
- Stanley Druckenmiller (Duquesne Family Office)

## Project Structure

```
autopilot-cli/
├── autopilot_cli/
│   ├── __init__.py
│   ├── main.py              # Typer CLI entrypoint
│   ├── mcp_server.py        # MCP server implementation
│   ├── models.py            # Pydantic models
│   └── sources/
│       ├── capitol_trades.py   # Capitol Trades fetcher
│       └── sec_edgar.py        # SEC EDGAR 13F fetcher
├── pyproject.toml
└── README.md
```

## Requirements

- Python 3.9+
- typer
- httpx
- rich
- pydantic
- beautifulsoup4
- lxml

## License

MIT

## Disclaimer

This tool is for educational purposes only. Congressional trade data is public information. 13F filings are public SEC disclosures. Always verify information independently before making investment decisions.
