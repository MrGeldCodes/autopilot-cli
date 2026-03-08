# autopilot-cli

**Congress trades stocks. You should know about it.**

The STOCK Act requires every member of Congress to disclose stock trades within 45 days. `autopilot-cli` surfaces those disclosures instantly — query by politician or ticker, pull hedge fund 13F filings, and pipe it all to AI agents via MCP. No API keys. No paywalls.

```bash
# Who in Congress bought NVDA recently?
autopilot trades --ticker NVDA

# What's Burry actually holding right now?
autopilot pilot burry

# Ask Claude directly (via MCP):
# "Which senators bought defense stocks before the Ukraine vote?"
```

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

> **Windows users:** Run commands in PowerShell or Command Prompt. If `autopilot` is not found after install, try `python -m autopilot_cli` or restart your terminal to refresh PATH.

## Quick Start

### Query Congressional Trades

```bash
# List all trackable politicians
autopilot politician --list

# Get recent trades for a specific politician
autopilot politician nancy-pelosi
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

## Sample Output

> Live data — results vary by trading activity.

### Congressional trades for NVDA

```
Congressional Trades - NVDA                          
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Politician         ┃ Date       ┃ Type     ┃ Amount  ┃ Party      ┃ Chamber ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ John Boozman       │ 2026-02-05 │ Purchase │ 1K–15K  │ Republican │ Senate  │
│ John Boozman       │ 2026-02-26 │ Purchase │ 1K–15K  │ Republican │ Senate  │
│ John Boozman       │ 2026-02-12 │ Purchase │ 1K–15K  │ Republican │ Senate  │
│ John Boozman       │ 2026-02-25 │ Purchase │ 1K–15K  │ Republican │ Senate  │
│ John Boozman       │ 2026-02-05 │ Purchase │ 1K–15K  │ Republican │ Senate  │
│ Sheldon Whitehouse │ 2026-02-22 │ Sale     │ 1K–15K  │ Democrat   │ Senate  │
└────────────────────┴────────────┴──────────┴─────────┴────────────┴─────────┘
Showing 6 trades
```

> **Note:** The STOCK Act requires Congress members to disclose trades within 45 days, but amounts are reported in ranges ($1K–$15K, $15K–$50K, etc.) — not exact figures. This is how the law works, not a data limitation.

### Politician list (with chamber)

```
                             Trackable Politicians                              
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name                      ┃ Slug                      ┃ Party      ┃ Chamber ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ John Boozman              │ john-boozman              │ Republican │ Senate  │
│ Shelley Moore Capito      │ shelley-moore-capito      │ Republican │ Senate  │
│ Sheldon Whitehouse        │ sheldon-whitehouse        │ Democrat   │ Senate  │
│ ...                       │                           │            │         │
│ Nancy Pelosi              │ nancy-pelosi              │ Democrat   │ House   │
│ Marjorie Taylor Greene    │ marjorie-taylor-greene    │ Republican │ House   │
│ Dan Crenshaw              │ dan-crenshaw              │ Republican │ House   │
└───────────────────────────┴───────────────────────────┴────────────┴─────────┘
```

### Michael Burry's current positions

```
Scion Asset Management, LLC
Filing Date: 2025-11-03
Period: 2025-09-30
Total Positions: 8

                        Top 8 Positions by Value                        
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ # ┃ Company                   ┃ CUSIP     ┃    Shares ┃        Value ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ 1 │ PALANTIR TECHNOLOGIES INC │ 69608A108 │ 5,000,000 │ $912,100,000 │
│ 2 │ NVIDIA CORPORATION        │ 67066G104 │ 1,000,000 │ $186,580,000 │
│ 3 │ PFIZER INC                │ 717081103 │ 6,000,000 │ $152,880,000 │
│ 4 │ HALLIBURTON CO            │ 406216101 │ 2,500,000 │  $61,500,000 │
│ 5 │ MOLINA HEALTHCARE INC     │ 60855R100 │   125,000 │  $23,920,000 │
│ 6 │ LULULEMON ATHLETICA INC   │ 550021109 │   100,000 │  $17,793,000 │
│ 7 │ SLM CORP                  │ 78442P106 │   480,054 │  $13,287,895 │
│ 8 │ BRUKER CORP               │ 116794207 │    48,334 │  $13,137,181 │
└───┴───────────────────────────┴───────────┴───────────┴──────────────┘
```

> **Note:** 13F filings are required quarterly with a 45-day lag by SEC law — this is the most current data legally available anywhere. No tool has more up-to-date hedge fund disclosures.

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
autopilot politician tommy-tuberville --limit 10
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

First install the package:

```bash
pip install -e .
playwright install chromium
```

Add to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "autopilot": {
      "command": "autopilot-mcp"
    }
  }
}
```

> **Tip:** Find the installed path of `autopilot-mcp` by running `which autopilot-mcp` (macOS/Linux) or `where autopilot-mcp` (Windows) after installation.

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
Fetches data from https://www.capitoltrades.com. No API key required. 200+ politicians tracked.

Run `autopilot politician --list` to see all available politicians.

### SEC EDGAR
Fetches 13F filings via the SEC EDGAR data API. No API key required.

**Available Managers:**
- Michael Burry (Scion Asset Management)
- Warren Buffett (Berkshire Hathaway)
- Bill Ackman (Pershing Square Capital Management)
- Ray Dalio (Bridgewater Associates)
- Stanley Druckenmiller (Duquesne Family Office)
- David Tepper (Appaloosa Management)
- Steven Cohen (Point72 Asset Management)
- David Einhorn (Greenlight Capital)
- George Soros (Soros Fund Management)
- Carl Icahn (Icahn Capital Management)
- Ken Griffin (Citadel Advisors)
- Chase Coleman (Tiger Global Management)
- Dan Loeb (Third Point LLC)

Run `autopilot pilot --list` to see all available managers.

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
- playwright

## License

MIT

## Disclaimer

This tool is for educational purposes only. Congressional trade data is public information. 13F filings are public SEC disclosures. Always verify information independently before making investment decisions.
