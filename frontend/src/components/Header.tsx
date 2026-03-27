import { Timer, Zap, AlertTriangle } from 'lucide-react';

interface HeaderProps {
  day: number;
  speed: number;
  onSpeedChange: (speed: number) => void;
  onTriggerAlert: () => void;
  price: number;
}

const SPEEDS = [1, 10, 100];

export default function Header({
  day,
  speed,
  onSpeedChange,
  onTriggerAlert,
  price,
}: HeaderProps) {
  const timeOfDay = (() => {
    const hour = (day * 24) % 24;
    if (hour < 6) return '凌晨';
    if (hour < 12) return '上午';
    if (hour < 18) return '下午';
    return '晚间';
  })();

  return (
    <header className="h-16 flex items-center justify-between px-6 liquid-glass border-b border-white/10 z-50 relative">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <span className="text-2xl">🦐</span>
        <div className="flex items-center gap-2">
          <span className="font-heading italic text-xl">虾塘大亨</span>
          <span className="font-body text-[10px] tracking-[0.2em] text-white/40 uppercase">
            AI Aquaculture Decision System
          </span>
        </div>
        <div className="liquid-glass rounded-full px-3 py-1 ml-2">
          <span className="text-[11px] font-body text-white/60">
            赛道二 · AI合伙人
          </span>
        </div>
      </div>

      {/* Day & Speed */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Timer size={14} className="text-white/40" />
          <span className="font-mono text-lg font-bold">D{day}</span>
          <span className="text-xs text-white/40">{timeOfDay}</span>
        </div>
        <div className="flex gap-1">
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              className={`px-2 py-0.5 rounded-full text-xs font-mono transition-all ${
                speed === s
                  ? 'bg-white/15 text-white'
                  : 'text-white/40 hover:text-white/60'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Alert trigger & Price */}
      <div className="flex items-center gap-4">
        <button
          onClick={onTriggerAlert}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-red-500/50 text-red-400 text-xs font-medium hover:bg-red-500/10 transition-all animate-pulse-alert"
        >
          <AlertTriangle size={12} />
          <span>触发告警</span>
        </button>
        <div className="flex items-center gap-1">
          <Zap size={12} className="text-emerald-400" />
          <span className="font-mono text-sm text-emerald-400">
            ¥{price.toFixed(1)}
          </span>
          <span className="text-[10px] text-white/30">/kg</span>
        </div>
      </div>
    </header>
  );
}
