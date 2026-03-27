#!/bin/bash
# 🦞 虾塘大亨 · 一键安装脚本（OpenClaw 开箱即用）
set -e

echo "🦞 虾塘大亨 · 安装中..."
echo ""

# ── 1. Python 依赖 ──
echo "📦 [1/6] 安装 Python 依赖..."
pip install -r requirements.txt -q

# ── 2. 创建 .env ──
if [ ! -f .env ]; then
    echo "📝 [2/6] 创建 .env 模板..."
    cat > .env << 'EOF'
# ═══════════════════════════════════════════
# 虾塘大亨 · 环境配置
# ═══════════════════════════════════════════

# 必填：Claude API Key（三层智能路由需要）
ANTHROPIC_API_KEY=

# 必填：飞书应用（告警/日报/周报推送）
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# 传感器模式：mock(默认) / tuya / dimos / drone
SENSOR_MODE=mock

# ── 涂鸦 IoT（SENSOR_MODE=tuya 时填写）──
# TUYA_REGION=eu
# TUYA_CLIENT_ID=
# TUYA_CLIENT_SECRET=
# TUYA_DEVICE_ID=

# ── DIMOS 机器狗（SENSOR_MODE=dimos 时填写）──
# DIMOS_MCP_URL=http://localhost:9090
EOF
    echo "   ✅ .env 已创建"
else
    echo "   ℹ️  .env 已存在，跳过"
fi

# ── 3. 初始化数据库 ──
echo "🗄️  [3/6] 初始化 SQLite 数据库..."
python3 -c "
import asyncio, sys
sys.path.insert(0, 'backend')
from db import PondDB
async def init():
    db = PondDB()
    await db.init()
    print('   ✅ SQLite 数据库已初始化 (data/pond.db)')
asyncio.run(init())
"

# ── 4. 注册 MCP Server ──
echo "🔌 [4/6] 注册 MCP Server..."
if command -v claude &> /dev/null; then
    claude mcp add shrimp-tycoon -- python3 mcp/server.py 2>/dev/null && \
        echo "   ✅ MCP Server 已注册（12 个工具）" || \
        echo "   ⚠️  MCP 注册失败，手动运行: claude mcp add shrimp-tycoon -- python3 mcp/server.py"
else
    echo "   ℹ️  claude CLI 未找到，手动注册:"
    echo "      claude mcp add shrimp-tycoon -- python3 mcp/server.py"
fi

# ── 5. 安装 OpenClaw Skill ──
echo "📚 [5/6] 安装 OpenClaw Skill..."
SKILL_DIR="${HOME}/.agents/skills/shrimp-tycoon"
if [ -d "$SKILL_DIR" ]; then
    echo "   ℹ️  Skill 目录已存在，更新中..."
fi
mkdir -p "$SKILL_DIR"
cp skill/SKILL.md "$SKILL_DIR/SKILL.md"
echo "   ✅ Skill 已安装到 $SKILL_DIR"

# ── 6. 添加 OpenClaw Cron ──
echo "⏰ [6/6] 添加 OpenClaw Cron 任务..."
if command -v openclaw &> /dev/null; then
    # 策略 Agent 日报（北京 06:00 = PDT 22:00）
    openclaw cron add --cron "0 22 * * *" \
        "策略Agent：为所有活跃虾塘生成今日日报。读 data/pond.db 当日传感器和决策记录，用 MCP 工具 harvest_advise + market_match + price_trend 分析，web_search 实时行情，生成 DAILY-1.0 日报，飞书推送。" 2>/dev/null && \
        echo "   ✅ 策略Agent cron（每天 06:00 北京时间）" || true

    # 增长 Agent 周报（北京 08:00 周一 = PDT 00:00 周一）
    openclaw cron add --cron "0 0 * * 1" \
        "增长Agent周报：生成本周获客任务清单。web_search 10个线索源，lead_score 评分，crm_write 写入CRM，匹配买家，计算多塘ROI，生成 GROWTH-1.0 周报，飞书推送。" 2>/dev/null && \
        echo "   ✅ 增长Agent周报 cron（每周一 08:00 北京时间）" || true

    # 增长 Agent 触达（北京 09:00 = PDT 01:00）
    openclaw cron add --cron "0 1 * * *" \
        "增长Agent触达：执行今日客户触达序列。读CRM中A/B级线索，按天数匹配触达模板（Day1首触/Day3PDF/Day7案例/Day14试用/Day21跟进），记录触达日志。" 2>/dev/null && \
        echo "   ✅ 增长Agent触达 cron（每天 09:00 北京时间）" || true
else
    echo "   ℹ️  openclaw CLI 未找到，手动添加 cron:"
    echo "      openclaw cron add --cron '0 22 * * *' '策略Agent：生成日报'"
    echo "      openclaw cron add --cron '0 0 * * 1'  '增长Agent：生成周报'"
    echo "      openclaw cron add --cron '0 1 * * *'  '增长Agent：触达序列'"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ 虾塘大亨安装完成！"
echo "═══════════════════════════════════════════════"
echo ""
echo "  📝 下一步："
echo "     1. 编辑 .env 填入 API Keys"
echo "     2. 启动后端：  python3 backend/server.py"
echo "     3. 启动前端：  cd frontend && npm run dev"
echo "     4. 打开浏览器：http://localhost:5173"
echo ""
echo "  🤖 OpenClaw 集成："
echo "     - Skill 已安装，说「查一下 A03 塘」即可触发"
echo "     - 3 个 cron 任务已注册，自动执行日报/周报/获客"
echo "     - MCP 12 个工具已注册，Claude 可直接调用"
echo ""
echo "  🦞 让每一口虾塘，都有一个 AI 合伙人。"
echo ""
