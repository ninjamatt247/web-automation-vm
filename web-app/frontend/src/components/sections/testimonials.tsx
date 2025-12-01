'use client';

import { ArrowRight } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { Marquee } from '@/components/magicui/marquee';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { cn } from '@/lib/utils';

const REVIEWS = [
  {
    name: 'Flora Schuler',
    username: '@floraFlawa',
    body: "i'm using @plasma to get access to some of the best automation features in the market, you should try it too",
    img: 'https://avatar.vercel.sh/floraFlawa',
  },
  {
    name: 'OneBadDev',
    username: '@elidecodes',
    body: "been using @plasma to automate my podcast post-prod flow. local triggers + ffmpeg scripts = chef's kiss",
    img: 'https://avatar.vercel.sh/elidecodes',
  },
  {
    name: 'John Robert',
    username: '@scripteddev',
    body: '@plasma is already part of my daily toolkit. Local folder watcher → python script → discord alert. Took 2 mins to set up.',
    img: 'https://avatar.vercel.sh/scripteddev',
  },
  {
    name: 'CodeNinja',
    username: '@sysninja',
    body: "Can't believe how fast @plasma runs. It's like Zapier if it respected your privacy and your CPU.",
    img: 'https://avatar.vercel.sh/sysninja',
  },
  {
    name: 'Tusmah',
    username: '@ananenu1',
    body: "Made a Plasma flow that watches my screenshot folder and auto-saves new captures to Notion. Didn't touch the cloud once. 🔥",
    img: 'https://avatar.vercel.sh/ananenu1',
  },
  {
    name: 'Liam Stone',
    username: '@liam.codes',
    body: "Plasma completely changed how I debug and monitor workflows. It's like having a second brain for automation.",
    img: 'https://avatar.vercel.sh/liam.codes',
  },
];

const firstRow = REVIEWS.slice(0, REVIEWS.length / 2);
const secondRow = REVIEWS.slice(REVIEWS.length / 2);
const Testimonials = () => {
  return (
    <section className="container flex flex-col gap-y-10 overflow-x-hidden py-10 md:py-15 lg:flex-row">
      <div className="flex max-w-lg flex-col gap-15 text-balance">
        <h2 className="text-4xxl leading-tight tracking-tight md:text-5xl">
          Real automation for control freaks
        </h2>
        <div className="space-y-7.5">
          <p className="text-muted-foreground text-lg leading-snug">
            Every run is tracked in detail - from inputs to outputs to runtime
            errors. Perfect for debugging and transparency.
          </p>

          <Button
            variant="ghost"
            asChild
            className="text-accent-foreground group gap-3 !px-0 hover:!bg-transparent hover:opacity-90"
          >
            <Link href="#">
              Get started too
              <ArrowRight className="size-5 transition-transform group-hover:translate-x-1" />
            </Link>
          </Button>
        </div>
      </div>

      <div className="relative -mr-[max(2rem,calc((100vw-80rem)/2+5rem))] flex flex-1 flex-col gap-2.25 overflow-hidden mask-l-from-50% mask-l-to-100%">
        <Marquee
          pauseOnHover
          className="py-0 [--duration:20s] [--gap:calc(var(--spacing)*2.25)]"
        >
          {firstRow.map((review) => (
            <ReviewCard key={review.username} {...review} />
          ))}
        </Marquee>
        <Marquee
          reverse
          pauseOnHover
          className="py-0 [--duration:20s] [--gap:calc(var(--spacing)*2.25)]"
        >
          {secondRow.map((review) => (
            <ReviewCard key={review.username} {...review} />
          ))}
        </Marquee>
      </div>
    </section>
  );
};

export default Testimonials;

const ReviewCard = ({
  img,
  name,
  username,
  body,
}: {
  img: string;
  name: string;
  username: string;
  body: string;
}) => {
  return (
    <Card
      className={cn(
        'hover:bg-accent/60 max-w-xs cursor-pointer gap-4 bg-transparent p-6 md:max-w-sm md:p-8',
        'transition-colors duration-200',
      )}
    >
      <CardHeader className="flex items-center gap-4 p-0">
        <Image
          className="rounded-full"
          width={32}
          height={32}
          alt={`${name} avatar`}
          src={img}
        />
        <div className="flex flex-col">
          <CardTitle className="text-sm font-bold">{name}</CardTitle>
          <CardDescription className="text-muted-foreground text-xs">
            {username}
          </CardDescription>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <blockquote className="text-sm leading-snug">
          {body.split(/(@plasma)/g).map((part, index) =>
            part === '@plasma' ? (
              <span key={index} className="text-chart-1">
                {part}
              </span>
            ) : (
              part
            ),
          )}
        </blockquote>
      </CardContent>
    </Card>
  );
};
