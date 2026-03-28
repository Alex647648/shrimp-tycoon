
import React from 'react';
import { ROIData } from '../types';
import { Coins } from 'lucide-react';

interface ROICardProps {
  data: ROIData | null;
}

export const ROICard: React.FC<ROICardProps> = ({ data }) => {
  if (!data) return null;

  return (
    <div className="liquid-glass p-10 rounded-[2rem] space-y-10 border border-slate-100 bg-white group">
      <div className="flex items-center gap-5">
        <div className="w-12 h-12 rounded-2xl bg-slate-50 flex items-center justify-center border border-slate-100 group-hover:border-highlight/20 transition-all">
          <Coins size={24} className="text-slate-400 group-hover:text-highlight transition-colors" />
        </div>
        <div>
          <h3 className="text-[11px] font-black text-slate-900 uppercase tracking-[0.3em]">经济效益展望协议</h3>
          <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest mt-1">ROI: {data.roi_ratio.toFixed(1)}× // 预测模型</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-12">
        <div className="space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">预计总营收</div>
          <div className="text-4xl font-black text-slate-900 tracking-tighter">
            ¥{data.revenue_prediction.toLocaleString()}
          </div>
        </div>
        <div className="text-right space-y-2">
          <div className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">投资回报倍数</div>
          <div className="text-4xl font-black text-highlight tracking-tighter">
            {data.roi_ratio.toFixed(1)}×
          </div>
        </div>
      </div>

      <div className="space-y-6 pt-10 border-t border-slate-50">
        <div className="flex justify-between items-center bg-slate-50 p-6 rounded-2xl border border-slate-100">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">系统服务月费</span>
            <span className="text-sm font-black text-slate-900">¥{data.saas_fee.toLocaleString()}</span>
          </div>
          <div className="text-right flex flex-col">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-1">风险减损预估</span>
            <span className="text-sm font-black text-highlight">≈ ¥{data.avoided_loss.toLocaleString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
