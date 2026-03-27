# 虾塘大亨 · Agent 工程约束规范 v1.0

> 本文件是 Agent 系统的工程法典。所有开发必须遵守，优先级高于功能需求。  
> 违反任意一条约束 → 必须在 PR review 前修复，不得 merge。

---

## 一、架构约束

### 1.1 单向数据流（最重要）

```
传感器 → MCP Server → Sentinel → DB
                                 ↓
                            Strategist → DB
                                         ↓
                                    Growth → 飞书
```

**禁止**：
- ❌ Agent 直接调用另一个 Agent（Sentinel 不能调 Strategist）
- ❌ Agent 直接修改另一个 Agent 的状态
- ❌ MCP Server 写 DB（工具层无状态）
- ❌ Growth 直接读传感器（必须经过 DB）

**允许**：
- ✅ Agent 读 DB（向下游只读）
- ✅ Agent 调 MCP 工具
- ✅ Agent 调飞书推送
- ✅ 多 Agent 并发读同一 DB（只要不同表/行）

### 1.2 层次边界

| 层 | 职责 | 禁止 |
|----|------|------|
| **MCP 工具层** | 计算 + 查询，无副作用 | 写 DB / 调 LLM / 发飞书 |
| **Agent 决策层** | 调工具 + 调 LLM + 决策 | 直接操作传感器硬件 |
| **推送层（Feishu）** | 发消息 + 缓存 token | 参与决策逻辑 |
| **存储层（DB）** | 读写持久化数据 | 包含业务逻辑 |
| **API 层（FastAPI）** | HTTP + WS 入口 | 包含决策逻辑 |

### 1.3 单文件行数限制

| 类型 | 上限 | 超出时 |
|------|------|--------|
| Agent 文件（.py） | 200 行 | 拆分为 `_core.py` + `_prompts.py` |
| MCP 工具文件 | 250 行 | 按功能拆分子模块 |
| FastAPI 路由文件 | 150 行 | 拆分 router |
| 单个函数 | 60 行 | 必须拆分 |

---

## 二、边界控制

### 2.1 Sentinel Agent 边界

**可以做**：
- 读当前传感器数据（sensor_read MCP 工具）
- 调用水质分析、投喂建议、病害评估工具
- 写 `decisions` 表
- 发飞书告警（risk_level ≥ 3 时）

**不可以做**：
- ❌ 读取历史数据（这是 Strategist 的职责）
- ❌ 做捕捞决策（只能给出参考，最终由 Strategist 决策）
- ❌ 调用 market_match 工具
- ❌ 直接操作增氧机等硬件（只能发建议，不能执行）

**触发条件**：由 server.py tick 驱动，每次 tick 均运行（快路径：规则引擎），CSI>20 时走 LLM

### 2.2 Strategist Agent 边界

**可以做**：
- 读 `sensor_readings` 和 `decisions` 表
- 调用 harvest_advise、market_match、price_trend 工具
- 写 `daily_reports` 表
- 发飞书日报（每日定时）

**不可以做**：
- ❌ 直接读传感器（必须经 DB）
- ❌ 写 `decisions` 表（不能覆盖 Sentinel 的记录）
- ❌ 发紧急告警（告警是 Sentinel 的职责）

**触发条件**：每日 20:00 cron，或手动触发 `POST /api/strategist/run`

### 2.3 Growth Agent 边界

**可以做**：
- 读所有 DB 表（只读）
- 读外部市场数据（price_trend、market_match）
- 写 `growth_reports` 表
- 发飞书周报

**不可以做**：
- ❌ 读传感器
- ❌ 发养殖操作建议（只做商业分析）
- ❌ 自动续费操作（只能发提醒）

**触发条件**：每周一 09:00 cron

### 2.4 MCP 工具边界（无状态原则）

