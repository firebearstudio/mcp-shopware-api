import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

# Handle both direct execution and module execution
try:
    from .prompts import register_prompts
    from .tools import ShopwareAuth, register_tools
except ImportError:
    # If relative imports fail, try absolute imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from mcp_shopware_api.prompts import register_prompts
    from mcp_shopware_api.tools import ShopwareAuth, register_tools

load_dotenv()

# Debug information
print(f"Python executable: {sys.executable}", file=sys.stderr)
print(f"Working directory: {os.getcwd()}", file=sys.stderr)
print(f"Script path: {__file__}", file=sys.stderr)

# Environment validation
store_url = os.getenv("STORE_URL")
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

print(
    f"Environment variables: STORE_URL={bool(store_url)}, API_KEY={bool(api_key)}, API_SECRET={bool(api_secret)}",
    file=sys.stderr,
)

if not all([store_url, api_key, api_secret]):
    print(
        "ERROR: Missing required environment variables: STORE_URL, API_KEY, API_SECRET",
        file=sys.stderr,
    )
    raise ValueError(
        "Missing required environment variables: STORE_URL, API_KEY, API_SECRET"
    )

# Initialize FastMCP server and auth
mcp: FastMCP = FastMCP("mcp-shopware-api")

# Ensure environment variables are not None
if store_url is None or api_key is None or api_secret is None:
    raise ValueError("Environment variables cannot be None")

shopware_auth = ShopwareAuth(store_url, api_key, api_secret)

# Register tools and prompts
register_tools(mcp, shopware_auth)
register_prompts(mcp, shopware_auth)

def main():
    """Main entry point for the MCP server."""
    mcp.run()

if __name__ == "__main__":
    main()
