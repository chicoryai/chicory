import React from 'react';

interface TrailIconProps {
  className?: string;
  size?: number;
}

const TrailIcon: React.FC<TrailIconProps> = ({ className = '', size = 20 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Top path with dots */}
      <circle cx="4" cy="6" r="2" fill="currentColor" />
      <path d="M6 6h4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <circle cx="12" cy="6" r="2" fill="currentColor" />
      <path d="M14 6h4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <circle cx="20" cy="6" r="2" fill="currentColor" />
      
      {/* Vertical connections */}
      <path d="M4 8v4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <path d="M12 8v4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <path d="M20 8v4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      
      {/* Bottom path with dots */}
      <circle cx="4" cy="14" r="2" fill="currentColor" />
      <path d="M6 14h4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <circle cx="12" cy="14" r="2" fill="currentColor" />
      <path d="M14 14h4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <circle cx="20" cy="14" r="2" fill="currentColor" />
      
      {/* Additional vertical connection for depth */}
      <path d="M12 16v2" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 1" />
      <circle cx="12" cy="20" r="2" fill="currentColor" />
    </svg>
  );
};

export default TrailIcon;