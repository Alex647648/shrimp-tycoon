export interface SensorData {
  temp: number;
  do: number;       // 后端发 DO，映射为 do
  ph: number;       // 后端发 pH，映射为 ph
  ammonia: number;  // 氨氮（替代盐度）
  timestamp: string;
  day: number;
  avg_weight: number;
  count: number;
  dead_shrimp: boolean;
  molt_peak: boolean;
}

export interface WQARData {
  risk_level: number;
  csi_score: number;
  status_label: string;
}

export interface ShrimpData {
  count: number;
  survival_rate: number;
  avg_weight: number;
  target_weight_diff: number;
  growth_progress: number;
}

export interface DecisionReport {
  suggestion: string;
  diagnosis: string;
  actions: string[];
  risk_level: number;
  auxiliary: {
    feed_ratio: string;
    disease_risk: string;
    harvest_timing: string;
  };
}

export interface AlertEvent {
  level: 'red' | 'amber' | 'green';
  message: string;
  timestamp: string;
}

export interface ROIData {
  revenue_prediction: number;
  roi_ratio: number;
  saas_fee: number;
  avoided_loss: number;
}

export interface MarketData {
  current_price: number;
  trend: 'up' | 'down' | 'stable';
}

export type Scenario = 'do_drop' | 'wssv' | 'storm' | 'molt' | 'harvest' | 'reset';
