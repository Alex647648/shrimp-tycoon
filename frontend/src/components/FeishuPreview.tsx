
import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Shrimp, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface FeishuPreviewProps {
  visible: boolean;
}

import { Send, Activity, ShieldCheck } from 'lucide-react';

export const FeishuPreview: React.FC<FeishuPreviewProps> = ({ visible }) => {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="w-full"
        >
          <div className="liquid-glass p-6 rounded-[2rem] shadow-lg overflow-hidden border border-slate-100 bg-white group">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-100 group-hover:border-highlight/20 transition-all">
                <Send size={20} className="text-slate-400 group-hover:text-highlight transition-colors" />
              </div>
              <div>
                <div className="text-[10px] text-slate-900 uppercase font-black tracking-[0.2em]">外部上行链路协议</div>
                <div className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">飞书通知推送 // 实时同步</div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 group-hover:bg-white transition-all">
                <div className="text-[9px] text-slate-400 font-black uppercase mb-1.5 tracking-widest">目标频道</div>
                <div className="text-xs font-black text-slate-900 tracking-tight">MANAGEMENT_CHANNEL_01</div>
              </div>
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 group-hover:bg-white transition-all">
                <div className="text-[9px] text-slate-400 font-black uppercase mb-1.5 tracking-widest">发送状态</div>
                <div className="text-xs font-black text-highlight tracking-tight">已成功送达 // 协议已确认</div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-50 flex items-center justify-between">
              <span className="text-[9px] font-bold text-slate-300 tracking-widest uppercase">ID: FS-8829-X</span>
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-highlight animate-pulse" />
                <span className="text-[9px] font-black text-highlight tracking-widest uppercase">链路激活</span>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
