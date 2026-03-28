import { useRef, useEffect, useCallback } from 'react';

interface PondCanvasProps {
  riskLevel: number;
  deadShrimp: boolean;
  moltPeak: boolean;
}

const WATER_COLORS: Record<number, [string, string]> = {
  1: ['hsl(195,80%,18%)', 'hsl(200,60%,8%)'],
  2: ['hsl(195,70%,14%)', 'hsl(200,50%,6%)'],
  3: ['hsl(40,55%,14%)',  'hsl(35,40%,6%)'],
  4: ['hsl(10,60%,14%)',  'hsl(5,50%,6%)'],
  5: ['hsl(0,70%,11%)',   'hsl(0,60%,5%)'],
};

interface Shrimp {
  x: number; y: number;
  vx: number; vy: number;
  size: number; phase: number; baseY: number;
  legPhase: number;
  z: number; // depth factor 0..1
}

interface Bubble {
  x: number; y: number;
  r: number; speed: number; wobble: number;
}

interface MarineSnow {
  x: number; y: number;
  vx: number; vy: number;
  size: number; opacity: number;
}

function createShrimps(count: number, w: number, h: number): Shrimp[] {
  return Array.from({ length: count }, () => {
    const y = h * 0.38 + Math.random() * h * 0.50;
    return {
      x: Math.random() * w, y,
      vx: (Math.random() - 0.5) * 0.7,
      vy: (Math.random() - 0.5) * 0.2,
      size: 7 + Math.random() * 6,
      phase: Math.random() * Math.PI * 2,
      baseY: y,
      legPhase: Math.random() * Math.PI * 2,
      z: Math.random(), // depth 0=far/blurry, 1=close/sharp
    };
  });
}

function createBubbles(count: number, w: number, h: number): Bubble[] {
  return Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: h * 0.5 + Math.random() * h * 0.5,
    r: 1 + Math.random() * 2.5,
    speed: 0.25 + Math.random() * 0.6,
    wobble: Math.random() * Math.PI * 2,
  }));
}

function createMarineSnow(count: number, w: number, h: number): MarineSnow[] {
  return Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.1,
    vy: 0.05 + Math.random() * 0.15,
    size: 0.5 + Math.random() * 1.5,
    opacity: 0.04 + Math.random() * 0.18,
  }));
}

