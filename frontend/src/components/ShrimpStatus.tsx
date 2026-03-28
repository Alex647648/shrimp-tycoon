
import React from 'react';
import { ShrimpData } from '../types';

interface ShrimpStatusProps {
  data: ShrimpData | null;
  csiScore: number;
}

export const ShrimpStatus: React.FC<ShrimpStatusProps> = ({ data, csiScore }) => {
  if (!data) return null;

  return (
    <div className="liquid-glass p-10 rounded-[2rem] space-y-10 border border-slate-100 bg-white group">
      <div className="flex items-center justify-between">
        <h3 className="text-[11px] font-black text-slate-900 uppercase tracking-[0.3em]">生物资产状态协议</h3>
        <div className="flex items-center gap-4">
          <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">健康指数 (CSI)</span>
          <span className={`text-2xl font-black ${csiScore > 80 ? 'text-highlight' : 'text-orange-500'}`}>{csiScore}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-12 gap-y-10">
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">种群数量估算</div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-slate-900 tracking-tighter">{data.count}</span>
            <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">尾</span>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">当前成活率</div>
          <div className="text-4xl font-black text-highlight tracking-tighter">{data.survival_rate}%</div>
        </div>
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">平均单体重量</div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-slate-900 tracking-tighter">{data.avg_weight}</span>
            <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">G</span>
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">距收获目标</div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-black text-slate-900 tracking-tighter">{data.target_weight_diff}</span>
            <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">G</span>
          </div>
        </div>
      </div>

      <div className="space-y-6 pt-10 border-t border-slate-50">
        <div>
          <div className="flex justify-between text-[10px] font-bold mb-4">
            <span className="text-slate-400 uppercase tracking-widest">生长周期进度</span>
            <span className="text-slate-900 font-black">{data.growth_progress}%</span>
          </div>
          <div className="h-2 bg-slate-50 rounded-full overflow-hidden relative border border-slate-100">
            <div 
              className="h-full bg-highlight transition-all duration-1000 ease-out" 
              style={{ width: `${data.growth_progress}%` }} 
            />
          </div>
        </div>
      </div>
    </div>
  );
};
