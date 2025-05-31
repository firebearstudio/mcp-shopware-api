# MCP Shopware API Debugging Guide

This guide helps you debug MCP communication between Claude Desktop and your Shopware MCP server effectively.

## 🔧 Debug Setup

### 1. Enhanced Logging

The MCP server now includes comprehensive logging that captures:

- **MCP Tool Calls**: Every tool invocation with parameters and results
- **API Requests**: All HTTP requests to Shopware API with headers and body
- **API Responses**: Response status, data summaries, and error details
- **Timestamps**: All events are timestamped for correlation

### 2. Log Locations

- **MCP Debug Log**: `/tmp/mcp-shopware-debug.log`
- **Claude Desktop Logs**: `~/Library/Logs/Claude/`

### 3. Log Levels

The server logs at different levels:
- `INFO`: Key events (tool calls, API requests/responses)
- `DEBUG`: Detailed data (full request/response bodies)
- `ERROR`: Errors and exceptions

## 📊 Debugging Tools

### Debug Script Usage

Use the provided debug script for easy log monitoring:

```bash
# Monitor live logs (default)
./debug_mcp.sh
./debug_mcp.sh tail

# Clear debug logs
./debug_mcp.sh clear

# Show recent activity summary
./debug_mcp.sh summary

# Search logs for specific terms
./debug_mcp.sh search "get_available_entities"
./debug_mcp.sh search "ERROR"

# Test server
./debug_mcp.sh test
```

### Manual Log Monitoring

```bash
# Monitor live logs with colors
tail -f /tmp/mcp-shopware-debug.log

# Show only MCP tool calls
grep "🔧 MCP TOOL" /tmp/mcp-shopware-debug.log

# Show only API requests
grep "🌐 API REQUEST" /tmp/mcp-shopware-debug.log

# Show only errors
grep "❌\|ERROR" /tmp/mcp-shopware-debug.log
```

## 🔍 Understanding Log Output

### MCP Tool Call Logs

```
2024-01-20 10:15:30 [INFO] MCP: 🔧 MCP TOOL CALLED: get_available_entities
2024-01-20 10:15:30 [INFO] MCP: 📥 INPUT ARGS: ()
2024-01-20 10:15:30 [INFO] MCP: 📥 INPUT KWARGS: {}
2024-01-20 10:15:31 [INFO] MCP: 📤 OUTPUT SUCCESS: get_available_entities
```

### Shopware API Logs

```
2024-01-20 10:15:30 [INFO] SHOPWARE_API: 🌐 API REQUEST: GET https://shop.example.com/api/_info/open-api-schema.json
2024-01-20 10:15:31 [INFO] SHOPWARE_API: 📡 API RESPONSE: GET https://shop.example.com/api/_info/open-api-schema.json -> 200
2024-01-20 10:15:31 [INFO] SHOPWARE_API: 📊 RESPONSE SUMMARY: 1 items (total: unknown)
```

### Search Request Logs

```
2024-01-20 10:16:00 [INFO] MCP: 🔧 MCP TOOL CALLED: search_shopware_entities
2024-01-20 10:16:00 [INFO] MCP: 📥 INPUT KWARGS: {'entity': 'product', 'search_criteria': {'limit': 10}}
2024-01-20 10:16:00 [INFO] SHOPWARE_API: 🌐 API REQUEST: POST https://shop.example.com/api/search/product
2024-01-20 10:16:00 [DEBUG] SHOPWARE_API: 📋 REQUEST BODY: {"limit": 10}
2024-01-20 10:16:01 [INFO] SHOPWARE_API: 📡 API RESPONSE: POST https://shop.example.com/api/search/product -> 200
2024-01-20 10:16:01 [INFO] SHOPWARE_API: 📊 RESPONSE SUMMARY: 10 items (total: 156)
```

## 🐛 Common Debug Scenarios

### 1. Tool Not Being Called

**Symptoms**: No "🔧 MCP TOOL CALLED" logs for expected tools

**Debugging**:
```bash
# Check if Claude Desktop can see the tools
./debug_mcp.sh summary

# Look for connection errors
grep "ERROR\|Exception" /tmp/mcp-shopware-debug.log
```

