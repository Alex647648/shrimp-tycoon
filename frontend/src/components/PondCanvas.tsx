import React, { useEffect, useRef } from 'react';

interface PondCanvasProps {
  riskLevel: number;
}

export const PondCanvas: React.FC<PondCanvasProps> = ({ riskLevel }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;
    
    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    window.addEventListener('resize', resize);
    resize();

    const w = canvas.width / window.devicePixelRatio;
    const h = canvas.height / window.devicePixelRatio;

    // --- Particle Systems ---
    
    // 1. Shrimp (Organic Movement)
    const shrimpCount = 45;
    const shrimp = Array.from({ length: shrimpCount }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      angle: Math.random() * Math.PI * 2,
      speed: 0.2 + Math.random() * 0.5,
      size: 4 + Math.random() * 6,
      turnSpeed: (Math.random() - 0.5) * 0.02,
      opacity: 0.1 + Math.random() * 0.4,
      z: Math.random() // Depth factor
    }));

    // 2. Marine Snow (Micro-debris)
    const snowCount = 120;
    const snow = Array.from({ length: snowCount }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.1,
      vy: 0.05 + Math.random() * 0.15,
      size: 0.5 + Math.random() * 1.5,
      opacity: Math.random() * 0.3
    }));

    const render = () => {
      time += 0.005;
      const displayW = canvas.width / window.devicePixelRatio;
      const displayH = canvas.height / window.devicePixelRatio;

      // --- 1. Volumetric Background ---
      let baseHue = 185; // Turquoise/Cyan
      let saturation = 40;
      let lightness = 85;

      if (riskLevel >= 4) {
        baseHue = 0; // Red
        saturation = 30;
        lightness = 80;
      } else if (riskLevel >= 2) {
        baseHue = 35; // Amber/Murky
        saturation = 25;
        lightness = 82;
      }

      const gradient = ctx.createRadialGradient(
        displayW * 0.5, displayH * 0.2, 0,
        displayW * 0.5, displayH * 0.5, displayW * 0.8
      );
      gradient.addColorStop(0, `hsla(${baseHue}, ${saturation}%, ${lightness + 5}%, 1)`);
      gradient.addColorStop(1, `hsla(${baseHue}, ${saturation}%, ${lightness}%, 1)`);
      
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, displayW, displayH);

      // --- 2. Dynamic Caustics (Shimmering Light) ---
      ctx.save();
      ctx.globalCompositeOperation = 'multiply';
      ctx.globalAlpha = 0.05;
      for (let i = 0; i < 3; i++) {
        const shift = time * (1 + i * 0.5);
        ctx.beginPath();
        for (let x = 0; x < displayW; x += 40) {
          for (let y = 0; y < displayH; y += 40) {
            const noise = Math.sin(x * 0.01 + shift) * Math.cos(y * 0.01 + shift);
            if (noise > 0.5) {
              ctx.rect(x, y, 2, 2);
            }
          }
        }
        ctx.fillStyle = '#000';
        ctx.fill();
      }
      ctx.restore();

      // --- 3. Marine Snow ---
      ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
      snow.forEach(p => {
        p.x += p.vx + Math.sin(time + p.x) * 0.05;
        p.y += p.vy;
        if (p.y > displayH) p.y = -10;
        if (p.x > displayW) p.x = 0;
        if (p.x < 0) p.x = displayW;

        ctx.globalAlpha = p.opacity;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // --- 4. Organic Shrimp ---
      shrimp.forEach(s => {
        // Organic wandering
        s.angle += s.turnSpeed + Math.sin(time * 2 + s.x) * 0.01;
        s.x += Math.cos(s.angle) * s.speed;
        s.y += Math.sin(s.angle) * s.speed;

        // Wrap around
        if (s.x < -20) s.x = displayW + 20;
        if (s.x > displayW + 20) s.x = -20;
        if (s.y < -20) s.y = displayH + 20;
        if (s.y > displayH + 20) s.y = -20;

        // Depth of field (blur based on z)
        const blur = (1 - s.z) * 2;
        ctx.filter = `blur(${blur}px)`;
        ctx.globalAlpha = s.opacity * (0.6 + s.z * 0.4);
        
        ctx.save();
        ctx.translate(s.x, s.y);
        ctx.rotate(s.angle);
        
        // Draw Shrimp Body (Teardrop shape)
        ctx.beginPath();
        ctx.moveTo(s.size, 0);
        ctx.quadraticCurveTo(0, s.size * 0.4, -s.size, 0);
        ctx.quadraticCurveTo(0, -s.size * 0.4, s.size, 0);
        ctx.fillStyle = riskLevel >= 4 ? '#ef4444' : '#00ccaa';
        ctx.fill();

        // Antennae
        ctx.beginPath();
        ctx.moveTo(s.size, 0);
        ctx.lineTo(s.size + 8, -4);
        ctx.moveTo(s.size, 0);
        ctx.lineTo(s.size + 8, 4);
        ctx.strokeStyle = 'rgba(0,0,0,0.1)';
        ctx.lineWidth = 0.5;
        ctx.stroke();

        ctx.restore();
        ctx.filter = 'none';
      });

      // --- 5. God Rays (Tyndall Effect) ---
      ctx.save();
      const rayGradient = ctx.createLinearGradient(0, 0, displayW, displayH);
      rayGradient.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
      rayGradient.addColorStop(0.5, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = rayGradient;
      
      for (let i = 0; i < 4; i++) {
        const rayX = (displayW * 0.2) + (i * displayW * 0.3) + Math.sin(time * 0.5 + i) * 50;
        ctx.beginPath();
        ctx.moveTo(rayX, -50);
        ctx.lineTo(rayX + 150, -50);
        ctx.lineTo(rayX - 300, displayH + 50);
        ctx.lineTo(rayX - 500, displayH + 50);
        ctx.fill();
      }
      ctx.restore();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, [riskLevel]);

  return <canvas ref={canvasRef} className="w-full h-full block" />;
};
