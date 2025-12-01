'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import React, { useEffect, useState } from 'react';

import Logo from '@/components/layout/logo';
import { ThemeToggle } from '@/components/theme-toggle';
import { Button } from '@/components/ui/button';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu';
import { cn } from '@/lib/utils';

export const NAV_LINKS = [
  { label: 'Dashboard', href: '/dashboard' },
  { label: 'Freed Notes', href: '/notes' },
  { label: 'Osmind Notes', href: '/osmind-notes' },
  { label: 'Comparison', href: '/comparison' },
  { label: 'Process', href: '/process' },
  { label: 'Dev Tools', href: '/dev-tools' },
];

const ACTION_BUTTONS: Array<{
  label: string;
  href: string;
  variant: 'ghost' | 'default';
}> = [
  // Action buttons can be re-enabled if authentication is needed
  // { label: 'Log in', href: '/signin', variant: 'ghost' as const },
  // { label: 'Sign up', href: '/signup', variant: 'default' as const },
];

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const pathname = usePathname();
  const hideNavbar = ['/signin', '/signup', '/otp', '/docs'].some((route) =>
    pathname.includes(route),
  );

  useEffect(() => {
    if (isMenuOpen) {
      document.documentElement.style.overflow = 'hidden';
      document.body.style.overflow = 'hidden';
    } else {
      document.documentElement.style.overflow = '';
      document.body.style.overflow = '';
    }

    return () => {
      document.documentElement.style.overflow = '';
      document.body.style.overflow = '';
    };
  }, [isMenuOpen]);

  if (hideNavbar) return null;

  return (
    <header className="lg:border-b">
      <div className="relative z-50 container flex h-[var(--header-height)] items-center justify-between gap-4">
        <Logo className="w-47" />

        <NavigationMenu viewport={false} className="hidden lg:block">
          <NavigationMenuList className="gap-4 xl:gap-8">
            {NAV_LINKS.map((item) => (
              <NavigationMenuItem key={item.label}>
                <NavigationMenuLink
                  href={item.href}
                  className={cn(
                    navigationMenuTriggerStyle(),
                    'bg-transparent',
                    pathname === item.href && 'bg-accent font-semibold',
                  )}
                >
                  {item.label}
                </NavigationMenuLink>
              </NavigationMenuItem>
            ))}
          </NavigationMenuList>
        </NavigationMenu>

        <div className="hidden w-47 items-center justify-end gap-4 lg:flex">
          <ThemeToggle />
          {ACTION_BUTTONS.map((button) => (
            <Button
              key={button.label}
              size="sm"
              variant={button.variant}
              asChild
            >
              <Link href={button.href}>{button.label}</Link>
            </Button>
          ))}
        </div>
        <div className="flex items-center gap-2 lg:hidden lg:gap-4">
          <ThemeToggle />
          <button
            className="text-muted-foreground relative flex size-8 rounded-sm border lg:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <span className="sr-only">Open main menu</span>
            <div
              className={cn(
                'absolute top-1/2 left-1/2 block w-4 -translate-x-1/2 -translate-y-1/2',
              )}
            >
              <span
                aria-hidden="true"
                className={cn(
                  'absolute block h-0.25 w-full rounded-full bg-current transition duration-500 ease-in-out',
                  isMenuOpen ? 'rotate-45' : '-translate-y-1.5',
                )}
              ></span>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute block h-0.25 w-full rounded-full bg-current transition duration-500 ease-in-out',
                  isMenuOpen ? 'opacity-0' : '',
                )}
              ></span>
              <span
                aria-hidden="true"
                className={cn(
                  'absolute block h-0.25 w-full rounded-full bg-current transition duration-500 ease-in-out',
                  isMenuOpen ? '-rotate-45' : 'translate-y-1.5',
                )}
              ></span>
            </div>
          </button>
        </div>

        {/*  Mobile Menu Navigation */}
        <div
          className={cn(
            'bg-background/95 text-accent-foreground fixed inset-0 top-[var(--header-height)] z-50 flex flex-col justify-between tracking-normal backdrop-blur-md transition-all duration-500 ease-out lg:hidden',
            isMenuOpen
              ? 'translate-x-0 opacity-100'
              : 'pointer-events-none translate-x-full opacity-0',
          )}
        >
          <div className="container">
            <NavigationMenu
              orientation="vertical"
              className="inline-block w-full max-w-none py-10"
            >
              <NavigationMenuList className="w-full flex-col items-start gap-6">
                {NAV_LINKS.map((item) => (
                  <NavigationMenuItem key={item.label} className="w-full">
                    <NavigationMenuLink
                      href={item.href}
                      className={cn(
                        'hover:text-foreground text-base transition-colors',
                        pathname === item.href && 'font-semibold',
                      )}
                      onClick={() => setIsMenuOpen(false)}
                    >
                      {item.label}
                    </NavigationMenuLink>
                  </NavigationMenuItem>
                ))}
              </NavigationMenuList>
            </NavigationMenu>
          </div>

          <div className="flex gap-4.5 border-t px-6 py-4">
            {ACTION_BUTTONS.map((button) => (
              <Button
                key={button.label}
                variant={button.variant === 'ghost' ? 'muted' : button.variant}
                asChild
                className="h-12 flex-1 rounded-sm transition-all hover:scale-105"
              >
                <Link href={button.href} onClick={() => setIsMenuOpen(false)}>
                  {button.label}
                </Link>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
