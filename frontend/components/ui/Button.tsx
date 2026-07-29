import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; children: ReactNode }) {
  const variantClass = variant === 'primary' ? 'button-primary' : variant === 'secondary' ? 'button-secondary' : '';
  return (
    <button className={`button ${variantClass} ${className}`} {...props}>
      {children}
    </button>
  );
}
