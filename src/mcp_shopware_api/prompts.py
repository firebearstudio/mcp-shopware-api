import json

from fastmcp import FastMCP

from .tools import ShopwareAuth


def register_prompts(mcp: FastMCP, shopware_auth: ShopwareAuth) -> None:
    """Register all MCP prompts with the FastMCP instance"""

