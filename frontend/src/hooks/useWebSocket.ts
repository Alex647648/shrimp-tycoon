import { useState, useEffect, useCallback, useRef } from 'react';
import { SensorData, WQARData, AlertEvent, DecisionReport, Scenario } from '../types';

// ── Mock 数据生成（离线/Vercel 部署时使用）──────────────────
function rand(base: number, range: number) {
  return +(base + (Math.random() - 0.5) * range).toFixed(2);
}

function mockTick(day: number): { sensor: SensorData; wqar: WQARData } {
  const temp = rand(25.5, 1.5);
  const doVal = rand(6.2, 1.0);
  const ph = rand(7.8, 0.4);
  const ammonia = rand(0.16, 0.08);
  const csi = Math.max(1, Math.round((28 - temp) ** 2 + (6 - doVal) ** 2 * 3 + (ammonia - 0.1) * 40));
  const risk = csi <= 20 ? 1 : csi <= 40 ? 2 : csi <= 60 ? 3 : csi <= 80 ? 4 : 5;
  const labels = ['正常运营', '轻微风险', '中等风险', '高风险', '极高风险'];

  return {
    sensor: {
      temp, do: doVal, ph, ammonia,
      timestamp: new Date().toISOString(),
      day,
      avg_weight: rand(28.5, 3),
      count: Math.round(rand(485, 20)),
      dead_shrimp: false,
      molt_peak: false,
    },
    wqar: {
      risk_level: risk,
      csi_score: csi,
      status_label: labels[risk - 1],
    },
  };
}

const MOCK_SCENARIOS: Record<string, {
  sensorPatch: Partial<SensorData>;
  alert: AlertEvent;
  decision: DecisionReport;
}> = {
  do_drop: {
    sensorPatch: { do: 2.1, temp: 24.5 },
    alert: { level: 'red', message: '🚨 溶解氧骤降至 2.1mg/L，低于安全阈值', timestamp: new Date().toISOString() },
    decision: {
      suggestion: '凌晨溶解氧骤降至2.1mg/L，已低于安全阈值，虾群出现浮头现象，需立即干预。',
      diagnosis: '溶解氧严重不足，可能原因：水体富营养化、高温、藻类大量死亡',
      actions: ['立即开启增氧机至最大功率', '减少当日投饵量50%', '检查水源进排水系统'],
      risk_level: 4,
      auxiliary: { feed_ratio: '1.5%', disease_risk: 'high', harvest_timing: '暂缓捕捞' },
    },
  },
  wssv: {
    sensorPatch: { dead_shrimp: true, count: 420 },
    alert: { level: 'red', message: '🚨 发现疑似白斑病毒(WSSV)感染迹象', timestamp: new Date().toISOString() },
    decision: {
      suggestion: '检测到疑似白斑综合征病毒(WSSV)感染迹象，多只虾体表出现白色斑点，需紧急隔离处理。',
      diagnosis: 'WSSV 早期特征：体表白斑、活力下降、死虾增加',
      actions: ['立即隔离病虾，设置隔离区', '全池泼洒聚维酮碘消毒', '联系水产兽医进行PCR确诊'],
      risk_level: 5,
      auxiliary: { feed_ratio: '0%（停喂）', disease_risk: 'critical', harvest_timing: '紧急评估是否抢收' },
    },
  },
  storm: {
    sensorPatch: { ph: 6.9, temp: 23.1 },
    alert: { level: 'amber', message: '⚠️ 暴雨导致水质突变，pH降至6.9', timestamp: new Date().toISOString() },
    decision: {
      suggestion: '暴雨导致水质突变，pH下降、浊度升高，需加强水质监测和应急处理。',
      diagnosis: '暴雨冲刷导致酸性物质进入塘口',
      actions: ['加大换水量，引入新鲜水源', '泼洒生石灰调节pH', '密切监测未来24小时水质变化'],
      risk_level: 3,
      auxiliary: { feed_ratio: '2.0%', disease_risk: 'medium', harvest_timing: '继续养殖' },
    },
  },
  molt: {
    sensorPatch: { molt_peak: true },
    alert: { level: 'amber', message: '⚠️ 检测到群体蜕壳高峰期信号', timestamp: new Date().toISOString() },
    decision: {
      suggestion: '检测到群体蜕壳高峰期信号，需调整投喂策略并补充矿物质。',
      diagnosis: '群体性蜕壳周期，属正常生理现象',
      actions: ['投喂中添加磷酸二氢钙', '停用当日消毒剂', '夜间加强巡塘观察'],
      risk_level: 2,
      auxiliary: { feed_ratio: '2.5%', disease_risk: 'low', harvest_timing: '继续养殖' },
    },
  },
  harvest: {
    sensorPatch: { avg_weight: 41.2, count: 478 },
    alert: { level: 'green', message: '✅ 虾群已达上市规格，市场价高位¥28.5/kg', timestamp: new Date().toISOString() },
    decision: {
      suggestion: '虾群已达上市规格，当前市场价处于高位，建议把握最佳捕捞窗口。',
      diagnosis: '均重41.2g，超过目标规格40g',
      actions: ['安排72小时内分批捕捞', '提前联系收购商锁定价格', '捕捞前24小时停止投喂'],
      risk_level: 1,
      auxiliary: { feed_ratio: '0%（停喂）', disease_risk: 'low', harvest_timing: '建议立即捕捞' },
    },
  },
};

