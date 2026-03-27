# 虾塘大亨 · 前端完整需求文档 v1.0

> 目标：让评委在 3 分钟内理解「AI 替代养殖专家」的完整价值链。  
> 定位：实时 AI 水产决策系统仪表盘，不是营销页面。

---

## 一、技术栈

| 项目 | 选型 |
|------|------|
| 框架 | React 18 + Vite + TypeScript |
| 样式 | Tailwind CSS v3 |
| 动画 | framer-motion |
| 图标 | lucide-react |
| 字体 | Google Fonts（见下） |
| 后端通信 | WebSocket `ws://localhost:8766/ws` + HTTP `http://localhost:8766` |

---

## 二、设计语言

### 颜色

| 用途 | 值 |
|------|----|
| 背景 | `#000000` |
| 主要文字 | `#ffffff` |
| 次要文字 | `rgba(255,255,255,0.5)` |
| 极弱文字 | `rgba(255,255,255,0.3)` |
| 主色（数据/高亮） | `#00c8b4`（青绿荧光） |
| ROI 数字 | `#f5a623`（琥珀） |
| 告警红 | `#ff4d6d` |
| 告警橙 | `#f97316` |
| 告警绿 | `#22c55e` |

### 字体

```html
<!-- index.html head 中加载 -->
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&family=Barlow:wght@300;400;500;600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet" />
```

| 用途 | 字体 | 样式 |
|------|------|------|
| 大标题、决策摘要 | Instrument Serif | italic |
| 正文、标签、按钮 | Barlow | 300–600 |
| 所有数字值 | Space Mono | 400/700 |

### Liquid Glass 效果（index.css）

```css
@layer components {
  .liquid-glass {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(8px) saturate(1.4);
    box-shadow: inset 0 1px 1px rgba(255,255,255,0.14), 0 4px 24px rgba(0,0,0,0.35);
    position: relative;
    overflow: hidden;
  }
  .liquid-glass::before {
    content: '';
    position: absolute; inset: 0;
    border-radius: inherit;
    padding: 1.4px;
    background: linear-gradient(180deg,
      rgba(255,255,255,0.45) 0%, rgba(255,255,255,0.15) 20%,
      rgba(255,255,255,0) 40%,   rgba(255,255,255,0) 60%,
      rgba(255,255,255,0.15) 80%, rgba(255,255,255,0.45) 100%);
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    pointer-events: none;
  }
  .liquid-glass-strong {
    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(50px) saturate(1.6);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 1px rgba(255,255,255,0.18);
    position: relative;
    overflow: hidden;
  }
  /* liquid-glass-strong::before 同上，改 opacity 0.5/0.2 */
}
```

---

## 三、页面布局

```
┌───────────────────── Header（fixed 56px）─────────────────────────┐
│ 🦞 虾塘大亨  [赛道二·AI合伙人]  D{n}  {时刻}  [1x][10x][100x]  [🚨触发告警]  ⚡¥26.7/kg │
└───────────────────────────────────────────────────────────────────┘

┌──── 主视图 flex-[65] ────────────┐  ┌── 侧栏 flex-[35] overflow-y-auto ──┐
│                                  │  │ [水质监测 2×2 卡片]                 │
│   <PondCanvas />                 │  │ [虾群状态]                          │
│   （绝对定位，充满父容器）         │  │ [AI 决策建议]                       │
│                                  │  │ [飞书推送预览] ← 条件显示            │
│   底部状态条（absolute bottom-0）  │  │ [演示事件按钮 2×3]                  │
│   告警横幅（absolute bottom-12）  │  │ [ROI 收益预测]                      │
└──────────────────────────────────┘  └─────────────────────────────────────┘
```

---

## 四、组件详细规范

### 4.1 Header

```
[🦞 虾塘大亨]  [赛道二·AI合伙人]  ···  [D48 凌晨]  [1x][10x][100x]  [🚨触发告警]  [⚡ ¥26.7/kg]
```

