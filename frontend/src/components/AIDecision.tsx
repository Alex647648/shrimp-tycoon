
import React from 'react';
import { DecisionReport } from '../types';
import { motion, AnimatePresence } from 'motion/react';
import { Cpu } from 'lucide-react';

interface AIDecisionProps {
  decision: DecisionReport | null;
}

export const AIDecision: React.FC<AIDecisionProps> = ({ decision }) => {
  if (!decision) return (
    <div className="liquid-glass p-6 rounded-[2rem] min-h-[240px] flex items-center justify-center border border-slate-100 bg-white">
      <p className="text-slate-300 text-[9px] animate-pulse font-black tracking-[0.3em] uppercase">AI 智能分析引擎初始化中...</p>
    </div>
  );

  return (
    <div className="liquid-glass p-6 space-y-6 h-full flex flex-col group">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-100 group-hover:border-highlight/20 transition-all">
            <Cpu size={20} className="text-slate-400 group-hover:text-highlight transition-colors" />
          </div>
          <div>
            <h3 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.2em]">AI 智能决策协议</h3>
            <p className="text-[8px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">Bloom Engine v4.2</p>
          </div>
        </div>
        <div className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.1em] border shadow-sm ${
          decision.risk_level >= 4 ? 'bg-white border-alarm-red/20 text-alarm-red' : 'bg-white border-highlight/20 text-highlight'
        }`}>
          风险 {decision.risk_level}
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto no-scrollbar">
        <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100 relative overflow-hidden group-hover:bg-white transition-all">
          <div className="absolute top-0 left-0 w-1 h-full bg-highlight/20" />
          <div className="text-[9px] text-slate-400 font-black uppercase tracking-widest mb-2">诊断结论与核心洞察</div>
          <p className="text-base text-slate-900 leading-tight tracking-tight font-black">{decision.diagnosis}</p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="w-1 h-1 rounded-full bg-highlight" />
            <span className="text-[9px] text-slate-400 font-black uppercase tracking-widest">建议执行操作</span>
          </div>
          <div className="space-y-3">
            {decision.actions.map((action, idx) => (
              <div key={idx} className="flex items-start gap-4 group/item">
                <div className="mt-0.5 w-5 h-5 rounded-lg bg-slate-50 flex items-center justify-center text-[9px] font-black text-slate-400 group-hover/item:bg-highlight group-hover/item:text-white transition-all border border-slate-100">
                  {idx + 1}
                </div>
                <span className="text-sm text-slate-600 group-hover/item:text-slate-900 transition-colors leading-tight font-medium">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 pt-6 border-t border-slate-100">
        <div className="flex flex-col">
          <div className="text-[9px] text-slate-300 font-black uppercase mb-2 tracking-widest">投喂策略</div>
          <div className="text-sm font-black text-slate-900">{decision.auxiliary_strategies?.feeding || decision.auxiliary?.feed_ratio}</div>
        </div>
        <div className="flex flex-col">
          <div className="text-[9px] text-slate-300 font-black uppercase mb-2 tracking-widest">病害风险</div>
          <div className="text-sm font-black text-slate-900">{decision.auxiliary_strategies?.disease_risk || decision.auxiliary?.disease_risk}</div>
        </div>
        <div className="flex flex-col">
          <div className="text-[9px] text-slate-300 font-black uppercase mb-2 tracking-widest">收获时机</div>
          <div className="text-sm font-black text-slate-900">{decision.auxiliary_strategies?.harvest_timing || decision.auxiliary?.harvest_timing}</div>
        </div>
      </div>
    </div>
  );
};
