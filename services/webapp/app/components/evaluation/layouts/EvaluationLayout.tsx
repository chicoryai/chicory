import React from 'react';
import { ParticleField } from '../effects/ParticleField';

interface EvaluationLayoutProps {
  children: React.ReactNode;
  particleBackground?: boolean;
  className?: string;
}

/**
 * Top-level layout wrapper that provides:
 * - Deep space background with particle effects
 * - Glass morphism base styling
 * - Z-index layering for floating elements
 */
export function EvaluationLayout({ 
  children, 
  particleBackground = true,
  className 
}: EvaluationLayoutProps) {
  return (
    <div className={`min-h-screen bg-transparent dark:bg-gray-900 relative overflow-hidden ${className || ''}`}>
      {/* Deep space gradient background */}
      <div className="absolute inset-0 bg-transparent dark:bg-gray-900" />
      
      {/* Content layer */}
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}