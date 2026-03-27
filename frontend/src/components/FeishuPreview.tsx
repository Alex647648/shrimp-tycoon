import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare } from 'lucide-react';
import type { AlertEvent, AlertLevel } from '../types/api';

interface FeishuPreviewProps {
  alert: { level: AlertLevel; data: AlertEvent } | null;
  feishuSent: boolean;
}

export default function FeishuPreview({ alert, feishuSent }: FeishuPreviewProps) {
  return (
    <AnimatePresence>
      {alert && feishuSent && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="rounded-2xl border border-blue-500/30 bg-blue-950/20 p-4 overflow-hidden"
        >
          <div className="flex items-center gap-2 mb-3">
            <MessageSquare size={14} className="text-blue-400" />
            <h3 className="text-xs text-blue-400 font-medium tracking-wider uppercase">
              飞书推送预览
            </h3>
          </div>

          <div className="bg-[#1a1f36] rounded-lg p-3 border-l-3 border-l-blue-500">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">
                {alert.level === 'red' ? '🔴' : alert.level === 'amber' ? '🟠' : '🟢'}
              </span>
              <span className="text-sm font-medium">{alert.data.title}</span>
            </div>
            <p className="text-xs text-white/60 mb-2">{alert.data.message}</p>
            {alert.data.actions.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] text-white/40">建议操作:</span>
                {alert.data.actions.map((action, i) => (
                  <p key={i} className="text-xs text-blue-300/70">
                    • {action}
                  </p>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
