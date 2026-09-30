import React, { HTMLAttributes, forwardRef } from 'react';
import { AlertCircle, CheckCircle2, Info, XCircle } from 'lucide-react';

export interface AlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'success' | 'warning';
  title?: string;
}

export const Alert = forwardRef<HTMLDivElement, AlertProps>(
  ({ className = '', variant = 'default', title, children, ...props }, ref) => {
    const variants = {
      default: 'bg-blue-50 text-blue-900 border-blue-200',
      destructive: 'bg-red-50 text-red-900 border-red-200',
      success: 'bg-green-50 text-green-900 border-green-200',
      warning: 'bg-yellow-50 text-yellow-900 border-yellow-200',
    };

    const icons = {
      default: <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />,
      destructive: <XCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />,
      success: <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />,
      warning: <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />,
    };

    return (
      <div
        ref={ref}
        role="alert"
        className={`w-full rounded-lg border p-4 flex items-start gap-3 ${variants[variant]} ${className}`}
        {...props}
      >
        {icons[variant]}
        <div className="flex-1">
          {title && <h5 className="mb-1 font-medium leading-none tracking-tight">{title}</h5>}
          <div className="text-sm opacity-90">{children}</div>
        </div>
      </div>
    );
  }
);
Alert.displayName = 'Alert';