- Logo：🦞 + `虾塘大亨`（font-heading italic text-xl）+ `AI AQUACULTURE DECISION SYSTEM`（Barlow 9px tracking-[0.2em] white/40）
- 徽章：`liquid-glass rounded-full px-3 py-1 text-xs`
- 养殖日：`D{day}`（Space Mono text-3xl font-bold）+ 时刻（white/50 text-sm）
- 速度按钮：三个 `rounded-full px-3 py-1 text-xs`，当前选中 `bg-white/10 border border-white/20`
- 告警按钮：`border border-red-500/60 text-red-400 rounded-full px-3 py-1 text-xs`，idle 时 `animate-pulse`
- 价格：`⚡` + Space Mono bold `¥{price}/kg`
- Header 背景：`border-b border-white/5 bg-black/80 backdrop-blur-sm`

---

### 4.2 PondCanvas（Canvas 动画）

**画面层次（从下到上）**：

1. 天空渐变（顶部 25%，深蓝→透明）
2. 水体渐变（随 `risk_level` 变色，见下表）
3. 丁达尔光柱（5道，`globalAlpha 0.03`，斜入射）
4. 水面折射线（sinusoidal，`globalAlpha 0.055`）
5. 底部泥沙渐变
6. 气泡（22个，从底部上升至水面消失，wobble 左右漂移）
7. **像素风小龙虾**（80只，见下）
8. 扫描线叠加（CSS `repeating-linear-gradient`，`opacity-[0.028]`）

**水体颜色（risk_level）**：

| risk_level | 水体主色 | 底色 |
|-----------|---------|------|
| 1 | `hsl(195,80%,18%)` | `hsl(200,60%,8%)` |
| 2 | `hsl(195,70%,14%)` | `hsl(200,50%,6%)` |
| 3 | `hsl(40,55%,14%)` | `hsl(35,40%,6%)` |
| 4 | `hsl(10,60%,14%)` | `hsl(5,50%,6%)` |
| 5 | `hsl(0,70%,11%)` | `hsl(0,60%,5%)` |

**小龙虾渲染（Canvas 像素风）**：

- 数量：80只（`moltPeak=true` 时 70只）
- 大小：`size = 7 + random()*5`，缩放系数 `0.09`（当前 0.11 太大）
- 朝向：按 `vx` 方向镜像
- 颜色：`rgba(220,90,50,0.82)`（正常），灰白（dead_shrimp）
- 组成部件：尾扇 → 腹节×6 → 头胸甲 → 步足×5 → 头部 → 额剑 → 眼柄 → 触须
- **risk≥4 时**：虾群 `vy` 向上偏移，聚集在水面 25% 区域

**底部状态条**（`absolute bottom-0 h-10`）：
- 左：`● 已连接`（绿）或 `○ 离线模式`（橙）+ 塘口 A03 + 时间戳
- 右：`CSI:{n} | 风险:{label}`（white/30）

**告警横幅**（`absolute bottom-12`，framer-motion）：
```tsx
initial={{ y: 60, opacity: 0 }}
animate={{ y: 0, opacity: 1 }}
exit={{ y: 60, opacity: 0 }}
// 背景色按 level: red/amber/green
```

---

### 4.3 水质监测卡片（4个，grid-cols-2 gap-3）

```
┌─────────────────────────────┐
│ 水温          [最适范围]      │  ← 顶部 border-t-2 彩色边线
│                              │
│  25.6 °C                    │  ← Space Mono text-2xl bold
└─────────────────────────────┘
```

状态色系：

| status | border | text | badge bg |
|--------|--------|------|---------|
| optimal | `border-emerald-400` | `text-emerald-400` | `bg-emerald-400/10` |
| normal | `border-cyan-400` | `text-cyan-400` | `bg-cyan-400/10` |
| caution | `border-yellow-400` | `text-yellow-400` | `bg-yellow-400/10` |
| warning | `border-orange-400` | `text-orange-400` | `bg-orange-400/10` |
| danger | `border-red-400` | `text-red-400` | `bg-red-400/10` |

数值精度：temp/DO/pH → 1位小数，ammonia → 2位小数

---

### 4.4 虾群状态

