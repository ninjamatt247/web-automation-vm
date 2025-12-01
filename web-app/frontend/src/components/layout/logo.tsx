import Link from 'next/link';

import { cn } from '@/lib/utils';

interface LogoProps {
  iconClassName?: string;
  wordmarkClassName?: string;
  className?: string;
  href?: string;
  noLink?: boolean;
}

export default function Logo({
  iconClassName,
  wordmarkClassName,
  className,
  href = '/',
  noLink = false,
}: LogoProps) {
  const Element = noLink ? 'div' : Link;

  return (
    <Element
      href={href}
      className={cn(
        'flex items-center gap-1.75 text-xl font-medium',
        className,
      )}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 40 30"
        fill="none"
        className={cn('w-7 object-contain', iconClassName)}
      >
        <path
          d="M23.1469 0.00488281L17.4401 10.1355H39.5096L28.3228 29.569H16.6081L22.3149 19.4384H0.245361L11.4322 0.00488281H23.1469Z"
          fill="#9A5CD0"
        />
      </svg>
      <span className={cn('', wordmarkClassName)}>Plasma</span>
    </Element>
  );
}
