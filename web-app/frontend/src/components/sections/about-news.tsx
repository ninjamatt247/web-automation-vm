import { ArrowRight } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const newsItems = [
  {
    id: 1,
    logo: {
      src: '/images/logos/forbes.svg',
      alt: 'Forbes',
      width: 162,
      height: 42,
      className: 'invert dark:invert-0',
    },
    title:
      'With a drag-and-drop interface that feels more like a design tool than a backend UI, Plasma is quietly redefining local-first automation. No cloud, no subscriptions - just speed and control.',
    readMoreLink: '#',
  },
  {
    id: 2,
    logo: {
      src: '/images/logos/tc.svg',
      alt: 'TechCrunch',
      width: 84,
      height: 42,
    },
    title:
      'Plasma puts full autonomy in the hands of builders. Its ability to connect folders, scripts, APIs and even AI-generated logic all without leaving your desktop',
    readMoreLink: '#',
  },
  {
    id: 3,
    logo: {
      src: '/images/logos/the-guardian.svg',
      alt: 'The Guardian',
      width: 127.8,
      height: 48,
      className: 'invert dark:invert-0',
    },
    title:
      "Lightweight, privacy-first, and shockingly powerful. It's rare for an automation product to feel this flexible out of the box. Local-first isn't just a feature—it's a philosophy.",
    readMoreLink: '#',
  },
];

export default function AboutNews() {
  return (
    <section className="section-padding bg-muted/40">
      <div className="container">
        <h2 className="text-4xxl leading-tight tracking-tight md:text-5xl">
          We are in the news!
        </h2>

        <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-3">
          {newsItems.map((item) => (
            <div key={item.id} className="space-y-3">
              <Image
                src={item.logo.src}
                alt={item.logo.alt}
                width={item.logo.width}
                height={item.logo.height}
                className={cn`object-contain ${item.logo.className}`}
              />

              <p className="text-accent-foreground text-lg leading-snug">
                {item.title}
              </p>

              <Button
                variant="ghost"
                asChild
                className="group gap-3 !px-0 font-normal transition-opacity hover:!bg-transparent hover:opacity-95"
              >
                <Link href={item.readMoreLink}>
                  Read more
                  <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </Button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
