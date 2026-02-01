import { useState, useEffect } from 'react';

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  loading?: boolean;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

export function ToggleSwitch({
  checked,
  onChange,
  disabled = false,
  loading = false,
  size = 'md',
  label,
  className = ''
}: ToggleSwitchProps) {
  const [isChecked, setIsChecked] = useState(checked);

  useEffect(() => {
    setIsChecked(checked);
  }, [checked]);

  const handleToggle = () => {
    if (!disabled && !loading) {
      const newState = !isChecked;
      setIsChecked(newState);
      onChange(newState);
    }
  };

  // Size configurations
  const sizeClasses = {
    sm: {
      switch: 'w-8 h-4',
      toggle: 'w-3 h-3',
      translate: 'translate-x-4',
      labelText: 'text-xs'
    },
    md: {
      switch: 'w-11 h-6',
      toggle: 'w-5 h-5',
      translate: 'translate-x-5',
      labelText: 'text-sm'
    },
    lg: {
      switch: 'w-14 h-7',
      toggle: 'w-6 h-6',
      translate: 'translate-x-7',
      labelText: 'text-base'
    }
  };

  const config = sizeClasses[size];

  return (
    <div className={`flex items-center ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={isChecked}
        onClick={handleToggle}
        disabled={disabled || loading}
        className={`
          relative inline-flex flex-shrink-0 cursor-pointer rounded-full 
          border-2 border-transparent transition-colors duration-200 ease-in-out 
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
          ${config.switch}
          ${isChecked 
            ? 'bg-blue-600 dark:bg-blue-500' 
            : 'bg-gray-300 dark:bg-gray-600'
          }
          ${(disabled || loading) ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <span className="sr-only">{label || 'Toggle'}</span>
        <span
          aria-hidden="true"
          className={`
            pointer-events-none inline-block rounded-full bg-white shadow 
            transform ring-0 transition duration-200 ease-in-out
            ${config.toggle}
            ${isChecked ? config.translate : 'translate-x-0'}
            ${loading ? 'animate-pulse' : ''}
          `}
        />
      </button>
      {label && (
        <span className={`ml-3 ${config.labelText} text-gray-700 dark:text-gray-300`}>
          {label}
        </span>
      )}
    </div>
  );
}