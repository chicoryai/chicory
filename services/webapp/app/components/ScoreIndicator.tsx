import { useEffect, useRef } from "react";

interface ScoreIndicatorProps {
  score: number;
  maxScore?: number;
  variant?: 'circular' | 'linear' | 'numeric';
  animated?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ScoreIndicator({
  score,
  maxScore = 100,
  variant = 'circular',
  animated = true,
  size = 'md'
}: ScoreIndicatorProps) {
  const percentage = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const currentValueRef = useRef(0);

  const sizeConfig = {
    sm: { canvas: 60, strokeWidth: 4, fontSize: 'text-sm', barHeight: 'h-2' },
    md: { canvas: 80, strokeWidth: 6, fontSize: 'text-base', barHeight: 'h-3' },
    lg: { canvas: 100, strokeWidth: 8, fontSize: 'text-lg', barHeight: 'h-4' }
  };

  const config = sizeConfig[size];

  const getScoreColor = (percent: number) => {
    if (percent >= 80) return { stroke: '#22c55e', bg: 'bg-green-500', text: 'text-green-600' };
    if (percent >= 60) return { stroke: '#84cc16', bg: 'bg-lime-500', text: 'text-lime-600' };
    if (percent >= 40) return { stroke: '#eab308', bg: 'bg-yellow-500', text: 'text-yellow-600' };
    if (percent >= 20) return { stroke: '#f97316', bg: 'bg-orange-500', text: 'text-orange-600' };
    return { stroke: '#ef4444', bg: 'bg-red-500', text: 'text-red-600' };
  };

  const colors = getScoreColor(percentage);

  useEffect(() => {
    if (variant !== 'circular' || !canvasRef.current || !animated) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const centerX = config.canvas / 2;
    const centerY = config.canvas / 2;
    const radius = (config.canvas - config.strokeWidth) / 2;

    const animate = () => {
      ctx.clearRect(0, 0, config.canvas, config.canvas);

      // Background circle
      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = config.strokeWidth;
      ctx.stroke();

      // Animated progress circle
      const targetValue = (percentage / 100) * 2 * Math.PI;
      currentValueRef.current += (targetValue - currentValueRef.current) * 0.1;

      ctx.beginPath();
      ctx.arc(
        centerX,
        centerY,
        radius,
        -Math.PI / 2,
        -Math.PI / 2 + currentValueRef.current,
        false
      );
      ctx.strokeStyle = colors.stroke;
      ctx.lineWidth = config.strokeWidth;
      ctx.lineCap = 'round';
      ctx.stroke();

      if (Math.abs(targetValue - currentValueRef.current) > 0.01) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [percentage, variant, animated, colors.stroke, config]);

  if (variant === 'numeric') {
    return (
      <div className={`font-bold ${config.fontSize} ${colors.text}`}>
        {animated ? (
          <span className="tabular-nums">
            {Math.round(percentage)}%
          </span>
        ) : (
          `${Math.round(percentage)}%`
        )}
      </div>
    );
  }

  if (variant === 'linear') {
    return (
      <div className="w-full">
        <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full ${config.barHeight} overflow-hidden`}>
          <div
            className={`${config.barHeight} rounded-full transition-all duration-500 ease-out ${colors.bg}`}
            style={{
              width: animated ? `${percentage}%` : `${percentage}%`,
              transition: animated ? 'width 0.5s ease-out' : 'none'
            }}
          />
        </div>
        <div className={`mt-1 text-right ${config.fontSize} font-medium ${colors.text}`}>
          {Math.round(percentage)}%
        </div>
      </div>
    );
  }

  // Circular variant
  return (
    <div className="relative inline-flex items-center justify-center">
      <canvas
        ref={canvasRef}
        width={config.canvas}
        height={config.canvas}
        className="transform -rotate-90"
      />
      <div className={`absolute inset-0 flex items-center justify-center ${config.fontSize} font-bold ${colors.text}`}>
        {Math.round(percentage)}%
      </div>
    </div>
  );
}