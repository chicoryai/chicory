import React from 'react';

interface AlertMessageProps {
  show: boolean;
  success?: boolean;
  message?: string;
}

export default function AlertMessage({ show, success, message }: AlertMessageProps) {
  if (!show || !message) return null;
  
  return (
    <div className={`mb-6 p-4 ${success 
      ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200' 
      : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'} rounded-md`}>
      {message}
    </div>
  );
}