/** 像素风小龙虾 */
function drawShrimp(
  ctx: CanvasRenderingContext2D,
  s: Shrimp, t: number, dead: boolean,
) {
  ctx.save();
  ctx.translate(s.x, s.y);
  const facing = s.vx >= 0 ? 1 : -1;
  ctx.scale(facing * s.size * 0.11, s.size * 0.11);

  const swimAngle = Math.sin(t * 2.5 + s.phase) * 6;
  const alpha = dead ? 0.45 : 0.82;

  const shellBase  = dead ? `rgba(180,175,170,${alpha})` : `rgba(220,90,50,${alpha})`;
  const shellDark  = dead ? `rgba(140,135,130,${alpha})` : `rgba(170,50,20,${alpha})`;
  const shellLight = dead ? `rgba(210,205,200,${alpha})` : `rgba(255,140,80,${alpha})`;
  const eyeCol     = dead ? 'rgba(120,120,120,0.7)' : 'rgba(20,10,5,0.95)';
  const legCol     = dead ? 'rgba(160,155,150,0.5)' : `rgba(200,80,40,${alpha * 0.7})`;
  const antennaCol = dead ? 'rgba(170,165,160,0.4)' : `rgba(230,120,60,${alpha * 0.55})`;

  ctx.lineJoin = 'round';
  ctx.lineCap  = 'round';

  // ── TAIL FAN (uropods) ──
  const tailFanParts = [-22, -13, -4, 5, 14];
  tailFanParts.forEach((ang, i) => {
    const fanLen = i === 2 ? 18 : 14;
    const fanW   = i === 2 ? 6 : 5;
    ctx.save();
    ctx.translate(-38, swimAngle * 0.4);
    ctx.rotate((ang * Math.PI) / 180);
    ctx.beginPath();
    ctx.ellipse(0, -fanLen / 2, fanW / 2, fanLen / 2, 0, 0, Math.PI * 2);
    ctx.fillStyle = i % 2 === 0 ? shellDark : shellBase;
    ctx.fill();
    ctx.restore();
  });

  // ── ABDOMEN segments ──
  const segCount = 6;
  const segW = [12, 11, 10, 9, 8, 7];
  const segH = [8,  8,  7,  7,  6,  6];
  let segX = -26;
  let cumAngle = 0;
  for (let i = 0; i < segCount; i++) {
    const bend = swimAngle * 0.08 + (i > 2 ? (i - 2) * 1.2 : 0);
    cumAngle += bend;
    ctx.save();
    ctx.translate(segX, cumAngle * 0.6);
    ctx.rotate((cumAngle * Math.PI) / 180);
    ctx.beginPath();
    ctx.ellipse(0, 0, segW[i] / 2, segH[i] / 2, 0, 0, Math.PI * 2);
    ctx.fillStyle = i % 2 === 0 ? shellBase : shellDark;
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(-segW[i] / 2 + 1, -1);
    ctx.lineTo(segW[i] / 2 - 1, -1);
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 1;
    ctx.stroke();
    if (i > 0 && i < 5) {
      ctx.beginPath();
      ctx.moveTo(0, segH[i] / 2);
      ctx.lineTo(-3 + Math.sin(t * 4 + s.legPhase + i) * 2, segH[i] / 2 + 5);
      ctx.strokeStyle = legCol;
      ctx.lineWidth = 1.2;
      ctx.stroke();
    }
    ctx.restore();
    segX += segW[i] * 0.75;
  }

  // ── CARAPACE ──
  ctx.save();
  ctx.translate(18, swimAngle * 0.05);
  ctx.beginPath();
  ctx.ellipse(0, 0, 16, 10, 0, 0, Math.PI * 2);
  ctx.fillStyle = shellBase;
  ctx.fill();
  ctx.beginPath();
  ctx.ellipse(2, -2, 10, 5, -0.2, 0, Math.PI * 2);
  ctx.fillStyle = shellLight;
  ctx.globalAlpha = 0.25;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.ellipse(0, 0, 16, 10, 0, 0, Math.PI * 2);
  ctx.strokeStyle = shellDark;
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.restore();

  // ── WALKING LEGS ──
  for (let i = 0; i < 5; i++) {
    const legX = 8 + i * (-3.5);
    const swing = Math.sin(t * 3 + s.legPhase + i * 0.9) * 3;
    ctx.beginPath();
    ctx.moveTo(legX, 8);
    ctx.lineTo(legX - 2 + swing, 15);
    ctx.lineTo(legX - 1 + swing, 20);
    ctx.strokeStyle = legCol;
    ctx.lineWidth = 1.3;
    ctx.stroke();
    if (i < 2) {
      ctx.beginPath();
      ctx.arc(legX - 1 + swing, 20, 2, 0, Math.PI * 2);
      ctx.fillStyle = shellDark;
      ctx.fill();
    }
  }

  // ── HEAD ──
  ctx.save();
  ctx.translate(31, swimAngle * 0.05);
  ctx.beginPath();
  ctx.ellipse(0, 0, 9, 8, 0, 0, Math.PI * 2);
  ctx.fillStyle = shellBase;
  ctx.fill();
  ctx.strokeStyle = shellDark;
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();

  // ── ROSTRUM ──
  ctx.save();
  ctx.translate(34, swimAngle * 0.04 - 4);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(14, -3);
  ctx.lineTo(0, -1);
  ctx.closePath();
  ctx.fillStyle = shellDark;
  ctx.fill();
  ctx.restore();

  // ── EYES ──
  const eyeSwing = Math.sin(t * 0.8 + s.phase) * 1;
  ctx.save();
  ctx.translate(37, swimAngle * 0.04 - 2 + eyeSwing);
  ctx.beginPath();
  ctx.moveTo(0, 0); ctx.lineTo(4, -4);
  ctx.strokeStyle = shellDark; ctx.lineWidth = 1.2; ctx.stroke();
  ctx.beginPath();
  ctx.arc(4, -4, 2.8, 0, Math.PI * 2);
  ctx.fillStyle = eyeCol; ctx.fill();
  ctx.beginPath();
  ctx.arc(5, -5, 1, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(255,255,255,0.5)'; ctx.fill();
  ctx.restore();

  // ── ANTENNAE ──
  const ant1Sway = Math.sin(t * 1.8 + s.phase) * 4;
  const ant2Sway = Math.sin(t * 1.8 + s.phase + 0.5) * 3;
  ctx.beginPath();
  ctx.moveTo(38, swimAngle * 0.04 - 3);
  ctx.quadraticCurveTo(52, -18 + ant1Sway, 72, -12 + ant1Sway);
  ctx.strokeStyle = antennaCol; ctx.lineWidth = 0.9; ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(38, swimAngle * 0.04 - 1);
  ctx.quadraticCurveTo(54, -8 + ant2Sway, 76, -2 + ant2Sway);
  ctx.strokeStyle = antennaCol; ctx.lineWidth = 0.7; ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(38, swimAngle * 0.04);
  ctx.lineTo(46, -6 + ant2Sway * 0.5);
  ctx.lineTo(50, -4 + ant2Sway * 0.3);
  ctx.strokeStyle = antennaCol; ctx.lineWidth = 0.8; ctx.stroke();

  ctx.restore();
}

export default function PondCanvas({ riskLevel, deadShrimp, moltPeak }: PondCanvasProps) {
  const canvasRef     = useRef<HTMLCanvasElement>(null);
  const shrimpsRef    = useRef<Shrimp[]>([]);
  const bubblesRef    = useRef<Bubble[]>([]);
  const snowRef       = useRef<MarineSnow[]>([]);
  const animRef       = useRef<number>(0);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const t = performance.now() / 1000;

    if (shrimpsRef.current.length === 0) {
      shrimpsRef.current = createShrimps(moltPeak ? 90 : 120, w, h);
      bubblesRef.current = createBubbles(22, w, h);
      snowRef.current    = createMarineSnow(120, w, h);
    }

    ctx.clearRect(0, 0, w, h);

    // Sky / surface
    const skyGrad = ctx.createLinearGradient(0, 0, 0, h * 0.28);
    skyGrad.addColorStop(0, 'hsl(220,30%,7%)');
    skyGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = skyGrad;
    ctx.fillRect(0, 0, w, h * 0.28);

    // Water body
    const [wc1, wc2] = WATER_COLORS[riskLevel] || WATER_COLORS[1];
    const waterGrad = ctx.createLinearGradient(0, h * 0.18, 0, h);
    waterGrad.addColorStop(0, 'transparent');
    waterGrad.addColorStop(0.12, wc1);
    waterGrad.addColorStop(1, wc2);
    ctx.fillStyle = waterGrad;
    ctx.fillRect(0, 0, w, h);

    // ── GOD RAYS (improved triangle shafts) ──
    ctx.save();
    ctx.globalAlpha = 0.035;
    for (let i = 0; i < 5; i++) {
      const lx = w * 0.08 + i * (w * 0.21) + Math.sin(t * 0.25 + i * 1.3) * 28;
      const rayWidth = 40 + Math.sin(t * 0.4 + i) * 12;
      const shaft = ctx.createLinearGradient(lx, h * 0.18, lx, h * 0.9);
      shaft.addColorStop(0, 'rgba(180,230,255,1)');
      shaft.addColorStop(0.5, 'rgba(140,200,240,0.4)');
      shaft.addColorStop(1, 'transparent');
      ctx.fillStyle = shaft;
      ctx.beginPath();
      ctx.moveTo(lx - rayWidth * 0.3, h * 0.18);
      ctx.lineTo(lx + rayWidth * 0.7, h * 0.18);
      ctx.lineTo(lx + rayWidth * 2.5, h * 0.9);
      ctx.lineTo(lx - rayWidth * 2.0, h * 0.9);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();

    // ── CAUSTICS (水面焦散光斑) ──
    ctx.save();
    ctx.globalAlpha = 0.045;
    ctx.globalCompositeOperation = 'screen';
    for (let i = 0; i < 3; i++) {
      const shift = t * (0.6 + i * 0.35);
      ctx.fillStyle = 'rgba(100,210,255,1)';
      for (let cx = 0; cx < w; cx += 48) {
        for (let cy = h * 0.2; cy < h * 0.75; cy += 48) {
          const noise = Math.sin(cx * 0.012 + shift) * Math.cos(cy * 0.012 + shift * 0.7);
          if (noise > 0.55) {
            const r = 2 + noise * 4;
            ctx.beginPath();
            ctx.arc(cx + Math.sin(shift + cy) * 8, cy + Math.cos(shift + cx) * 8, r, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.restore();

    // Bottom mud gradient
    const mudGrad = ctx.createLinearGradient(0, h * 0.82, 0, h);
    mudGrad.addColorStop(0, 'transparent');
    mudGrad.addColorStop(1, 'rgba(50,32,16,0.5)');
    ctx.fillStyle = mudGrad;
    ctx.fillRect(0, h * 0.82, w, h * 0.18);

    // ── MARINE SNOW ──
    ctx.save();
    snowRef.current.forEach((p) => {
      p.x += p.vx + Math.sin(t + p.x * 0.01) * 0.05;
      p.y += p.vy;
      if (p.y > h + 10) { p.y = -10; p.x = Math.random() * w; }
      if (p.x > w) p.x = 0;
      if (p.x < 0) p.x = w;

      ctx.globalAlpha = p.opacity;
      ctx.fillStyle = 'rgba(200,235,255,1)';
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.restore();

    // Bubbles
    ctx.save();
    bubblesRef.current.forEach((b) => {
      b.y -= b.speed;
      b.x += Math.sin(t * 2 + b.wobble) * 0.25;
      if (b.y < h * 0.22) {
        b.y = h * 0.82 + Math.random() * h * 0.1;
        b.x = Math.random() * w;
      }
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,240,255,${0.04 + b.r * 0.015})`;
      ctx.fill();
    });
    ctx.restore();

    // ── SHRIMPS with depth-of-field blur ──
    const floatUp = riskLevel >= 4;
    // Sort by z so far shrimps render first
    const sorted = [...shrimpsRef.current].sort((a, b) => a.z - b.z);
    sorted.forEach((s) => {
      s.phase    += 0.009;
      s.legPhase += 0.015;
      s.x += s.vx;
      s.y += s.vy;

      if (floatUp) {
        s.vy -= 0.008;
        if (s.y < h * 0.26) s.vy = Math.abs(s.vy) * 0.4;
      } else {
        s.vy += (s.baseY - s.y) * 0.0025;
      }
      s.vy = Math.max(-1.2, Math.min(1.2, s.vy));
      s.vy *= 0.985;

      if (s.x < -60) s.x = w + 60;
      if (s.x > w + 60) s.x = -60;
      if (s.y > h * 0.94) { s.vy = -Math.abs(s.vy); s.y = h * 0.94; }

      // Depth of field: far shrimps (z→0) get blur and lower opacity
      const blur = (1 - s.z) * 2.2;
      ctx.filter = blur > 0.3 ? `blur(${blur.toFixed(1)}px)` : 'none';
      ctx.globalAlpha = 0.55 + s.z * 0.45;
      drawShrimp(ctx, s, t, deadShrimp);
      ctx.filter = 'none';
      ctx.globalAlpha = 1;
    });

    animRef.current = requestAnimationFrame(draw);
  }, [riskLevel, deadShrimp, moltPeak]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        const dpr = window.devicePixelRatio || 1;
        canvas.width  = rect.width  * dpr;
        canvas.height = rect.height * dpr;
        canvas.style.width  = `${rect.width}px`;
        canvas.style.height = `${rect.height}px`;
        const ctx = canvas.getContext('2d');
        if (ctx) ctx.scale(dpr, dpr);
        shrimpsRef.current = [];
        snowRef.current    = [];
      }
    };
    resize();
    window.addEventListener('resize', resize);
    animRef.current = requestAnimationFrame(draw);
    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
    };
  }, [draw]);

  return (
    <div className="relative w-full h-full">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
    </div>
  );
}
