#!/usr/bin/env python3
"""MCP Server for Autopilot CLI - Exposes Congressional trades and 13F filings as MCP tools."""

import json
import sys
from typing import Any, Dict, List
from autopilot_cli.sources.capitol_trades import (
    fetch_politician_trades,
    fetch_trades_by_ticker,
    list_politicians,
)
from autopilot_cli.sources.sec_edgar import fetch_13f_filings, list_hedge_fund_managers


class MCPServer:
    """Simple MCP server implementation following the MCP protocol."""

    def __init__(self):
        self.tools = [
            {
                "name": "query_politician_trades",
                "description": "Query recent Congressional stock trades for a specific politician by name or slug (e.g., 'nancy-pelosi', 'tuberville'). Returns trades with date, ticker, type, and amount.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "politician_slug": {
                            "type": "string",
                            "description": "Politician name slug (e.g., 'nancy-pelosi', 'tommy-tuberville')",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of trades to fetch (default: 20)",
                            "default": 20,
                        },
                    },
                    "required": ["politician_slug"],
                },
            },
            {
                "name": "query_trades_by_ticker",
                "description": "Query recent Congressional trades for a specific stock ticker symbol. Shows which members of Congress have traded this stock. Example: 'NVDA', 'AAPL', 'TSLA'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": "Stock ticker symbol (e.g., 'NVDA', 'AAPL')",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of trades to fetch (default: 20)",
                            "default": 20,
                        },
                    },
                    "required": ["ticker"],
                },
            },
            {
                "name": "list_politicians",
                "description": "List all politicians with tracked Congressional trading disclosures. Returns politician names, slugs, party affiliation, and chamber.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "query_13f_filing",
                "description": "Query the latest 13F filing for a hedge fund manager. Shows their portfolio positions including holdings, values, and shares. Available managers: 'burry' (Michael Burry), 'buffett' (Warren Buffett), 'ackman' (Bill Ackman), 'dalio' (Ray Dalio), 'druckenmiller'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "manager": {
                            "type": "string",
                            "description": "Manager slug: 'burry', 'buffett', 'ackman', 'dalio', 'druckenmiller', or CIK number",
                        },
                    },
                    "required": ["manager"],
                },
            },
            {
                "name": "list_hedge_fund_managers",
                "description": "List all trackable hedge fund managers with 13F filings. Returns manager names and CIK numbers.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests."""
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "autopilot-cli-mcp",
                        "version": "0.1.0",
                    },
                    "capabilities": {
                        "tools": {},
                    },
                },
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": self.tools,
                },
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            try:
                result = self.call_tool(tool_name, arguments)

                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result, indent=2, default=str),
                            }
                        ],
                    },
                }

            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32000,
                        "message": str(e),
                    },
                }

        elif method == "notifications/initialized":
            return None  # Notifications don't require a response

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool and return results."""
        if tool_name == "query_politician_trades":
            politician_slug = arguments["politician_slug"]
            limit = arguments.get("limit", 20)

            trades = fetch_politician_trades(politician_slug, page_size=limit)
            return [t.model_dump() for t in trades]

        elif tool_name == "query_trades_by_ticker":
            ticker = arguments["ticker"]
            limit = arguments.get("limit", 20)

            trades = fetch_trades_by_ticker(ticker, page_size=limit)
            return [t.model_dump() for t in trades]

        elif tool_name == "list_politicians":
            politicians = list_politicians()
            return [p.model_dump() for p in politicians]

        elif tool_name == "query_13f_filing":
            manager = arguments["manager"]
            filing = fetch_13f_filings(manager)
            return filing.model_dump() if filing else None

        elif tool_name == "list_hedge_fund_managers":
            managers = list_hedge_fund_managers()
            return [m.model_dump() for m in managers]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def run(self):
        """Run the MCP server on stdio."""
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}",
                    },
                }
                print(json.dumps(error_response), flush=True)


def main():
    """Main entry point for MCP server."""
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
