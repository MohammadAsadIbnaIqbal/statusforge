import React, { HTMLAttributes } from 'react';

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'warning' | 'destructive' | 'outline';
}

export function Badge({ className = '', variant = 'default', ...props }: BadgeProps) {
  const baseStyles = 'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  
  const variants = {
    default: 'border-transparent bg-gray-900 text-white hover:bg-gray-800',
    success: 'border-transparent bg-green-100 text-green-800',
    warning: 'border-transparent bg-yellow-100 text-yellow-800',
    destructive: 'border-transparent bg-red-100 text-red-800',
    outline: 'text-gray-950 border-gray-200',
  };

  return (
    <div className={`${baseStyles} ${variants[variant]} ${className}`} {...props} />
  );
}
