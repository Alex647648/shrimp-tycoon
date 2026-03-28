import { useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Header from './components/Header';
import PondCanvas from './components/PondCanvas';
import MetricCard from './components/MetricCard';
import ShrimpStatus from './components/ShrimpStatus';
import AIDecision from './components/AIDecision';
import FeishuPreview from './components/FeishuPreview';
import EventButtons from './components/EventButtons';
import ROICard from './components/ROICard';
import { useWebSocket } from './hooks/useWebSocket';
import { useShrimpData } from './hooks/useShrimpData';

const METRIC_CONFIG = [
  { key: 'temp', label: '水温', unit: '°C' },
  { key: 'DO', label: '溶解氧', unit: 'mg/L' },
  { key: 'pH', label: 'pH值', unit: '' },
  { key: 'ammonia', label: '氨氮', unit: 'mg/L' },
];

const MOCK_DECISIONS: Record<string, import('./types/api').DecisionReport> = {
  do_drop: {
    schema: 'DECISION-1.0',
    risk_level: 4,
    risk_label: '高风险',
    model_used: 'deepseek-r1',
    latency_ms: 2340,
    confidence: 0.87,
    summary: '凌晨溶解氧骤降至2.1mg/L，已低于安全阈值，虾群出现浮头现象，需立即干预。',
    actions: ['立即开启增氧机至最大功率', '减少当日投饵量50%', '检查水源进排水系统'],
    feeding: { total_ratio: 1.5, morning: null, evening: null, skip: false },
    disease: { risk: 'high', diseases: [], herb_formula: null, alert: true },
    harvest: { recommended: false, days_to_target: 25, current_price: 26.7, price_trend: 'stable', expected_revenue: 34600 },
    feishu_sent: true,
    feishu_message_id: 'mock-001',
  },
  wssv: {
    schema: 'DECISION-1.0',
    risk_level: 5,
    risk_label: '极高风险',
    model_used: 'deepseek-r1',
    latency_ms: 3120,
    confidence: 0.92,
    summary: '检测到疑似白斑综合征病毒(WSSV)感染迹象，多只虾体表出现白色斑点，需紧急隔离处理。',
    actions: ['立即隔离病虾，设置隔离区', '全池泼洒聚维酮碘消毒', '联系水产兽医进行PCR确诊'],
    feeding: { total_ratio: 0, morning: null, evening: null, skip: true },
    disease: { risk: 'critical', diseases: ['WSSV'], herb_formula: '板蓝根+大黄复方', alert: true },
    harvest: { recommended: false, days_to_target: 25, current_price: 26.7, price_trend: 'down', expected_revenue: 18200 },
    feishu_sent: true,
    feishu_message_id: 'mock-002',
  },
  storm: {
    schema: 'DECISION-1.0',
    risk_level: 3,
    risk_label: '中等风险',
    model_used: 'deepseek-r1',
    latency_ms: 1890,
    confidence: 0.78,
    summary: '暴雨导致水质突变，pH下降、浊度升高，需加强水质监测和应急处理。',
    actions: ['加大换水量，引入新鲜水源', '泼洒生石灰调节pH', '密切监测未来24小时水质变化'],
    feeding: { total_ratio: 2, morning: null, evening: null, skip: false },
    disease: { risk: 'medium', diseases: [], herb_formula: null, alert: false },
    harvest: { recommended: false, days_to_target: 25, current_price: 26.7, price_trend: 'stable', expected_revenue: 34600 },
    feishu_sent: false,
    feishu_message_id: null,
  },
  molt: {
    schema: 'DECISION-1.0',
    risk_level: 2,
    risk_label: '轻微风险',
    model_used: 'deepseek-r1',
    latency_ms: 1540,
    confidence: 0.85,
    summary: '检测到群体蜕壳高峰期信号，需调整投喂策略并补充矿物质。',
    actions: ['投喂中添加磷酸二氢钙', '停用当日消毒剂', '夜间加强巡塘观察'],
    feeding: { total_ratio: 2.5, morning: null, evening: null, skip: false },
    disease: { risk: 'low', diseases: [], herb_formula: null, alert: false },
    harvest: { recommended: false, days_to_target: 20, current_price: 26.7, price_trend: 'up', expected_revenue: 36800 },
    feishu_sent: false,
    feishu_message_id: null,
  },
  harvest: {
    schema: 'DECISION-1.0',
    risk_level: 1,
    risk_label: '低风险',
    model_used: 'deepseek-r1',
    latency_ms: 1220,
    confidence: 0.94,
    summary: '虾群已达上市规格，当前市场价处于高位，建议把握最佳捕捞窗口。',
    actions: ['安排72小时内分批捕捞', '提前联系收购商锁定价格', '捕捞前24小时停止投喂'],
    feeding: { total_ratio: 0, morning: null, evening: null, skip: true },
    disease: { risk: 'low', diseases: [], herb_formula: null, alert: false },
    harvest: { recommended: true, days_to_target: 0, current_price: 28.5, price_trend: 'up', expected_revenue: 42000 },
    feishu_sent: false,
    feishu_message_id: null,
  },
};

const MOCK_ALERTS: Record<string, { level: 'red' | 'amber' | 'green'; title: string; message: string; actions: string[] }> = {
  do_drop: { level: 'red', title: '🚨 溶解氧骤降告警', message: 'DO值降至2.1mg/L，低于安全阈值3.0mg/L', actions: ['立即开启增氧机', '减少投饵量'] },
  wssv: { level: 'red', title: '🚨 白斑病毒预警', message: '发现疑似WSSV感染虾只，体表白色斑点', actions: ['隔离病虾', '全池消毒', '联系兽医'] },
  storm: { level: 'amber', title: '⚠️ 暴雨水质突变', message: '降雨导致pH从7.8降至6.9，浊度升高', actions: ['加大换水', '调节pH'] },
  molt: { level: 'amber', title: '⚠️ 蜕壳高峰期', message: '群体性蜕壳信号明显，需特殊管理', actions: ['补充矿物质', '减少扰动'] },
  harvest: { level: 'green', title: '✅ 最佳捕捞时机', message: '虾群达标，市场价高位¥28.5/kg', actions: ['安排捕捞', '联系收购商'] },
};

const MOCK_SENSORS: Record<string, Partial<import('./types/api').SensorData>> = {
  do_drop: { DO: 2.1, temp: 24.5 },
  wssv: { dead_shrimp: true, count: 420 },
  storm: { pH: 6.9, temp: 23.1, transparency: 15 },
  molt: { molt_peak: true },
  harvest: { avg_weight: 41.2, count: 478 },
};

const MOCK_WQARS: Record<string, Partial<import('./types/api').WQARData>> = {
  do_drop: { csi: 60, risk_level: 4, risk_label: '高风险', indicators: { temp: { value: 24.5, status: 'normal', label: '正常' }, DO: { value: 2.1, status: 'danger', label: '严重偏低' }, pH: { value: 7.8, status: 'optimal', label: '最佳范围' }, ammonia: { value: 0.18, status: 'caution', label: '接近警戒' } } },
  wssv: { csi: 80, risk_level: 5, risk_label: '极高风险', indicators: { temp: { value: 25.4, status: 'optimal', label: '最适范围' }, DO: { value: 5.8, status: 'normal', label: '正常' }, pH: { value: 7.6, status: 'optimal', label: '最佳范围' }, ammonia: { value: 0.22, status: 'warning', label: '偏高' } } },
  storm: { csi: 45, risk_level: 3, risk_label: '中等风险', indicators: { temp: { value: 23.1, status: 'caution', label: '偏低' }, DO: { value: 5.5, status: 'normal', label: '正常' }, pH: { value: 6.9, status: 'warning', label: '偏低' }, ammonia: { value: 0.2, status: 'caution', label: '接近警戒' } } },
  molt: { csi: 25, risk_level: 2, risk_label: '轻微风险', indicators: { temp: { value: 25.4, status: 'optimal', label: '最适范围' }, DO: { value: 6.0, status: 'normal', label: '正常' }, pH: { value: 7.7, status: 'optimal', label: '最佳范围' }, ammonia: { value: 0.17, status: 'caution', label: '接近警戒' } } },
  harvest: { csi: 12, risk_level: 1, risk_label: '正常运营', indicators: { temp: { value: 26.0, status: 'optimal', label: '最适范围' }, DO: { value: 6.5, status: 'optimal', label: '充足' }, pH: { value: 7.9, status: 'optimal', label: '最佳范围' }, ammonia: { value: 0.12, status: 'optimal', label: '优良' } } },
};

function App() {
  const { state, handleMessage, setSpeed, clearDecision } = useShrimpData();
  const { connected, send } = useWebSocket(handleMessage);

  const handleTrigger = useCallback(
    (scenario: string) => {
      if (scenario === 'reset') {
        clearDecision();
        if (connected) {
          send({ type: 'trigger', scenario: 'reset', push_feishu: false });
        }
        // Reset to defaults handled by clearDecision
        return;
      }

      if (connected) {
        send({ type: 'trigger', scenario, push_feishu: true });
      } else {
        // Mock mode
        const mockSensor = MOCK_SENSORS[scenario];
        const mockWqar = MOCK_WQARS[scenario];
        const mockDecision = MOCK_DECISIONS[scenario];
        const mockAlert = MOCK_ALERTS[scenario];

        if (mockSensor) {
          handleMessage({
            type: 'tick',
            sensor: { ...state.sensor, ...mockSensor } as import('./types/api').SensorData,
            wqar: { ...state.wqar, ...mockWqar } as import('./types/api').WQARData,
          });
        }
        if (mockAlert) {
          handleMessage({
            type: 'alert',
            level: mockAlert.level,
            data: { scenario, title: mockAlert.title, message: mockAlert.message, actions: mockAlert.actions },
          });
        }
        if (mockDecision) {
          setTimeout(() => {
            handleMessage({ type: 'decision_ready', data: mockDecision });
            if (mockDecision.feishu_sent) {
              setTimeout(() => {
                handleMessage({ type: 'feishu_sent', message_id: mockDecision.feishu_message_id || '', level: mockAlert?.level || 'amber' });
              }, 800);
            }
          }, 1500);
        }
      }
    },
    [connected, send, handleMessage, state.sensor, state.wqar, clearDecision],
  );

  const handleSpeedChange = useCallback(
    (speed: number) => {
      setSpeed(speed);
      if (connected) {
        send({ type: 'set_speed', multiplier: speed });
      }
    },
    [connected, send, setSpeed],
  );

  const handleTriggerAlert = useCallback(() => {
    handleTrigger('do_drop');
  }, [handleTrigger]);

  const price = state.decision?.harvest?.current_price ?? 26.7;
  const indicators = state.wqar.indicators;

  return (
    <div className="h-screen flex flex-col bg-black">
      <Header
        day={state.sensor.day}
        speed={state.speed}
        onSpeedChange={handleSpeedChange}
        onTriggerAlert={handleTriggerAlert}
        price={price}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Main pond view */}
        <div className="flex-[65] relative">
          <PondCanvas
            riskLevel={state.wqar.risk_level}
            deadShrimp={state.sensor.dead_shrimp}
            moltPeak={state.sensor.molt_peak}
          />

          {/* Day counter — editorial style, bottom-left of pond */}
          <div className="absolute bottom-16 left-6 pointer-events-none select-none">
            <div className="editorial-heading text-[5rem] opacity-20 leading-none">
              D{state.sensor.day ?? 1}
            </div>
            <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-white/25 mt-1 ml-1">
              养殖天数
            </div>
          </div>

          {/* Bottom status bar — frosted glass */}
          <div className="absolute bottom-0 left-0 right-0 h-11 flex items-center justify-between px-6"
            style={{
              background: 'linear-gradient(to top, rgba(0,5,15,0.85) 0%, rgba(0,5,15,0.5) 60%, transparent 100%)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
            }}
          >
            <div className="flex items-center gap-4 text-xs text-white/40">
              <span className={connected ? 'text-emerald-400' : 'text-red-400'}>
                {connected ? '● 已连接' : '○ 离线模式'}
              </span>
              <span>塘口 {state.sensor.pond_id}</span>
              <span>{state.sensor.timestamp ? new Date(state.sensor.timestamp).toLocaleTimeString('zh-CN') : '--:--:--'}</span>
            </div>
            <div className="text-xs text-white/30">
              CSI:{state.wqar.csi} | 风险:{state.wqar.risk_label}
            </div>
          </div>

          {/* Alert banner */}
          <AnimatePresence>
            {state.alert && (
              <motion.div
                initial={{ y: 60, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: 60, opacity: 0 }}
                className={`absolute bottom-12 left-4 right-4 rounded-xl p-4 ${
                  state.alert.level === 'red'
                    ? 'bg-red-950/80 border border-red-500/40'
                    : state.alert.level === 'amber'
                      ? 'bg-amber-950/80 border border-amber-500/40'
                      : 'bg-emerald-950/80 border border-emerald-500/40'
                } backdrop-blur-sm`}
              >
                <p className="text-sm font-medium">{state.alert.data.title}</p>
                <p className="text-xs text-white/60 mt-1">{state.alert.data.message}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right sidebar */}
        <div className="flex-[35] border-l border-white/5 overflow-y-auto p-4 space-y-4">
          {/* Metric cards 2x2 */}
          <div className="grid grid-cols-2 gap-3">
            {METRIC_CONFIG.map((m) => (
              <MetricCard
                key={m.key}
                name={m.key}
                label={m.label}
                unit={m.unit}
                indicator={
                  indicators[m.key] || {
                    value: 0,
                    status: 'normal' as const,
                    label: '--',
                  }
                }
              />
            ))}
          </div>

          <ShrimpStatus sensor={state.sensor} wqar={state.wqar} />

          <AIDecision decision={state.decision} />

          <FeishuPreview alert={state.alert} feishuSent={state.feishuSent} />

          <EventButtons onTrigger={handleTrigger} />

          <ROICard sensor={state.sensor} price={price} />
        </div>
      </div>
    </div>
  );
}

export default App;
