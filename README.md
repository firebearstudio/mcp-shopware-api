# MCP Shopware API Server

A Model Context Protocol (MCP) server that provides seamless integration with Shopware 6 stores through their **Admin API** (not the Storefront API). This server enables AI assistants to interact with Shopware stores, retrieve data, and perform operations using OAuth authentication.

## Features

- 🔐 OAuth 2.0 authentication with automatic token refresh
- 🛍️ Shopware 6 Admin API integration with 150+ entity types
- 🚀 Built with FastMCP for simplified MCP server development
- 📦 Package management with uv
- 🏪 Comprehensive store data access and manipulation tools
- 🔍 Universal search system supporting complex queries
- 🎯 Optimized for AI assistant workflows

## Prerequisites

- Python 3.10+
- uv package manager
- Shopware 6 store with Admin API access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mcp-shopware-api.git
cd mcp-shopware-api
```

2. Install dependencies using uv:
```bash
uv sync
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your Shopware store credentials:
```env
STORE_URL=https://your-shopware-store.com
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
```

## Configuration

### Shopware 6 Admin API Credentials

**Important**: This MCP server connects to the Shopware **Admin API**, not the Storefront API. You need admin-level integration credentials.

To get your API credentials:

1. Log in to your Shopware 6 admin panel
2. Go to Settings → System → Integrations
3. Create a new integration or use an existing one
4. Copy the Access Key ID (API_KEY) and Secret Access Key (API_SECRET)
5. Ensure the integration has the necessary permissions for the entities you want to access

### Environment Variables

- `STORE_URL`: Your Shopware 6 store URL (without trailing slash)
- `API_KEY`: Your Shopware Admin API Access Key ID
- `API_SECRET`: Your Shopware Admin API Secret Access Key

## Prompts

### `ready_to_ship_orders`
**Automatically retrieve and format Shopware orders that are paid but not yet shipped.**

This intelligent prompt:
- Executes complex API queries to find orders in "paid" transaction state and "open" delivery state
- Dynamically retrieves state machine UUIDs for accurate filtering
- Loads comprehensive order data including customer info, products, and shipping addresses
- Returns formatted instructions for displaying results in a clear table format

**What it provides:**
- Order numbers and dates
- Product details with quantities and pricing
- Complete shipping addresses
- Payment and delivery status information
- Sorted by newest orders first

**Use case:** Perfect for fulfillment workflows where you need to quickly identify which orders are ready for shipping and packaging.

## Available Tools

### Entity Search & Retrieval Tools

#### `search_shopware_entities(entity, search_criteria)`
Universal search tool for any Shopware entity using the Admin API `/api/search/{entity}` endpoint.

**Supported Entities** (150+ total including):
- **Core**: product, order, customer, category, media, user
- **E-commerce**: payment-method, shipping-method, promotion, tax
- **Content**: cms-page, cms-block, landing-page, mail-template
- **System**: sales-channel, language, currency, country

**Search Criteria Features**:
- Advanced filtering (equals, contains, range, etc.)
- Sorting and pagination
- Association loading
- Field selection for performance
- Aggregations for statistics

**Product Variant Handling**: Automatically filters to parent products only (excludes variants) unless custom filters are provided.

#### `search_shopware_entity_ids(entity, search_criteria)`
Lightweight search returning only matching IDs for performance optimization. Same search criteria as full search but returns only IDs.

#### `get_shopware_entity_by_id(entity, entity_id, associations)`
Fetch single entity by ID with optional association loading. Direct entity retrieval by unique identifier.

### Universal HTTP Tools

#### `shopware_get_request(endpoint, params)`
Make GET requests to any Shopware Admin API endpoint with automatic authentication.
- Access any API endpoint directly
- Optional query parameters support
- Useful for custom endpoints and info endpoints

#### `shopware_post_request(endpoint, data, params)`
Make POST requests to any Shopware Admin API endpoint with automatic authentication.
- Create new entities
- Execute custom actions
- Advanced search operations

#### `shopware_patch_request(endpoint, data, params)`
Make PATCH requests to update entities in the Shopware Admin API.
- Update existing entities
- Partial data updates
- Flexible field modifications

#### `shopware_delete_request(endpoint, params)`
Make DELETE requests to remove entities from the Shopware Admin API.
- Delete entities by ID
- Supports additional parameters
- Proper error handling

### Bulk Operations

#### `shopware_sync_operation(entity, action, payload, operation_key, indexing_behavior, skip_trigger_flow)`
Execute high-performance bulk operations using Shopware's Sync API.

**Actions**:
- `upsert`: Create or update multiple entities
- `delete`: Remove multiple entities

**Performance Optimizations**:
- `indexing_behavior`: Control data indexing (sync/async/disabled)
- `skip_trigger_flow`: Skip business logic flows for faster processing
- Transactional operations (all-or-nothing)

**Use Cases**:
- Bulk product imports/updates
- Mass inventory updates
- Category management
- Customer data imports
- Cleanup operations

### Schema & Discovery Tools

#### `get_available_entities()`
Get a complete list of all available entity names in the Shopware system. Returns 150+ entity types that can be used with search and CRUD operations.

#### `get_entity_definition(entity)`
Get the entity definition from Shopware's schema including properties, types, and relationships. Essential for understanding entity structure before operations.

#### `get_entity_openapi_schema(entity)`
Get the OpenAPI schema definition for a specific entity including endpoint definitions, request/response schemas, and available operations.

## MCP Client Setup

<details>
<summary><strong>Claude Code</strong> - Automatic project discovery</summary>

Claude Code automatically discovers and connects to MCP servers in your project directory.

**Setup Steps**:
Run the following command to add mcp server to Claude Code:

