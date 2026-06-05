#!/bin/bash
# OpenCopilot MCP Server 启动脚本

export PYTHONPATH="/Users/onetwo/Documents/trae_projects/OpenCopilot"

echo "🚀 Starting OpenCopilot MCP Server..."
echo "   Server exposes 5 tools:"
echo "   - query_knowledge_graph: Query knowledge graph (482 entities, 329 relations)"
echo "   - search_memory: Search companion memory (L2+L3)"
echo "   - get_broker_status: Get Broker system status"
echo "   - search_conversation: Search conversation history"
echo "   - get_system_info: Get system information"
echo ""
echo "📡 Listening on stdio (JSON-RPC)"
echo "   Press Ctrl+C to stop"
echo ""

python /Users/onetwo/Documents/trae_projects/OpenCopilot/tools/mcp_server.py
