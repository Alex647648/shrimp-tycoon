import { Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { DecisionReport } from '../types/api';

interface AIDecisionProps {
  decision: DecisionReport | null;
}

const RISK_COLORS: Record<number, { bg: string; text: string; label: string }> = {
  1: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', label: '低风险' },
  2: { bg: 'bg-cyan-500/15', text: 'text-cyan-400', label: '轻微风险' },
  3: { bg: 'bg-yellow-500/15', text: 'text-yellow-400', label: '中等风险' },
  4: { bg: 'bg-orange-500/15', text: 'text-orange-400', label: '高风险' },
  5: { bg: 'bg-red-500/15', text: 'text-red-400', label: '极高风险' },
};

export default function AIDecision({ decision }: AIDecisionProps) {
  if (!decision) {
    return (
      <div className="liquid-glass-strong rounded-2xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain size={14} className="text-white/40" />
          <h3 className="text-xs text-white/50 font-medium tracking-wider uppercase">
            AI 决策建议
          </h3>
        </div>
        <p className="text-sm text-white/30 italic">等待数据分析...</p>
      </div>
    );
  }

  const risk = RISK_COLORS[decision.risk_level] || RISK_COLORS[3];

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={decision.summary}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="liquid-glass-strong rounded-2xl p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Brain size={14} className="text-cyan-400" />
            <h3 className="text-xs text-white/50 font-medium tracking-wider uppercase">
              AI 决策建议
            </h3>
          </div>
          <span className={`text-[10px] px-2 py-0.5 rounded-full ${risk.bg} ${risk.text}`}>
            {risk.label}
          </span>
        </div>

        <p className="font-heading italic text-sm text-white/80 mb-3 leading-relaxed">
          {decision.summary}
        </p>

        <div className="space-y-1.5">
          {decision.actions.slice(0, 3).map((action, i) => (
            <div key={i} className="flex gap-2 text-xs text-white/60">
              <span className="text-cyan-400 font-mono shrink-0">{i + 1}.</span>
              <span>{action}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/5 text-[10px] text-white/30">
          <span>{decision.model_used}</span>
          <span>{decision.latency_ms}ms</span>
          <span>置信度 {(decision.confidence * 100).toFixed(0)}%</span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
