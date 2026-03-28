import type { IndicatorData } from '../types/api';

interface MetricCardProps {
  name: string;
  label: string;
  unit: string;
  indicator: IndicatorData;
}

const STATUS_BAR_COLORS: Record<string, string> = {
  optimal: 'bg-emerald-400',
  normal:  'bg-cyan-400',
  caution: 'bg-yellow-400',
  warning: 'bg-orange-400',
  danger:  'bg-red-400',
};

const STATUS_TEXT_COLORS: Record<string, string> = {
  optimal: 'text-emerald-400',
  normal:  'text-cyan-400',
  caution: 'text-yellow-400',
  warning: 'text-orange-400',
  danger:  'text-red-400',
};

const METRIC_LABELS: Record<string, string> = {
  temp:    '水温',
  DO:      '溶解氧',
  pH:      'pH值',
  ammonia: '氨氮',
};

export default function MetricCard({ name, label, unit, indicator }: MetricCardProps) {
  const barColor  = STATUS_BAR_COLORS[indicator.status]  || STATUS_BAR_COLORS.normal;
  const textColor = STATUS_TEXT_COLORS[indicator.status] || STATUS_TEXT_COLORS.normal;

  return (
    <div className="liquid-glass rounded-2xl overflow-hidden flex">
      {/* Left status bar */}
      <div className={`w-1 flex-shrink-0 ${barColor}`} />

      {/* Content */}
      <div className="flex-1 p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-white/50 font-medium">
            {METRIC_LABELS[name] || label}
          </span>
          <span className={`text-[10px] font-semibold ${textColor}`}>
            {indicator.label}
          </span>
        </div>
        <div className="flex items-baseline gap-1">
          <span className={`font-mono text-3xl font-bold tracking-tight ${textColor}`}>
            {indicator.value.toFixed(name === 'pH' ? 1 : name === 'ammonia' ? 2 : 1)}
          </span>
          <span className="text-xs text-white/30">{unit}</span>
        </div>
      </div>
    </div>
  );
}
