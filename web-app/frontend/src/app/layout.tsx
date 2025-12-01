import './globals.css';

import { RootProvider } from 'fumadocs-ui/provider';
import type { Metadata } from 'next';
import { Azeret_Mono, Inter } from 'next/font/google';

import Footer from '@/components/layout/footer';
import Navbar from '@/components/layout/navbar';
import { StyleGlideProvider } from '@/components/styleglide-provider';
import { ThemeProvider } from '@/components/theme-provider';
import { cn } from '@/lib/utils';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const azeretMono = Azeret_Mono({
  variable: '--font-azeret-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: 'Medical Notes Processor',
    template: '%s | Medical Notes',
  },
  description:
    'Medical notes processing and management system for Freed.ai and Osmind integration.',
  keywords: [
    'Medical Notes',
    'Healthcare',
    'EHR',
    'Freed.ai',
    'Osmind',
  ],
  authors: [{ name: 'Medical Notes Processor' }],
  creator: 'Medical Notes Processor',
  publisher: 'Medical Notes',
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: [
      { url: '/favicon/favicon.ico', sizes: '48x48' },
      { url: '/favicon/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon/favicon-96x96.png', sizes: '96x96', type: 'image/png' },
      { url: '/favicon/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon/favicon.ico' },
    ],
    apple: [{ url: '/favicon/apple-touch-icon.png', sizes: '180x180' }],
    shortcut: [{ url: '/favicon/favicon.ico' }],
  },
  openGraph: {
    title: 'Plasma - Modern Next.js Template',
    description:
      'A modern, fully featured Next.js template built with Shadcn/UI, TailwindCSS and TypeScript, perfect for your next web application.',
    siteName: 'Plasma',
    images: [
      {
        url: '/images/og-image.jpeg',
        width: 1200,
        height: 630,
        alt: 'Plasma - Modern Next.js Template',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Plasma - Modern Next.js Template',
    description:
      'A modern, fully featured Next.js template built with Shadcn/UI, TailwindCSS and TypeScript, perfect for your next web application.',
    images: ['/images/og-image.jpeg'],
    creator: '@shadcnblocks',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          'relative flex min-h-screen flex-col antialiased [--header-height:calc(var(--spacing)*17)]',
          inter.variable,
          azeretMono.variable,
        )}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          disableTransitionOnChange
        >
          <RootProvider
            search={{
              options: {
                type: 'static',
              },
            }}
          >
            {/* Background Blur */}
            <div className="bg-background/10 absolute inset-0 z-[-2] backdrop-blur-[85px] will-change-transform md:backdrop-blur-[170px]" />
            {/* Noise Background */}
            <div
              className="absolute inset-0 z-[-1] size-full opacity-70 mix-blend-overlay dark:md:opacity-100"
              style={{
                background: `url(/images/noise.webp) lightgray 0% 0% / 83.69069695472717px 83.69069695472717px repeat`,
              }}
            />
            <StyleGlideProvider />
            <Navbar />
            <main className="flex-1">{children}</main>
            <Footer />
          </RootProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
