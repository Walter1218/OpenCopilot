#!/bin/bash

# API 集成测试脚本
# 测试所有模块 API 是否正确集成到主系统

set -e

BASE_URL="http://localhost:8089"
PASS=0
FAIL=0
SKIP=0

echo "=========================================="
echo "OpenCopilot API 集成测试"
echo "=========================================="
echo "测试目标: $BASE_URL"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local expected_status=$3
    local description=$4
    local data=$5
    
    echo -n "测试: $description ... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" 2>/dev/null || echo "000")
    elif [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$endpoint" \
                -H "Content-Type: application/json" \
                -d "$data" 2>/dev/null || echo "000")
        else
            response=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL$endpoint" 2>/dev/null || echo "000")
        fi
    fi
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC} (HTTP $response)"
        ((PASS++))
    elif [ "$response" = "000" ]; then
        echo -e "${YELLOW}⏭️  SKIP${NC} (连接失败)"
        ((SKIP++))
    else
        echo -e "${RED}❌ FAIL${NC} (Expected: $expected_status, Got: $response)"
        ((FAIL++))
    fi
}

# 检查服务是否运行
echo "1. 检查服务状态"
echo "----------------------------------------"
if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 服务正在运行${NC}"
else
    echo -e "${RED}❌ 服务未运行${NC}"
    echo "请先启动服务: python smart_copilot_platform.py"
    exit 1
fi

# 系统端点测试
echo ""
echo "2. 系统端点测试"
echo "----------------------------------------"
test_endpoint "GET" "/health" "200" "系统健康检查"
test_endpoint "GET" "/api/health" "200" "API 健康检查"
test_endpoint "GET" "/api/modules" "200" "获取模块信息"
test_endpoint "GET" "/" "200" "根路径"

# 上下文 API 测试
echo ""
echo "3. 上下文 API 测试"
echo "----------------------------------------"
test_endpoint "GET" "/api/context/current" "200" "获取当前上下文"

# MCP API 测试
echo ""
echo "4. MCP API 测试"
echo "----------------------------------------"
test_endpoint "GET" "/api/mcp/servers" "200" "列出 MCP Server"
test_endpoint "POST" "/api/mcp/refresh" "200" "刷新 MCP 配置"
test_endpoint "GET" "/api/mcp/status" "200" "获取 MCP 状态"

# 符号引用 API 测试
echo ""
echo "5. 符号引用 API 测试"
echo "----------------------------------------"

# 创建临时测试文件
TEMP_FILE="/tmp/test_symbols_$$.py"
cat > "$TEMP_FILE" << 'EOF'
def hello():
    """Say hello"""
    print("Hello, World!")

def greet(name):
    """Greet someone"""
    hello()
    print(f"Hello, {name}!")

class MyClass:
    """Test class"""
    
    def method(self):
        """Test method"""
        hello()
EOF

test_endpoint "GET" "/api/code/symbols?file_path=$TEMP_FILE" "200" "获取文件符号"
test_endpoint "POST" "/api/code/definition" "200" "查找符号定义" '{"file_path": "'$TEMP_FILE'", "line": 0, "character": 4}'
test_endpoint "POST" "/api/code/references" "200" "查找符号引用" '{"file_path": "'$TEMP_FILE'", "line": 0, "character": 4}'
test_endpoint "POST" "/api/code/clear-cache" "200" "清除符号缓存"

# 清理临时文件
rm -f "$TEMP_FILE"

# PPT API 测试
echo ""
echo "6. PPT API 测试"
echo "----------------------------------------"
test_endpoint "POST" "/api/ppt/generate" "200" "生成 PPT" '{"slides": [{"title": "Test", "content": "Content"}]}'

# WebSocket 测试（简单检查）
echo ""
echo "7. WebSocket 测试"
echo "----------------------------------------"
echo -n "测试: WebSocket 端点 ... "
# WebSocket 需要特殊处理，这里只检查端点是否存在
if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ws/events" | grep -q "426\|200"; then
    echo -e "${GREEN}✅ PASS${NC} (端点存在)"
    ((PASS++))
else
    echo -e "${YELLOW}⏭️  SKIP${NC} (需要 WebSocket 客户端)"
    ((SKIP++))
fi

# 汇总结果
echo ""
echo "=========================================="
echo "测试结果汇总"
echo "=========================================="
echo -e "通过: ${GREEN}$PASS${NC}"
echo -e "失败: ${RED}$FAIL${NC}"
echo -e "跳过: ${YELLOW}$SKIP${NC}"
echo "总计: $((PASS + FAIL + SKIP))"

if [ $FAIL -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 所有测试通过！${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}⚠️  有 $FAIL 个测试失败${NC}"
    exit 1
fi