// ── Hook ────────────────────────────────────────────────────
export function useWebSocket() {
  const [sensorData, setSensorData] = useState<SensorData | null>(null);
  const [wqarData, setWqarData] = useState<WQARData | null>(null);
  const [alert, setAlert] = useState<AlertEvent | null>(null);
  const [decision, setDecision] = useState<DecisionReport | null>(null);
  const [feishuSent, setFeishuSent] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1);
  const [mockMode, setMockMode] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const dayRef = useRef(42);
  const mockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 启动 mock tick
  const startMockTicks = useCallback(() => {
    setMockMode(true);
    // 立即发一次
    const { sensor, wqar } = mockTick(dayRef.current);
    setSensorData(sensor);
    setWqarData(wqar);

    mockIntervalRef.current = setInterval(() => {
      dayRef.current += speed >= 100 ? 1 : 0;
      const { sensor, wqar } = mockTick(dayRef.current);
      setSensorData(sensor);
      setWqarData(wqar);
    }, 2000 / speed);
  }, [speed]);

  useEffect(() => {
    // 尝试连接 WebSocket
    try {
      const wsUrl = location.hostname === 'localhost' || location.hostname === '127.0.0.1'
        ? 'ws://localhost:8766/ws'
        : ''; // Vercel 部署时不连

      if (!wsUrl) {
        startMockTicks();
        return;
      }

      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        // 连上了，清除 mock
        if (mockIntervalRef.current) {
          clearInterval(mockIntervalRef.current);
          mockIntervalRef.current = null;
        }
        setMockMode(false);
      };

      socket.onerror = () => {
        if (!mockMode && !mockIntervalRef.current) startMockTicks();
      };

      socket.onclose = () => {
        if (!mockIntervalRef.current) startMockTicks();
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.type) {
          case 'tick': {
            const raw = data.sensor;
            setSensorData({
              temp: raw.temp, do: raw.DO ?? raw.do ?? 0, ph: raw.pH ?? raw.ph ?? 0,
              ammonia: raw.ammonia ?? 0, timestamp: raw.timestamp, day: raw.day,
              avg_weight: raw.avg_weight ?? 0, count: raw.count ?? 0,
              dead_shrimp: raw.dead_shrimp ?? false, molt_peak: raw.molt_peak ?? false,
            });
            const wqar = data.wqar;
            setWqarData({
              risk_level: wqar.risk_level ?? 1,
              csi_score: wqar.csi ?? wqar.csi_score ?? 0,
              status_label: wqar.risk_label ?? wqar.status_label ?? '正常',
            });
            break;
          }
          case 'alert': {
            const a = data.data ?? data;
            setAlert({ level: a.level ?? data.level ?? 'amber', message: a.message ?? a.title ?? '', timestamp: a.timestamp ?? new Date().toISOString() });
            break;
          }
          case 'decision_ready': {
            const d = data.data;
            setDecision({
              suggestion: d.summary ?? d.suggestion ?? '', diagnosis: d.diagnosis ?? '',
              actions: d.actions ?? [], risk_level: d.risk_level ?? 1,
              auxiliary: {
                feed_ratio: d.feeding?.total_ratio?.toString() ?? d.auxiliary?.feed_ratio ?? '',
                disease_risk: d.disease?.risk ?? d.auxiliary?.disease_risk ?? '',
                harvest_timing: d.harvest?.recommended ? '建议捕捞' : d.auxiliary?.harvest_timing ?? '继续养殖',
              },
            });
            break;
          }
          case 'feishu_sent':
            setFeishuSent(true);
            setTimeout(() => setFeishuSent(false), 5000);
            break;
        }
      };

      return () => { socket.close(); };
    } catch {
      startMockTicks();
    }

    return () => {
      if (mockIntervalRef.current) clearInterval(mockIntervalRef.current);
    };
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // speed 变化时更新 mock interval
  useEffect(() => {
    if (mockMode && mockIntervalRef.current) {
      clearInterval(mockIntervalRef.current);
      mockIntervalRef.current = setInterval(() => {
        dayRef.current += speed >= 100 ? 1 : 0;
        const { sensor, wqar } = mockTick(dayRef.current);
        setSensorData(sensor);
        setWqarData(wqar);
      }, 2000 / speed);
    }
  }, [speed, mockMode]);

  const triggerScenario = useCallback((scenario: Scenario) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'trigger', scenario, push_feishu: true }));
      return;
    }

    // Mock 模式：本地模拟场景
    if (scenario === 'reset') {
      setAlert(null);
      setDecision(null);
      return;
    }
    const mock = MOCK_SCENARIOS[scenario];
    if (!mock) return;

    // 更新传感器
    setSensorData(prev => prev ? { ...prev, ...mock.sensorPatch } as SensorData : prev);

    // 模拟告警
    setAlert(mock.alert);

    // 模拟 AI 决策延迟
    setTimeout(() => {
      setDecision(mock.decision);
      // 模拟飞书推送
      setTimeout(() => {
        setFeishuSent(true);
        setTimeout(() => setFeishuSent(false), 5000);
      }, 800);
    }, 1500);
  }, []);

  const changeSpeed = useCallback((multiplier: number) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_speed', multiplier }));
    }
    setSpeed(multiplier);
  }, []);

  return { sensorData, wqarData, alert, decision, feishuSent, speed, triggerScenario, changeSpeed };
}
