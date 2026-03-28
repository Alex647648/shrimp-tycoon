
import React from 'react';
import { Scenario } from '../types';
import { motion } from 'motion/react';

interface EventButtonsProps {
  onTrigger: (scenario: Scenario) => void;
}

import { Activity, Wind, Thermometer, AlertTriangle, Zap, RotateCcw } from 'lucide-react';

export const EventButtons: React.FC<EventButtonsProps> = ({ onTrigger }) => {
  const events: { label: string; icon: React.ReactNode; scenario: Scenario; color: string }[] = [
    { label: '低氧预警', icon: <Wind size={16} />, scenario: 'do_drop', color: 'text-orange-600' },
    { label: '病毒入侵', icon: <AlertTriangle size={16} />, scenario: 'wssv', color: 'text-alarm-red' },
    { label: '极端天气', icon: <Activity size={16} />, scenario: 'storm', color: 'text-orange-600' },
    { label: '脱壳监测', icon: <Zap size={16} />, scenario: 'molt', color: 'text-emerald-600' },
    { label: '收获模拟', icon: <Zap size={16} />, scenario: 'harvest', color: 'text-highlight' },
    { label: '系统重置', icon: <RotateCcw size={16} />, scenario: 'reset', color: 'text-slate-400' },
  ];

  return (
    <div className="flex items-center gap-5 overflow-x-auto pb-4 no-scrollbar">
      {events.map((e) => (
        <button
          key={e.scenario}
          onClick={() => onTrigger(e.scenario)}
          className="group flex items-center gap-4 px-8 py-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-highlight/30 hover:bg-white hover:shadow-xl transition-all active:scale-95 shrink-0"
        >
          <span className={`${e.color} group-hover:scale-125 transition-transform duration-500`}>{e.icon}</span>
          <span className="text-[11px] font-black text-slate-400 group-hover:text-slate-900 uppercase tracking-[0.3em] transition-colors">
            {e.label}
          </span>
        </button>
      ))}
    </div>
  );
};
