import React from 'react';
import { Link } from '@remix-run/react';

interface AuditTrailPanelButtonProps {
  taskId: string;
  className?: string;
  disabled?: boolean;
}

function AuditTrailPanelGlyph(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 36 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      <path
        d="M4 24 Q10 10 14 8 Q22 16 24 24 Q30 16 34 14"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="3.5 4.8"
      />
      <circle cx={4} cy={24} r={3.2} fill="currentColor" />
      <circle cx={14} cy={8} r={3.2} fill="currentColor" />
      <circle cx={24} cy={24} r={3.2} fill="currentColor" />
      <circle cx={34} cy={14} r={3.2} fill="currentColor" />
    </svg>
  );
}

const AuditTrailPanelButton: React.FC<AuditTrailPanelButtonProps> = ({
  taskId,
  className = '',
  disabled = false
}) => {
  if (disabled) {
    return (
      <div
        className={`
          ml-2 p-1.5 rounded-md
          text-gray-400 dark:text-gray-500
          opacity-50 cursor-not-allowed
          ${className}
        `}
        title="Audit trail"
        aria-label="Audit trail"
      >
        <AuditTrailPanelGlyph className="h-5 w-5" />
      </div>
    );
  }

  return (
    <Link
      to={`audit/${taskId}`}
      relative="path"
      preventScrollReset
      className={`
        group ml-2 p-1.5 rounded-md inline-block
        text-gray-400 hover:text-whitePurple-50 dark:text-gray-500 dark:hover:text-purple-400
        hover:bg-whitePurple-50 dark:hover:bg-purple-900/20
        transition-all duration-200
        ${className}
      `}
      title="Audit trail"
      aria-label="Audit trail"
    >
      <AuditTrailPanelGlyph className="h-5 w-5 transition-transform group-hover:scale-110" />
    </Link>
  );
};

export default AuditTrailPanelButton;
