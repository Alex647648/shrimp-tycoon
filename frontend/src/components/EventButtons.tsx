interface EventButtonsProps {
  onTrigger: (scenario: string) => void;
}

const SCENARIOS = [
  { id: 'do_drop', emoji: '🫧', label: '凌晨DO骤降', color: 'border-red-500/30 hover:bg-red-500/10' },
  { id: 'wssv', emoji: '🦠', label: '白斑病毒预警', color: 'border-red-500/30 hover:bg-red-500/10' },
  { id: 'storm', emoji: '🌧️', label: '暴雨水质突变', color: 'border-orange-500/30 hover:bg-orange-500/10' },
  { id: 'molt', emoji: '🦐', label: '蜕壳高峰期', color: 'border-yellow-500/30 hover:bg-yellow-500/10' },
  { id: 'harvest', emoji: '🎣', label: '最佳捕捞时机', color: 'border-emerald-500/30 hover:bg-emerald-500/10' },
  { id: 'reset', emoji: '🔄', label: '重置仿真', color: 'border-white/20 hover:bg-white/5' },
];

export default function EventButtons({ onTrigger }: EventButtonsProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs text-white/50 font-medium tracking-wider uppercase">
        演示事件
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => onTrigger(s.id)}
            className={`liquid-glass rounded-xl p-3 text-left border ${s.color} transition-all group`}
          >
            <span className="text-lg block mb-1 group-hover:scale-110 transition-transform inline-block">
              {s.emoji}
            </span>
            <span className="text-xs text-white/70 block">{s.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
