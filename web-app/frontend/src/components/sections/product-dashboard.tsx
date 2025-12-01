'use client';

import { Activity, ArrowRight, Bug, Clock, Settings } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

const FEATURE_CARDS = [
  {
    title: 'Runtime & Performance Logs',
    description:
      'Instantly view how long each node takes to execute, with timestamps and retry data.',
    icon: Clock,
    cta: 'Read more',
    href: '#',
  },
  {
    title: 'Live Flow Activity Feed',
    description:
      'Watch your automation unfold in real time — success, fail, delay — no refresh needed.',
    icon: Activity,
    cta: 'Read more',
    href: '#',
  },
  {
    title: 'Node-Level Debugging',
    description:
      'Click into any node to inspect its payloads, logs, and available data output at each step.',
    icon: Bug,
    cta: 'Read more',
    href: '#',
  },
  {
    title: 'Custom Event Tracking',
    description:
      'Attach custom events to any trigger or node and track their journey through the flow.',
    icon: Settings,
    cta: 'Read more',
    href: '#',
  },
];

export default function ProductDashboard() {
  return (
    <section className="section-padding relative container !pt-0">
      {/* Header */}
      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        <h2 className="text-4xl leading-none tracking-tight text-balance md:text-5xl lg:text-6xl">
          Privacy friendly, lightweight visualisation and control
        </h2>
      </div>

      {/* Main Dashboard Image */}
      <Image
        src="/images/product/plasma.webp"
        alt="Plasma Dashboard"
        width={1440}
        height={905}
        className="mx-auto mt-10 mask-b-from-50% mask-b-to-95% invert md:mt-16 dark:invert-0"
      />

      {/* Tagline */}
      <h3 className="text-muted-foreground mt-4 text-center uppercase">
        EVERYTHING YOU WANT TO SEE, NOTHING YOU DON&apos;T
      </h3>

      {/* Feature Cards */}
      <div className="mx-auto mt-6 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {FEATURE_CARDS.map((card, index) => {
          const IconComponent = card.icon;
          return (
            <Card
              key={index}
              className="group bg-accent/80 gap-4 border-none shadow-none"
            >
              <CardHeader className="gap-2.5">
                <div className="bg-card/50 flex size-10 items-center justify-center rounded-md border">
                  <IconComponent className="size-4.5 opacity-70" />
                </div>
                <CardTitle className="text-lg">{card.title}</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-1 flex-col">
                <CardDescription className="text-muted-foreground flex-1 text-sm">
                  {card.description}
                </CardDescription>
                <div>
                  <Button
                    variant="ghost"
                    asChild
                    className="group mt-6 h-12 gap-3 !px-0 font-normal transition-opacity hover:!bg-transparent hover:opacity-95"
                  >
                    <Link href={card.href}>
                      Read more
                      <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
