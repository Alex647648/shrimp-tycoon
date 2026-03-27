import { TrendingUp } from 'lucide-react';
import type { SensorData } from '../types/api';

interface ROICardProps {
  sensor: SensorData;
  price: number;
}

export default function ROICard({ sensor, price }: ROICardProps) {
  const totalKg = (sensor.count * sensor.avg_weight) / 1000;
  const totalValue = totalKg * price;
  const saasFee = 299;
  const diseaseSaving = 12000;
  const roi = totalValue > 0 ? ((totalValue - saasFee) / saasFee).toFixed(1) : '0.0';

  return (
    <div className="liquid-glass rounded-2xl p-4 space-y-3">
      <div className="flex items-center gap-2">
        <TrendingUp size={14} className="text-emerald-400" />
        <h3 className="text-xs text-white/50 font-medium tracking-wider uppercase">
          ROI 收益预测
        </h3>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-mono text-3xl font-bold text-emerald-400 drop-shadow-[0_0_12px_rgba(16,185,129,0.3)]">
          ¥{totalValue.toFixed(0)}
        </span>
        <span className="text-xs text-white/30">总产值</span>
      </div>

      <div className="flex items-baseline gap-2">
        <span className="font-mono text-xl font-bold text-amber-400">
          {roi}x
        </span>
        <span className="text-xs text-white/30">ROI倍数</span>
      </div>

      <div className="space-y-1.5 text-xs text-white/40 pt-2 border-t border-white/5">
        <div className="flex justify-between">
          <span>存活量 × 均重</span>
          <span className="font-mono text-white/60">
            {sensor.count} × {sensor.avg_weight.toFixed(1)}g = {totalKg.toFixed(1)}kg
          </span>
        </div>
        <div className="flex justify-between">
          <span>市场价</span>
          <span className="font-mono text-white/60">¥{price.toFixed(1)}/kg</span>
        </div>
        <div className="flex justify-between">
          <span>SaaS月费</span>
          <span className="font-mono text-white/60">¥{saasFee}/月</span>
        </div>
        <div className="flex justify-between">
          <span>病害规避</span>
          <span className="font-mono text-emerald-400/60">+¥{diseaseSaving.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
