import { useState, useCallback } from 'react';
import type {
  SensorData,
  WQARData,
  DecisionReport,
  AlertEvent,
  AlertLevel,
  WSMessage,
} from '../types/api';

const MOCK_SENSOR: SensorData = {
  schema: 'SDP-1.0',
  pond_id: 'POND-001',
  timestamp: new Date().toISOString(),
  temp: 25.4,
  DO: 6.2,
  pH: 7.8,
  ammonia: 0.16,
  transparency: 35,
  avg_weight: 28.5,
  count: 485,
  day: 45,
  dead_shrimp: false,
  molt_peak: false,
};

const MOCK_WQAR: WQARData = {
  schema: 'WQAR-1.0',
  csi: 18,
  risk_level: 1,
  risk_label: '正常运营',
  trigger_llm: false,
  indicators: {
    temp: { value: 25.4, status: 'optimal', label: '最适范围' },
    DO: { value: 6.2, status: 'normal', label: '正常' },
    pH: { value: 7.8, status: 'optimal', label: '最佳范围' },
    ammonia: { value: 0.16, status: 'caution', label: '接近警戒' },
  },
};

export interface ShrimpState {
  sensor: SensorData;
  wqar: WQARData;
  decision: DecisionReport | null;
  alert: { level: AlertLevel; data: AlertEvent } | null;
  feishuSent: boolean;
  speed: number;
}

export function useShrimpData() {
  const [state, setState] = useState<ShrimpState>({
    sensor: MOCK_SENSOR,
    wqar: MOCK_WQAR,
    decision: null,
    alert: null,
    feishuSent: false,
    speed: 1,
  });

  const handleMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case 'tick':
        setState((prev) => ({
          ...prev,
          sensor: msg.sensor,
          wqar: msg.wqar,
        }));
        break;
      case 'alert':
        setState((prev) => ({
          ...prev,
          alert: { level: msg.level, data: msg.data },
        }));
        break;
      case 'decision_ready':
        setState((prev) => ({
          ...prev,
          decision: msg.data,
          alert: null,
        }));
        break;
      case 'feishu_sent':
        setState((prev) => ({
          ...prev,
          feishuSent: true,
        }));
        break;
    }
  }, []);

  const setSpeed = useCallback((speed: number) => {
    setState((prev) => ({ ...prev, speed }));
  }, []);

  const clearAlert = useCallback(() => {
    setState((prev) => ({ ...prev, alert: null }));
  }, []);

  const clearDecision = useCallback(() => {
    setState((prev) => ({ ...prev, decision: null, feishuSent: false }));
  }, []);

  return { state, handleMessage, setSpeed, clearAlert, clearDecision };
}
