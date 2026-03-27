#!/bin/bash
# 虾塘大亨 · 一键安装脚本
set -e

echo "🦞 虾塘大亨 · 安装中..."

# 1. Python 依赖
echo "📦 安装 Python 依赖..."
pip install -r requirements.txt

# 2. 创建 .env（如不存在）
if [ ! -f .env ]; then
    echo "📝 创建 .env 模板..."
    cat > .env << 'EOF'
# 虾塘大亨配置
ANTHROPIC_API_KEY=
FEISHU_APP_ID=
FEISHU_APP_SECRET=
SENSOR_MODE=mock
# TUYA_ACCESS_ID=
# TUYA_ACCESS_SECRET=
# TUYA_DEVICE_ID=
EOF
    echo "⚠️  请填写 .env 中的 API Key"
fi

# 3. 初始化数据库
echo "🗄️ 初始化数据库..."
python -c "
import asyncio
import sys
sys.path.insert(0, 'backend')
from db import PondDB
async def init():
    db = PondDB()
    await db.init()
    print('   ✅ SQLite 数据库已初始化')
asyncio.run(init())
"

# 4. MCP Server 注册（如有 claude CLI）
if command -v claude &> /dev/null; then
    echo "🔌 注册 MCP Server..."
    claude mcp add shrimp-tycoon -- python mcp/server.py
    echo "   ✅ MCP Server 已注册"
else
    echo "ℹ️  claude CLI 未找到，跳过 MCP 注册"
    echo "   手动注册: claude mcp add shrimp-tycoon -- python mcp/server.py"
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "启动后端:  cd backend && python server.py"
echo "启动 MCP:  python mcp/server.py"
echo ""
echo "🦞 虾塘大亨准备就绪！"
