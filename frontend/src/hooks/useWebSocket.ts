import { useState, useEffect, useCallback, useRef } from 'react';
import { SensorData, WQARData, AlertEvent, DecisionReport, Scenario } from '../types';

export function useWebSocket() {
  const [sensorData, setSensorData] = useState<SensorData | null>(null);
  const [wqarData, setWqarData] = useState<WQARData | null>(null);
  const [alert, setAlert] = useState<AlertEvent | null>(null);
  const [decision, setDecision] = useState<DecisionReport | null>(null);
  const [feishuSent, setFeishuSent] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1);
  
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8766/ws');
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'tick': {
          // 后端发 DO/pH/ammonia，前端用 do/ph/ammonia
          const raw = data.sensor;
          const sensor: SensorData = {
            temp: raw.temp,
            do: raw.DO ?? raw.do ?? 0,
            ph: raw.pH ?? raw.ph ?? 0,
            ammonia: raw.ammonia ?? 0,
            timestamp: raw.timestamp,
            day: raw.day,
            avg_weight: raw.avg_weight ?? 0,
            count: raw.count ?? 0,
            dead_shrimp: raw.dead_shrimp ?? false,
            molt_peak: raw.molt_peak ?? false,
          };
          setSensorData(sensor);

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
          setAlert({
            level: a.level ?? data.level ?? 'amber',
            message: a.message ?? a.title ?? '',
            timestamp: a.timestamp ?? new Date().toISOString(),
          });
          break;
        }
        case 'decision_ready': {
          const d = data.data;
          setDecision({
            suggestion: d.summary ?? d.suggestion ?? '',
            diagnosis: d.diagnosis ?? '',
            actions: d.actions ?? [],
            risk_level: d.risk_level ?? 1,
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

    return () => {
      socket.close();
    };
  }, []);

  const triggerScenario = useCallback((scenario: Scenario) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'trigger', scenario, push_feishu: true }));
    }
  }, []);

  const changeSpeed = useCallback((multiplier: number) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'set_speed', multiplier }));
      setSpeed(multiplier);
    }
  }, []);

  return {
    sensorData,
    wqarData,
    alert,
    decision,
    feishuSent,
    speed,
    triggerScenario,
    changeSpeed
  };
}