```
┌──────────────────────────────────────┐
│ 存活数量          存活率              │
│  485 尾          97.0%               │  ← Space Mono bold
│                                      │
│ 均重             距上市规格           │
│  28.5g           11.5g               │
│                                      │
│ 生长进度  ━━━━━━━━━━━━━━━○──  71%    │  ← 渐变进度条，顶部光点
│                                      │
│ CSI 水质综合评分  ●────────────  18  │  ← 低=好，绿→黄→红
└──────────────────────────────────────┘
```

进度条：`bg-gradient-to-r from-cyan-500 to-teal-400`，光点：绝对定位白点随进度移动

CSI 进度条颜色：`csi<30` → emerald，`30-60` → yellow，`>60` → red

---

### 4.5 AI 决策建议框

`liquid-glass-strong rounded-2xl p-4`

**无决策时**：
```
⊕ AI 决策建议                    [等待中...]
─────────────────────────────────────────────
等待数据分析...（italic white/30）
```

**有决策时**：
```
⊕ AI 决策建议   [高风险]   claude-haiku · 2.3s
─────────────────────────────────────────────
凌晨溶解氧骤降至2.1mg/L，已低于安全阈值，
虾群出现浮头现象，需立即干预。
（Instrument Serif italic 15px）

① 立即开启增氧机至最大功率
② 减少当日投饵量50%
③ 检查水源进排水系统

[投喂 1.5%] [病害:高风险] [暂不捕捞]
```

风险标签颜色：1=emerald / 2=cyan / 3=yellow / 4=orange / 5=red

---

### 4.6 飞书推送预览

**触发条件**：收到 `feishu_sent` WebSocket 消息  
**动画**：从右侧滑入（`x: 40→0, opacity: 0→1，0.3s ease-out`）

```
┌──────────────────────────────────────┐
│ 🦞 虾塘大亨 · 告警通知    ✓ 已发送   │  ← 深蓝左边框（4px）
│ ──────────────────────────────────   │
│ ⚠️ 风险等级：4级（高风险）           │
│ 📊 DO值降至 2.1mg/L                  │
│ 🔧 立即操作：                        │
│    · 开启增氧机至最大功率            │
│    · 减少投饵量50%                   │
│ ✅ 已推送至养殖户手机                 │
└──────────────────────────────────────┘
```

样式：`border-l-4 border-blue-500 bg-blue-950/40 rounded-r-xl p-3`

---

### 4.7 演示事件按钮（6个，grid-cols-2）

| 文字 | emoji | 边框色 | 触发 scenario |
|------|-------|--------|--------------|
| 凌晨DO骤降 | 💧 | `border-red-500/60` | `do_drop` |
| 白斑病毒预警 | 🦠 | `border-red-500/60` | `wssv` |
| 暴雨水质突变 | ⛈️ | `border-orange-500/60` | `storm` |
| 蜕壳高峰期 | 🦀 | `border-yellow-500/60` | `molt` |
| 最佳捕捞时机 | ✅ | `border-emerald-500/60` | `harvest` |
| 重置仿真 | 🔄 | `border-white/20` | `reset` |

每个按钮：`liquid-glass rounded-xl p-3 text-xs border`  
点击效果：`whileTap={{ scale: 0.95 }}` + 短暂高亮（`bg-white/10`）

---

### 4.8 ROI 收益预测

```
┌──────────────────────────────────────┐
│ 💰 收益预测                           │
│                                      │
│  ¥34,600          2.5×              │
│  （#00c8b4 荧光）  （琥珀 ROI倍数）   │
│                                      │
│ 存活量：412尾 × 35g = 14.4kg         │
│ 市场价：¥26.7/kg                     │
│ SaaS月费：¥2,000                     │
│ 病害规避：≈¥8,000                    │
└──────────────────────────────────────┘
```

---

## 五、数据接口

### WebSocket 接收（`ws://localhost:8766/ws`）

