#!/bin/bash

# MCP Shopware API Debug Script
# This script helps debug MCP communication by tailing logs and providing useful commands

echo "🔧 MCP Shopware API Debug Helper"
echo "================================"
echo ""

# Function to show log locations
show_logs() {
    echo "📁 Log file locations:"
    echo "  - MCP Debug Log: /tmp/mcp-shopware-debug.log"
    echo "  - Claude Desktop Logs: ~/Library/Logs/Claude/"
    echo ""
}

# Function to tail logs
tail_logs() {
    echo "📊 Starting live log monitoring..."
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Create log file if it doesn't exist
    touch /tmp/mcp-shopware-debug.log
    
    # Tail the debug log with colors
    tail -f /tmp/mcp-shopware-debug.log | sed \
        -e 's/🔧 MCP TOOL CALLED/\x1b[32m🔧 MCP TOOL CALLED\x1b[0m/g' \
        -e 's/📥 INPUT/\x1b[34m📥 INPUT\x1b[0m/g' \
        -e 's/📤 OUTPUT SUCCESS/\x1b[32m📤 OUTPUT SUCCESS\x1b[0m/g' \
        -e 's/❌ OUTPUT ERROR/\x1b[31m❌ OUTPUT ERROR\x1b[0m/g' \
        -e 's/🌐 API REQUEST/\x1b[36m🌐 API REQUEST\x1b[0m/g' \
        -e 's/📡 API RESPONSE/\x1b[35m📡 API RESPONSE\x1b[0m/g' \
        -e 's/📊 RESPONSE SUMMARY/\x1b[33m📊 RESPONSE SUMMARY\x1b[0m/g'
}

# Function to clear logs
clear_logs() {
    echo "🗑️  Clearing debug logs..."
    > /tmp/mcp-shopware-debug.log
    echo "✅ Logs cleared"
}

# Function to test MCP server
test_server() {
    echo "🧪 Testing MCP server..."
    cd /opt/homebrew/var/www/mcp/mcp-shopware-api
    uv run python src/mcp_shopware_api/server.py --help 2>&1 | head -10
}

# Function to show recent log summary
show_summary() {
    echo "📋 Recent log summary (last 50 lines):"
    echo "======================================="
    if [ -f /tmp/mcp-shopware-debug.log ]; then
        tail -50 /tmp/mcp-shopware-debug.log | grep -E "(🔧|📤|❌|🌐|📡)" | tail -20
    else
        echo "No debug log found yet. Start Claude Desktop and make some requests."
    fi
}

# Function to search logs
search_logs() {
    if [ -z "$1" ]; then
        echo "Usage: $0 search <search_term>"
        echo "Example: $0 search \"get_available_entities\""
        return 1
    fi
    
    echo "🔍 Searching logs for: $1"
    echo "========================"
    if [ -f /tmp/mcp-shopware-debug.log ]; then
        grep -n --color=always "$1" /tmp/mcp-shopware-debug.log | tail -20
    else
        echo "No debug log found yet."
    fi
}

# Main script logic
case "$1" in
    "tail"|"")
        show_logs
        tail_logs
        ;;
    "clear")
        clear_logs
        ;;
    "test")
        test_server
        ;;
    "summary")
        show_summary
        ;;
    "search")
        search_logs "$2"
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  tail     - Monitor live logs (default)"
        echo "  clear    - Clear debug logs"
        echo "  test     - Test MCP server"
        echo "  summary  - Show recent log summary"
        echo "  search   - Search logs for term"
        echo "  help     - Show this help"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac