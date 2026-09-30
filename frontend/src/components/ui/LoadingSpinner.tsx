import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  fullScreen?: boolean;
}

export function LoadingSpinner({ size = 'md', className = '', fullScreen = false }: LoadingSpinnerProps) {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  const spinner = (
    <Loader2 className={`animate-spin text-blue-600 ${sizes[size]} ${className}`} />
  );

  if (fullScreen) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] w-full">
        {spinner}
      </div>
    );
  }

  return spinner;
}