每个工具必须满足：
- **幂等**：相同输入 → 相同输出，多次调用无副作用
- **无状态**：不依赖上次调用的结果
- **无 DB 写入**：工具只读 DB，不写
- **超时 ≤ 5s**：任何工具调用超过 5s 视为失败

---

## 三、命名规范

### 3.1 文件命名

```
snake_case，动词_名词风格

✅ sentinel.py / strategist.py / db.py / feishu.py
✅ tuya_adapter.py / kb_searcher.py
❌ SentinelAgent.py / DBHelper.py / utils.py（太宽泛）
```

### 3.2 类命名

```
PascalCase，名词

✅ SentinelAgent / StrategistAgent / PondDB / FeishuPusher
✅ TuyaAdapter / KBSearcher / SentinelMemory
❌ sentinel_agent / feishu_pusher_class / Helper
```

### 3.3 函数/方法命名

```
snake_case，动词_名词

✅ analyze() / run_daily() / send_alert() / get_trend()
✅ _rule_engine() / _llm_analyze() / _keyword_model()
❌ process() / handle() / do_stuff() / run()（太模糊）

私有方法：单下划线前缀 _method_name
异步方法：同步命名约定，加 async 声明（不加 async_ 前缀）
```

### 3.4 MCP 工具命名

```
snake_case，动词_名词

✅ sensor_read / water_quality_score / feeding_recommend
✅ disease_assess / harvest_advise / market_match
❌ getSensor / waterQuality / feed
```

### 3.5 数据 Schema 命名

```
UPPER-VERSION 格式

✅ SDP-1.0 / WQAR-1.0 / DECISION-1.0 / DAILY-1.0 / GROWTH-1.0
规则：Schema 版本升级 → 文件版本号递增，旧版本保留兼容层
```

### 3.6 常量命名

```
UPPER_SNAKE_CASE，模块级定义

✅ RISK_LABELS / WATER_COLORS / KEYWORD_TRIGGERS / KB_PATH
✅ MAX_RECONNECT / RECONNECT_DELAY / WS_URL
❌ riskLabels / waterColors（小驼峰不用于 Python 常量）
```

### 3.7 环境变量命名

```
UPPER_SNAKE，按服务分组

FEISHU_APP_ID / FEISHU_APP_SECRET
ANTHROPIC_API_KEY
TUYA_REGION / TUYA_CLIENT_ID / TUYA_CLIENT_SECRET / TUYA_DEVICE_ID
DB_PATH（可选，默认 data/pond.db）
```

---

## 四、风险管理

### 4.1 LLM 调用风险

| 风险 | 处理方式 |
|------|---------|
| API 超时（>10s） | fallback 到规则引擎，记录 `model_used="rule_engine_fallback"` |
| API 不可用（401/500） | fallback 到规则引擎，不抛异常 |
| 返回非法 JSON | 重试一次（strip markdown），再失败 → fallback |
| 连续调用 Opus >5次 | 自动降级到 Haiku，等待 60s 后恢复 |
| 响应缺失必要字段 | `result.setdefault(field, default_value)` 补全 |

```python
# 标准 LLM 调用模式（必须遵守）
async def _llm_analyze(sensor, wqar, model):
    try:
        async with asyncio.timeout(10):  # 严格 10s 超时
            result = await _call_llm(sensor, wqar, model)
            return _validate_schema(result)  # 必须验证
    except (asyncio.TimeoutError, anthropic.APIError, json.JSONDecodeError) as e:
        logger.warning("LLM call failed (%s): %s — fallback", model, e)
        return _rule_engine(sensor, wqar)  # 必须有 fallback
```

### 4.2 飞书推送风险

| 风险 | 处理方式 |
|------|---------|
| 推送失败（网络） | 重试1次，失败后 `feishu_sent=False`，不阻塞决策流程 |
| Token 过期 | 自动刷新（已在 FeishuPusher 中实现），静默重试 |
| 消息内容过长 | 截断至 4000 字，添加「...（已截断）」 |
| 重复推送同一事件 | 同一 pond_id + scenario 的告警，60分钟内不重复发送 |

