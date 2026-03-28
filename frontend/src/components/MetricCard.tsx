
import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit: string;
  range: string;
  status: 'optimal' | 'normal' | 'caution' | 'warning' | 'danger';
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, unit, range, status }) => {
  const statusColor = {
    optimal: 'text-emerald-500',
    normal: 'text-sky-500',
    caution: 'text-amber-500',
    warning: 'text-orange-500',
    danger: 'text-rose-500'
  }[status];

  return (
    <div className="liquid-glass p-8 rounded-[2rem] group hover:bg-white/20 transition-all border border-white/20 hover:border-sky-400/50 bg-white/40 backdrop-blur-2xl shadow-[0_8px_32px_rgba(0,0,0,0.05)]">
      <div className="flex justify-between items-start mb-8">
        <span className="text-[10px] font-black text-slate-700 uppercase tracking-[0.3em] drop-shadow-sm">{label}</span>
        <div className={`w-2.5 h-2.5 rounded-full animate-pulse shadow-[0_0_10px_rgba(0,0,0,0.1)] ${statusColor.replace('text', 'bg')}`} />
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-5xl font-black tracking-tighter drop-shadow-[0_2px_4px_rgba(0,0,0,0.1)] ${statusColor}`}>{value}</span>
        <span className="text-xs font-bold text-slate-600 uppercase tracking-widest drop-shadow-sm">{unit}</span>
      </div>
      <div className="mt-8 pt-6 border-t border-slate-200/50 flex justify-between items-center">
        <span className="text-[9px] font-bold text-slate-600 uppercase tracking-widest drop-shadow-sm">参考范围: {range}</span>
        <div className="h-1 w-20 bg-slate-200/50 rounded-full overflow-hidden">
          <div className={`h-full ${statusColor.replace('text', 'bg')} opacity-60 shadow-[0_0_8px_rgba(0,0,0,0.05)]`} style={{ width: '65%' }} />
        </div>
      </div>
    </div>
  );
};