```typescript
// 每5秒 tick
{ type: 'tick', sensor: SensorData, wqar: WQARData }

// 告警
{ type: 'alert', level: 'red'|'amber'|'green', data: AlertEvent }

// AI 决策完成
{ type: 'decision_ready', data: DecisionReport }

// 飞书推送确认
{ type: 'feishu_sent', message_id: string, level: string }
```

### WebSocket 发送

```typescript
{ type: 'trigger', scenario: 'do_drop'|'wssv'|'storm'|'molt'|'harvest'|'reset', push_feishu: boolean }
{ type: 'set_speed', multiplier: 1 | 10 | 100 }
```

### HTTP

```
GET /api/status → { status: 'ok', agent_ready: boolean }
GET /api/price?days=30 → { current: number, trend: string, history: [...] }
GET /api/roi → ROIData
```

### 离线兜底（后端未启动时）

后端连不上时，所有演示按钮触发 mock 数据，界面完整运行，不崩溃。  
Mock 数据已在 `App.tsx` 的 `MOCK_*` 对象中定义，保持现有结构。

---

## 六、状态机

| 状态 | Canvas 颜色 | 虾群行为 | 告警横幅 |
|------|------------|---------|---------|
| 正常（risk 1） | 青蓝 | 正常游动 | 无 |
| 警戒（risk 2-3） | 偏暗/琥珀 | 正常，略聚集 | amber（risk 3） |
| 危险（risk 4-5） | 红褐/深红 | 上浮聚集 | red |
| dead_shrimp | 任意 | 部分虾变灰白 | red |
| molt_peak | 青蓝 | 虾群密度减小 | amber |
| harvest | 青蓝清澈 | 正常，虾体饱满 | green |

---

## 七、动画规范

| 元素 | 动画 |
|------|------|
| 首次加载（侧栏卡片） | stagger fade-in，间隔 0.08s |
| 告警横幅出现/消失 | `y: ±60, opacity: 0→1`，spring |
| AI 决策框内容更新 | blur-in：`filter: blur(8px)→0`，0.4s |
| 飞书预览卡片 | 从右滑入：`x: 40→0, opacity: 0→1`，0.3s |
| 演示按钮点击 | `scale: 0.95`，0.1s |
| 数值变化（可选） | 数字滚动（CSS counter 或 framer-motion） |

---

## 八、已知问题 & 修复优先级

| 优先级 | 问题 | 修复方法 |
|--------|------|---------|
| **P0** | 虾群密度过高，个体轮廓模糊 | count 80，size 系数 0.09，增加间距 |
| **P0** | 侧栏 ROI 卡片被截断 | 确认侧栏 `overflow-y-auto` 且高度正确 |
| **P1** | Instrument Serif 未在标题/摘要中生效 | Header logo + AIDecision summary 加 `font-heading italic` |
| **P1** | 飞书预览样式过于简陋 | 按 4.6 节深蓝边框卡片重写 |
| **P2** | 演示按钮缺点击动画 | 加 `whileTap={{ scale: 0.95 }}` |
| **P2** | 进度条无光点移动效果 | 绝对定位白点，`left: {progress}%` |

---

## 九、文件结构

```
frontend/
├── index.html          # 含 Google Fonts link
├── src/
│   ├── App.tsx         # 根组件，WebSocket 连接，mock 数据
│   ├── main.tsx
│   ├── index.css       # liquid-glass CSS，字体变量
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── PondCanvas.tsx      # Canvas 虾塘动画
│   │   ├── MetricCard.tsx      # 水质指标卡（×4）
│   │   ├── ShrimpStatus.tsx    # 虾群状态
│   │   ├── AIDecision.tsx      # AI 决策建议框
│   │   ├── FeishuPreview.tsx   # 飞书推送预览
│   │   ├── EventButtons.tsx    # 演示事件按钮
│   │   └── ROICard.tsx         # 收益预测
│   ├── hooks/
│   │   ├── useWebSocket.ts     # WS 连接 + 自动重连
│   │   └── useShrimpData.ts    # 全局状态管理
│   └── types/
│       └── api.ts              # 所有数据类型（勿改，与后端对齐）
```

---

*生成时间：2026-03-27 | 对应后端：`backend/server.py`（port 8766）*