```python
# 去重逻辑（必须实现）
_last_alert: dict = {}  # {f"{pond_id}:{scenario}": timestamp}

def _should_push(pond_id, scenario, cooldown_min=60) -> bool:
    key = f"{pond_id}:{scenario}"
    last = _last_alert.get(key, 0)
    return time.time() - last > cooldown_min * 60
```

### 4.3 传感器数据风险

| 风险 | 处理方式 |
|------|---------|
| 传感器断连 | 使用最后一次有效数据，并在 sensor 中加 `data_stale=True` |
| 数值异常（DO=999, pH=-1）| 范围检查，超出物理合理范围 → 标记 `invalid`，不触发告警 |
| 数据频率下降 | 记录 `missing_count`，连续5次无数据 → 飞书发送离线告警 |

```python
# 合理范围（物理上限）
VALID_RANGES = {
    "temp":         (0, 45),
    "DO":           (0, 20),
    "pH":           (3, 12),
    "ammonia":      (0, 10),
    "transparency": (0, 200),
    "avg_weight":   (0, 200),
}

def validate_sensor(sensor: dict) -> dict:
    """验证传感器数据合理性，异常字段标记 invalid"""
    for field, (lo, hi) in VALID_RANGES.items():
        val = sensor.get(field)
        if val is not None and not (lo <= val <= hi):
            logger.warning("Sensor %s out of range: %s", field, val)
            sensor[f"{field}_invalid"] = True
    return sensor
```

### 4.4 决策安全红线

以下操作**禁止 AI 自主推荐**，必须加「需人工确认」标注：

| 操作 | 原因 |
|------|------|
| 全塘清塘/排水 | 不可逆，损失极大 |
| 大量用药（>标准剂量 2倍） | 可能造成虾群急性中毒 |
| 紧急捕捞（提前30天以上） | 收益损失重大 |
| 关闭所有增氧设备 | 极端危险 |

```python
# 危险操作关键词检测
DANGEROUS_KEYWORDS = ["清塘", "全部排水", "停止增氧", "超量用药", "大量投药"]

def _safety_check(actions: list[str]) -> list[str]:
    """检测危险操作，添加人工确认标注"""
    result = []
    for action in actions:
        if any(kw in action for kw in DANGEROUS_KEYWORDS):
            result.append(f"⚠️【需人工确认】{action}")
        else:
            result.append(action)
    return result
```

### 4.5 模型调用频率控制

```python
# API 速率保护（全局单例）
class RateLimiter:
    OPUS_MAX_PER_HOUR = 20      # Opus 每小时最多调用20次
    HAIKU_MAX_PER_HOUR = 200    # Haiku 每小时最多调用200次
    FEISHU_MAX_PER_HOUR = 50    # 飞书每小时最多发50条

    def can_call(self, model: str) -> bool: ...
    def record(self, model: str): ...
```

### 4.6 DB 写入风险

| 风险 | 处理方式 |
|------|---------|
| DB 写入失败 | 记录 warning 日志，**不阻塞决策流程**（决策比持久化重要） |
| DB 文件损坏 | 自动备份（每日），启动时校验完整性 |
| 磁盘满 | 超过 500MB 时删除30天前的 sensor_readings |

```python
# DB 写入必须非阻塞
async def save_decision(decision: dict):
    try:
        await db.execute(INSERT_SQL, decision)
    except Exception as e:
        logger.warning("DB write failed (non-fatal): %s", e)
        # 不 raise，不影响主流程
```

---

## 五、错误处理规范

### 5.1 异常分级

