import type { IndicatorData } from '../types/api';

interface MetricCardProps {
  name: string;
  label: string;
  unit: string;
  indicator: IndicatorData;
}

const STATUS_COLORS: Record<string, { border: string; text: string; bg: string }> = {
  optimal: { border: 'border-emerald-400', text: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  normal: { border: 'border-cyan-400', text: 'text-cyan-400', bg: 'bg-cyan-400/10' },
  caution: { border: 'border-yellow-400', text: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  warning: { border: 'border-orange-400', text: 'text-orange-400', bg: 'bg-orange-400/10' },
  danger: { border: 'border-red-400', text: 'text-red-400', bg: 'bg-red-400/10' },
};

const METRIC_LABELS: Record<string, string> = {
  temp: '水温',
  DO: '溶解氧',
  pH: 'pH值',
  ammonia: '氨氮',
};

export default function MetricCard({ name, label, unit, indicator }: MetricCardProps) {
  const colors = STATUS_COLORS[indicator.status] || STATUS_COLORS.normal;

  return (
    <div className={`liquid-glass rounded-2xl p-4 border-t-2 ${colors.border}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-white/50 font-medium">
          {METRIC_LABELS[name] || label}
        </span>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full ${colors.text} ${colors.bg}`}
        >
          {indicator.label}
        </span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="font-mono text-2xl font-bold tracking-tight">
          {indicator.value.toFixed(name === 'pH' ? 1 : name === 'ammonia' ? 2 : 1)}
        </span>
        <span className="text-xs text-white/30">{unit}</span>
      </div>
    </div>
  );
}