**Solutions**:
- Verify Claude Desktop MCP configuration
- Check environment variables are set
- Restart Claude Desktop

### 2. API Authentication Issues

**Symptoms**: "❌ ERROR RESPONSE" with 401 status codes

**Debugging**:
```bash
# Look for auth errors
./debug_mcp.sh search "401\|authentication\|token"
```

**Solutions**:
- Verify STORE_URL, API_KEY, API_SECRET in environment
- Check Shopware integration is active
- Verify API credentials have correct permissions

### 3. Tool Input/Output Issues

**Symptoms**: Tools called but unexpected results

**Debugging**:
```bash
# Check specific tool calls
./debug_mcp.sh search "search_shopware_entities"

# Look at input parameters
grep "📥 INPUT" /tmp/mcp-shopware-debug.log | tail -10
```

**Solutions**:
- Verify input parameter format (JSON vs dict)
- Check entity names are correct
- Validate search criteria structure

### 4. Performance Issues

**Symptoms**: Slow responses or timeouts

**Debugging**:
```bash
# Monitor response times by looking at timestamp differences
grep "🌐 API REQUEST\|📡 API RESPONSE" /tmp/mcp-shopware-debug.log | tail -20
```

**Solutions**:
- Add pagination to large queries
- Use `search_shopware_entity_ids` for lightweight searches
- Optimize search criteria and associations

## 🔧 Claude Desktop Debug Configuration

Ensure your Claude Desktop config includes debug settings:

```json
{
  "mcpServers": {
    "mcp-shopware-api": {
      "command": "uv",
      "args": ["run", "python", "/path/to/server.py"],
      "env": {
        "STORE_URL": "https://your-shop.com",
        "API_KEY": "your-key",
        "API_SECRET": "your-secret",
        "MCP_DEBUG": "1"
      }
    }
  },
  "debug": {
    "enabled": true,
    "level": "debug"
  }
}
```

## 📈 Performance Monitoring

### Response Time Analysis

```bash
# Extract timestamps for request/response pairs
grep "🌐 API REQUEST\|📡 API RESPONSE" /tmp/mcp-shopware-debug.log | \
  tail -20 | \
  awk '{print $1 " " $2 " " $0}'
```

### API Call Frequency

```bash
# Count API calls by endpoint
grep "🌐 API REQUEST" /tmp/mcp-shopware-debug.log | \
  awk '{print $NF}' | \
  sort | uniq -c | sort -nr
```

### Error Rate Analysis

```bash
# Show error percentage
total=$(grep "📡 API RESPONSE" /tmp/mcp-shopware-debug.log | wc -l)
errors=$(grep "📡 API RESPONSE.*[45][0-9][0-9]" /tmp/mcp-shopware-debug.log | wc -l)
echo "Error rate: $errors/$total"
```

## 🚨 Troubleshooting Checklist

1. **Environment Variables**
   - [ ] STORE_URL is set and accessible
   - [ ] API_KEY and API_SECRET are valid
   - [ ] No trailing slashes in STORE_URL

2. **Shopware Configuration**
   - [ ] Integration is active in Shopware admin
   - [ ] API credentials have required permissions
   - [ ] Store is accessible from your network

3. **MCP Configuration**
   - [ ] Claude Desktop config file is valid JSON
   - [ ] Server path is correct
   - [ ] uv/python environment is working

4. **Network/Connectivity**
   - [ ] Can reach Shopware store from command line
   - [ ] No firewall blocking connections
   - [ ] SSL certificates are valid

## 🔄 Debug Workflow

1. **Start Debugging**:
   ```bash
   ./debug_mcp.sh clear  # Clear old logs
   ./debug_mcp.sh tail   # Start monitoring
   ```

2. **Trigger Actions in Claude Desktop**:
   - Ask Claude to list available entities
   - Request specific data (products, orders, etc.)
   - Try complex searches with filters

3. **Analyze Logs**:
   - Check tool call sequence
   - Verify API request/response flow
   - Look for errors or unexpected behavior

4. **Iterate and Fix**:
   - Adjust queries based on findings
   - Fix configuration issues
   - Test edge cases