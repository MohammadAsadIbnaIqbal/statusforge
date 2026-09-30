import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'primary', size = 'md', isLoading = false, children, disabled, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
    
    const variants = {
      primary: 'bg-gray-900 text-white hover:bg-gray-800 focus-visible:ring-gray-900 shadow-sm',
      secondary: 'bg-white border border-gray-200 text-gray-900 hover:bg-gray-50 hover:text-gray-900 focus-visible:ring-gray-200 shadow-sm',
      destructive: 'bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-600 shadow-sm',
      outline: 'border border-gray-200 bg-transparent hover:bg-gray-50 text-gray-900 focus-visible:ring-gray-200',
      ghost: 'bg-transparent hover:bg-gray-50 text-gray-900 focus-visible:ring-gray-200',
    };

    const sizes = {
      sm: 'h-8 px-3 text-sm',
      md: 'h-10 px-4 py-2',
      lg: 'h-12 px-8 text-lg',
    };

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';
