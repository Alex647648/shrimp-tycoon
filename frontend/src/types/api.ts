export interface SensorData {
  schema: 'SDP-1.0';
  pond_id: string;
  timestamp: string;
  temp: number;
  DO: number;
  pH: number;
  ammonia: number;
  transparency: number;
  avg_weight: number;
  count: number;
  day: number;
  dead_shrimp: boolean;
  molt_peak: boolean;
}

export interface IndicatorData {
  value: number;
  status: 'optimal' | 'normal' | 'caution' | 'warning' | 'danger';
  label: string;
}

export interface WQARData {
  schema: 'WQAR-1.0';
  csi: number;
  risk_level: number;
  risk_label: string;
  indicators: Record<string, IndicatorData>;
  trigger_llm: boolean;
}

export interface FeedingData {
  total_ratio: number;
  morning: unknown;
  evening: unknown;
  skip: boolean;
}

export interface DiseaseData {
  risk: string;
  diseases: string[];
  herb_formula: string | null;
  alert: boolean;
}

export interface HarvestData {
  recommended: boolean;
  days_to_target: number;
  current_price: number;
  price_trend: string;
  expected_revenue: number;
}

export interface DecisionReport {
  schema: 'DECISION-1.0';
  risk_level: number;
  risk_label: string;
  model_used: string;
  latency_ms: number;
  confidence: number;
  summary: string;
  actions: string[];
  feeding: FeedingData;
  disease: DiseaseData;
  harvest: HarvestData;
  feishu_sent: boolean;
  feishu_message_id: string | null;
}

export interface AlertEvent {
  scenario: string;
  title: string;
  message: string;
  actions: string[];
}

export type AlertLevel = 'red' | 'amber' | 'green';

export interface ROIData {
  total_value: number;
  roi_multiple: number;
  survival_count: number;
  avg_weight: number;
  total_kg: number;
  market_price: number;
  saas_monthly_fee: number;
  disease_savings: number;
}

export type WSMessage =
  | { type: 'tick'; sensor: SensorData; wqar: WQARData }
  | { type: 'alert'; level: AlertLevel; data: AlertEvent }
  | { type: 'decision_ready'; data: DecisionReport }
  | { type: 'feishu_sent'; message_id: string; level: string };
