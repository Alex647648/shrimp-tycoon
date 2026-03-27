import type { SensorData, WQARData } from '../types/api';

interface ShrimpStatusProps {
  sensor: SensorData;
  wqar: WQARData;
}

const TARGET_WEIGHT = 40; // grams, market size

export default function ShrimpStatus({ sensor, wqar }: ShrimpStatusProps) {
  const survivalRate = ((sensor.count / 500) * 100).toFixed(1);
  const growthProgress = Math.min((sensor.avg_weight / TARGET_WEIGHT) * 100, 100);
  const csiPercent = Math.min(wqar.csi, 100);

  return (
    <div className="liquid-glass rounded-2xl p-4 space-y-3">
      <h3 className="text-xs text-white/50 font-medium tracking-wider uppercase">
        虾群状态
      </h3>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-white/40 text-xs">存活数量</span>
          <p className="font-mono font-bold">{sensor.count} 尾</p>
        </div>
        <div>
          <span className="text-white/40 text-xs">存活率</span>
          <p className="font-mono font-bold">{survivalRate}%</p>
        </div>
        <div>
          <span className="text-white/40 text-xs">均重</span>
          <p className="font-mono font-bold">{sensor.avg_weight.toFixed(1)}g</p>
        </div>
        <div>
          <span className="text-white/40 text-xs">距上市规格</span>
          <p className="font-mono font-bold">
            {(TARGET_WEIGHT - sensor.avg_weight).toFixed(1)}g
          </p>
        </div>
      </div>

      {/* Growth progress */}
      <div>
        <div className="flex justify-between text-[10px] text-white/40 mb-1">
          <span>生长进度</span>
          <span>{growthProgress.toFixed(0)}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <div
            className="h-full rounded-full relative"
            style={{
              width: `${growthProgress}%`,
              background: 'linear-gradient(90deg, #06b6d4, #10b981)',
            }}
          >
            <div className="absolute right-0 top-0 w-2 h-full bg-white/40 rounded-full blur-sm" />
          </div>
        </div>
      </div>

      {/* CSI score */}
      <div>
        <div className="flex justify-between text-[10px] text-white/40 mb-1">
          <span>CSI 水质综合评分</span>
          <span>{wqar.csi}</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <div
            className="h-full rounded-full relative"
            style={{
              width: `${csiPercent}%`,
              background:
                wqar.risk_level <= 2
                  ? 'linear-gradient(90deg, #10b981, #06b6d4)'
                  : wqar.risk_level <= 3
                    ? 'linear-gradient(90deg, #f59e0b, #eab308)'
                    : 'linear-gradient(90deg, #ef4444, #f97316)',
            }}
          >
            <div className="absolute right-0 top-0 w-2 h-full bg-white/40 rounded-full blur-sm" />
          </div>
        </div>
      </div>
    </div>
  );
}
