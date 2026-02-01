import React from 'react';

interface TabPanelProps {
  value: string;
  current: string;
  children: React.ReactNode;
}

export function TabPanel({ value, current, children }: TabPanelProps) {
  if (value !== current) return null;
  
  return (
    <div className="animate-fadeIn">
      {children}
    </div>
  );
}