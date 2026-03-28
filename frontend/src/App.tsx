/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { Shrimp, Zap, AlertCircle, Menu, Settings, Bell, Twitter, Linkedin, Instagram } from 'lucide-react';
import { motion } from 'motion/react';
import { useWebSocket } from './hooks/useWebSocket';
import { MarketData, ShrimpData, ROIData } from './types';
import { PondCanvas } from './components/PondCanvas';
import { AIDecision } from './components/AIDecision';
import { MetricCard } from './components/MetricCard';
import { ShrimpStatus } from './components/ShrimpStatus';
import { ROICard } from './components/ROICard';
import { EventButtons } from './components/EventButtons';
import { FeishuPreview } from './components/FeishuPreview';

export default function App() {
  const {
    sensorData,
    wqarData,
    alert,
    decision,
    feishuSent,
    speed,
    triggerScenario,
    changeSpeed
  } = useWebSocket();

  const [market] = useState<MarketData>({ current_price: 26.7, trend: 'stable' });
  const [shrimp] = useState<ShrimpData>({
    count: 485,
    survival_rate: 97.0,
    avg_weight: 28.5,
    target_weight_diff: 11.5,
    growth_progress: 71
  });
  const [roi] = useState<ROIData>({
    revenue_prediction: 34600,
    roi_ratio: 2.5,
    saas_fee: 2000,
    avoided_loss: 8000
  });

  return (
    <main className="h-screen w-screen flex flex-col overflow-hidden relative atmosphere grid-pattern">
      {/* Simplified Background */}
      <div className="paper-texture" />
      <div className="water-surface absolute inset-0 bg-gradient-to-br from-sky-300/40 via-blue-200/20 to-sky-400/30 pointer-events-none z-[-3]" />

      {/* Top Header Bar - Premium Editorial */}
      <header className="relative z-50 flex items-center justify-between px-16 py-10 shrink-0 border-b border-white/10 bg-white/20 backdrop-blur-md">
        <div className="flex items-center gap-12">
          <div className="flex flex-col">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-2 h-2 rounded-full bg-highlight animate-pulse" />
              <span className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">
                Bloom AI // 实时生态协议
              </span>
            </div>
            <h1 className="editorial-heading text-6xl tracking-tighter">
              虾塘大亨<span className="text-highlight">.</span>
            </h1>
          </div>
          
          <div className="h-16 w-px bg-slate-100" />
          
          <div className="flex items-center gap-10">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">市场基准</span>
              <span className="text-2xl font-black text-slate-900">¥{market.current_price.toFixed(1)}<span className="text-xs text-slate-400 ml-1">/KG</span></span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">模拟速率</span>
              <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-full border border-slate-100">
                {[1, 10, 100].map((s) => (
                  <button
                    key={s}
                    onClick={() => changeSpeed(s)}
                    className={`px-4 py-1 rounded-full text-[9px] font-black transition-all ${
                      speed === s ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'text-slate-400 hover:text-slate-600'
                    }`}
                  >
                    {s}X
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <button className="pill-button">
            生成分析报告
          </button>
          <div className="flex items-center gap-4 pl-6 border-l border-slate-100">
            <div className="text-right">
              <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">系统管理员</div>
              <div className="text-xs font-bold text-slate-900">JD_ADMIN</div>
            </div>
            <div className="w-12 h-12 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center text-sm font-black text-slate-900">
              JD
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Split Layout */}
      <div className="flex-1 flex gap-12 px-16 pb-12 min-h-0 relative z-10">
        
        {/* Middle Section: Immersive Visualizer + AI Decision */}
        <section className="flex-[2] flex flex-col gap-8 overflow-y-auto no-scrollbar pb-20">
          
          {/* Shrimp Pond Card - Restored to a more prominent size */}
          <div className="relative liquid-glass-strong overflow-hidden h-[480px] shrink-0 group">
            <div className="absolute top-8 left-8 z-20">
              <div className="px-5 py-2 rounded-full bg-white/80 backdrop-blur-xl border border-slate-100 flex items-center gap-3 shadow-sm">
                <div className="w-2 h-2 rounded-full bg-highlight animate-pulse" />
                <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-900">实时视觉流监控</span>
              </div>
            </div>

            <div className="absolute inset-0 z-0">
              <PondCanvas riskLevel={wqarData?.risk_level || 1} />
            </div>

            {/* Day Counter */}
            <div className="absolute bottom-8 left-8 z-20 flex flex-col pointer-events-none">
              <span className="text-[10px] text-slate-500 uppercase tracking-[0.4em] font-black mb-1">养殖周期进度</span>
              <div className="editorial-heading text-8xl text-slate-900 tracking-tighter relative">
                <span className="text-highlight/10 absolute -left-4 -top-6 select-none text-9xl">#</span>
                <span className="relative">{sensorData?.day || 42}</span>
              </div>
            </div>

            {/* Alert and Controls */}
            <div className="absolute bottom-8 right-8 z-30 flex flex-col items-end gap-4 max-w-md">
              {alert && alert.level !== 'green' && (
                <motion.div 
                  initial={{ x: 50, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  className={`px-6 py-3 rounded-2xl border bg-white shadow-xl flex items-center gap-4 ${
                    alert.level === 'red' ? 'border-alarm-red/20 text-alarm-red' : 'border-orange-500/20 text-orange-500'
                  }`}
                >
                  <AlertCircle size={20} className="animate-pulse" />
                  <div className="text-left">
                    <div className="text-[8px] uppercase font-black tracking-[0.3em] opacity-40 mb-0.5">系统预警</div>
                    <div className="text-sm font-black tracking-tight uppercase">{alert.message}</div>
                  </div>
                </motion.div>
              )}
              
              <div className="glass-card p-6 flex flex-col gap-4 w-full bg-white/90 backdrop-blur-xl">
                <div className="flex justify-between items-center">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">环境干预协议 // 控制单元</span>
                </div>
                <EventButtons onTrigger={triggerScenario} />
              </div>
            </div>
          </div>

          {/* AI Decision - Full width in the middle section */}
          <div className="shrink-0">
            <AIDecision decision={decision} />
          </div>
        </section>

        {/* Right Sidebar: Numerical Data Display */}
        <section className="flex-1 flex flex-col gap-8 overflow-y-auto no-scrollbar pr-2 min-w-[400px] pb-20">
          <div className="grid grid-cols-2 gap-6 shrink-0">
            <MetricCard 
              label="水温" 
              value={sensorData?.temp || 25.6} 
              unit="°C" 
              range="24-28" 
              status="normal" 
            />
            <MetricCard 
              label="溶解氧" 
              value={sensorData?.do || 6.2} 
              unit="mg/L" 
              range=">5.0" 
              status={sensorData?.do && sensorData.do < 3 ? 'danger' : 'optimal'} 
            />
            <MetricCard 
              label="pH 值" 
              value={sensorData?.ph || 8.1} 
              unit="ph" 
              range="7.5-8.5" 
              status="optimal" 
            />
            <MetricCard 
              label="氨氮" 
              value={sensorData?.ammonia || 0.17} 
              unit="mg/L" 
              range="<0.5" 
              status={sensorData?.ammonia && sensorData.ammonia > 0.3 ? 'danger' : 'normal'} 
            />
          </div>

          <div className="space-y-8 shrink-0">
            <ShrimpStatus data={shrimp} csiScore={wqarData?.csi_score || 18} />
            <ROICard data={roi} />
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="px-16 py-8 flex justify-between items-center border-t border-white/20 bg-white/30 backdrop-blur-xl shrink-0 relative z-50">
        <div className="flex items-center gap-12">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
              最后同步: 2024.03.21 14:30
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 rounded-full bg-slate-200" />
            <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
              加密节点: SH-082
            </span>
          </div>
        </div>
        <span className="text-[9px] font-black text-slate-900 uppercase tracking-[0.3em]">
          Bloom AI Engine v4.2 // 全自主养殖协议
        </span>
      </footer>
    </main>
  );
}