```bash
claude mcp add mcp-shopware-api \
    -e STORE_URL=https://your-store-url.com \
    -e API_KEY=your_api_key_here \
    -e API_SECRET=your_api_secret_here \
    -- uv \
    --directory /absolute/path/to/mcp-shopware-api \
    run \
    python src/mcp_shopware_api/server.py
```

</details>

<details>
<summary><strong>Claude Desktop</strong> - Desktop application setup</summary>

**Setup Steps**:
1. **Create or edit configuration file**:
   
   **macOS:**
   ```bash
   mkdir -p ~/Library/Application\ Support/Claude/
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
   
   **Windows:**
   ```bash
   mkdir %APPDATA%\Claude
   notepad %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Add server configuration**:
   ```json
   {
     "mcpServers": {
       "shopware-api": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/mcp-shopware-api",
           "run",
           "python",
           "src/mcp_shopware_api/server.py"
         ],
         "env": {
           "STORE_URL": "https://your-shopware-store.com",
           "API_KEY": "your_api_key_here",
           "API_SECRET": "your_api_secret_here"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** for changes to take effect.

</details>

<details>
<summary><strong>Cursor</strong> - AI-powered IDE setup</summary>

**Setup Steps**:
1. **Configure MCP server** via Cursor settings:
   - Open Command Palette (`Cmd/Ctrl + Shift + P`)
   - Search for "MCP: Configure Servers"
   - Add server configuration:
   ```json
   {
     "shopware-api": {
       "command": "uv",
       "args": [
         "--directory",
         "/absolute/path/to/mcp-shopware-api",
         "run",
         "python",
         "src/mcp_shopware_api/server.py"
       ],
       "env": {
         "STORE_URL": "https://your-shopware-store.com",
         "API_KEY": "your_api_key_here",
         "API_SECRET": "your_api_secret_here"
       }
     }
   }
   ```

2. **Restart Cursor** to apply the configuration.

</details>

<details>
<summary><strong>Windsurf</strong> - Codeium's AI-powered IDE</summary>

**Setup Steps**:
1. **Configure MCP integration**:
   - Open Settings → Extensions → MCP
   - Add new server configuration:
   ```json
   {
     "name": "shopware-api",
     "command": "uv",
     "args": [
       "--directory",
       "/absolute/path/to/mcp-shopware-api",
       "run",
       "python",
       "src/mcp_shopware_api/server.py"
     ],
     "env": {
       "STORE_URL": "https://your-shopware-store.com",
       "API_KEY": "your_api_key_here",
       "API_SECRET": "your_api_secret_here"
     }
   }
   ```

2. **Reload Windsurf** to enable the MCP server.

</details>

<details>
<summary><strong>Cline (VS Code Extension)</strong> - Visual Studio Code integration</summary>

**Prerequisites**: 

**Setup Steps**:
1. **Configure Cline MCP server**:
   - Open Command Palette (`Cmd/Ctrl + Shift + P`)
   - Run "Cline: Configure MCP Servers"
   - Add configuration:
   ```json
   {
     "mcpServers": {
       "shopware-api": {
         "command": "uv",
         "args": [
           "--directory",
           "/absolute/path/to/mcp-shopware-api",
           "run",
           "python",
           "src/mcp_shopware_api/server.py"
         ],
         "env": {
           "STORE_URL": "https://your-shopware-store.com",
           "API_KEY": "your_api_key_here",
           "API_SECRET": "your_api_secret_here"
         }
       }
     }
   }
   ```

2. **Restart VS Code** or reload the Cline extension.

</details>

## Testing Your Setup

Once configured with any MCP client, you can test the connection:

```
"Test my Shopware store connection"
"Show me 5 products from my store"
"Get information about recent orders"
"List available tools for Shopware"
```

## Debugging

If you encounter issues with the MCP server, see [DEBUGGING.md](DEBUGGING.md) for comprehensive troubleshooting steps and debugging techniques.

## Development

### Running the Server Manually

```bash
uv run python src/mcp_shopware_api/server.py
```

### Development Commands

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black src/
uv run isort src/
```

### Project Structure

```
mcp-shopware-api/
├── src/
│   └── mcp_shopware_api/
│       ├── __init__.py
│       └── server.py          # Main MCP server implementation
├── docs/
│   ├── api.md                 # API documentation
│   └── task.openapi.md        # OpenAPI specifications
├── pyproject.toml             # Project configuration
├── .env.example               # Environment template
├── DEBUGGING.md               # Debugging guide
└── README.md                  # This file
```

## Authentication

The server implements OAuth 2.0 client credentials flow with the Shopware Admin API:

- Automatic token refresh (60-second buffer before expiration)
- Secure credential handling
- Error handling for authentication failures
- Bearer token authentication for all requests

## API Coverage

This MCP server provides access to the complete Shopware 6 Admin API, including:

- **Product Management**: Products, variants, categories, manufacturers
- **Order Processing**: Orders, order items, payments, shipments
- **Customer Management**: Customers, addresses, groups
- **Content Management**: CMS pages, blocks, media, templates
- **System Configuration**: Sales channels, languages, currencies
- **Marketing Tools**: Promotions, newsletters, reviews
- **And 150+ more entity types**

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Create an issue for bug reports or feature requests
- Check existing issues before creating new ones
- Provide detailed information about your Shopware version and configuration
- Include relevant logs when reporting issues

## Roadmap

- [x] Basic store information and connectivity testing
- [x] Product retrieval with pagination
- [x] Order data access with pagination  
- [x] Customer information fetching with pagination
- [x] Universal search system for all entities
- [x] Advanced search criteria support
- [x] Association loading and optimization
- [ ] **Response size optimization**: Limit requested fields and associations to prevent token count limits when dealing with large Shopware API responses