| 级别 | 示例 | 处理 |
|------|------|------|
| **FATAL** | DB 无法启动 / MCP Server 崩溃 | 停止服务，发飞书系统告警 |
| **ERROR** | LLM 连续失败 >3次 | 记录 error 日志，飞书发送工程师告警 |
| **WARNING** | LLM 单次失败 / 飞书推送失败 | 记录 warning 日志，fallback 继续运行 |
| **INFO** | 关键词触发 / 模型切换 | 记录 info 日志 |

### 5.2 日志规范

```python
# 格式：%(asctime)s %(levelname)s %(name)s: %(message)s
logger = logging.getLogger("sentinel")  # 模块名作为 logger 名

# 必须记录的事件
logger.info("Sentinel triggered: keyword=%s model=%s pond=%s", tag, model, pond_id)
logger.info("Decision made: risk=%d latency=%dms model=%s", rl, latency, model)
logger.warning("LLM fallback: reason=%s model=%s", reason, model)
logger.warning("Feishu push failed: pond=%s scenario=%s", pond_id, scenario)
logger.error("Critical: %s", error_detail)
```

### 5.3 WebSocket 错误处理

```python
# 任何 handler 内部异常不得导致 WS 连接断开
async def handle_message(ws, msg):
    try:
        await _process(ws, msg)
    except Exception as e:
        logger.error("WS handler error: %s", e)
        await ws.send_json({"type": "error", "message": str(e)})
        # 不 raise，保持连接
```

---

## 六、测试约束

### 6.1 每个 Agent 必须有单元测试

```
tests/
├── test_sentinel.py     # 5个场景 × 3个断言
├── test_strategist.py   # 日报生成 + 飞书推送 mock
├── test_growth.py       # 周报生成
├── test_mcp_tools.py    # 9个工具的输入输出验证
└── test_db.py           # CRUD 操作
```

### 6.2 测试必须 mock 外部依赖

```python
# 禁止在测试中真实调用 Anthropic / 飞书 API
@patch("sentinel.anthropic.AsyncAnthropic")
@patch("feishu.requests.post")
async def test_do_drop(mock_feishu, mock_anthropic):
    mock_anthropic.return_value.messages.create = AsyncMock(return_value=MOCK_RESPONSE)
    ...
```

### 6.3 验收标准（CI 门禁）

```bash
pytest tests/ -v              # 全部通过
python -m mypy backend/ agent/ mcp/  # 类型检查无 error（warning 允许）
python -m flake8 --max-line-length=100  # 代码风格
```

---

## 七、版本控制约束

### 7.1 提交信息格式

```
<type>(<scope>): <description>

type: feat / fix / refactor / test / docs / chore
scope: sentinel / strategist / growth / mcp / db / feishu / frontend

✅ feat(sentinel): add keyword triggers for DO/WSSV/pH
✅ fix(feishu): handle token expiry with auto-refresh
✅ refactor(mcp): extract kb_query into separate module
❌ update stuff
❌ fix bug
```

### 7.2 不得推送到 main 的内容

- ❌ 包含真实 API Key（ANTHROPIC_API_KEY, FEISHU_APP_SECRET 等）
- ❌ DEV_CONSTRAINTS.md / INTERFACE_SPEC.md（已在 .gitignore）
- ❌ data/pond.db（运行时生成，已在 .gitignore）
- ❌ 测试不通过的代码

---

## 八、快速检查清单

开发任何功能前，确认：

- [ ] 函数 ≤ 60 行
- [ ] 文件 ≤ 200 行
- [ ] 所有外部调用有 try/catch + fallback
- [ ] LLM 调用有 10s 超时
- [ ] 飞书推送失败不阻塞主流程
- [ ] 危险操作加「需人工确认」标注
- [ ] 传感器数据经过 validate_sensor() 检查
- [ ] 新增 Agent 接口在 INTERFACE_SPEC.md 中有描述
- [ ] 新增工具在 MCP Server 注册表中有条目
- [ ] 单元测试 mock 了所有外部 API

---

*版本：v1.0 | 2026-03-27 | 所有开发必须遵守*
