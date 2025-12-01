'use client';

import {
  BadgeCheck,
  ChevronsUpDown,
  Download,
  FileSpreadsheet,
  Folder,
  Share,
} from 'lucide-react';
import { motion, useInView } from 'motion/react';
import { useRef } from 'react';
import {
  FaApple,
  FaAws,
  FaDiscord,
  FaDropbox,
  FaDroplet,
  FaFigma,
  FaGithub,
  FaGoogle,
  FaIntercom,
  FaLinkedin,
  FaMailchimp,
  FaMicrosoft,
  FaSalesforce,
  FaShopify,
  FaSlack,
  FaSpotify,
  FaStripe,
  FaTrello,
  FaTwitter,
  FaWandSparkles,
} from 'react-icons/fa6';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from 'recharts';

import { NumberTicker } from '@/components/magicui/number-ticker';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ChartContainer } from '@/components/ui/chart';
import { cn } from '@/lib/utils';

// Feature card data
const FEATURE_CARDS = [
  {
    title: 'Step-by-Step Debugging',
    description: 'Visualize how each node performs in real time',
    image: '/images/product/debugging.png',
  },
  {
    title: 'Export Data',
    description: 'Export node outputs or logs as CSV, JSON, or XLS',
    image: '/images/product/export.png',
  },
  {
    title: 'Performance tracking',
    description:
      'Track successful run counts and spot performance spikes or drops',
    image: '/images/product/performance.png',
  },
  {
    title: 'Integrate data and tracking with apps',
    description: 'Observe outputs from third-party apps',
    image: '/images/product/integrate.png',
  },
  {
    title: 'AI Usage tracking',
    description: 'Monitor token usage and AI-triggered actions',
    image: '/images/product/ai-usage.png',
  },
];

export default function ProductFeatures() {
  return (
    <section className="section-padding container max-w-screen-xl">
      {/* Header */}
      <div className="mx-auto max-w-4xl">
        <h2 className="text-4xxl leading-tight tracking-tight md:text-5xl">
          Details Don&apos;t Mean Clarity — Until They Do
        </h2>
        <p className="text-muted-foreground mt-3 text-lg leading-snug">
          Most automators hide the details. Plasma shows you the right
          things — logs, durations, errors, and system info — at the right time.
        </p>
      </div>

      {/* Feature Cards Grid */}
      <div className="mt-10 grid grid-cols-1 gap-6 md:mt-16 lg:grid-cols-6">
        {FEATURE_CARDS.map((card, index) => (
          <FeatureCard
            key={card.title}
            title={card.title}
            description={card.description}
            className={cn(
              'lg:col-span-2',
              (index === 4 || index === 3) &&
                `!h-auto flex-col-reverse justify-between gap-6 lg:col-span-3 lg:flex-row-reverse lg:items-center [&_.card-header]:lg:max-w-50`,
            )}
          >
            {renderCardContent(index)}
          </FeatureCard>
        ))}
      </div>
    </section>
  );
}

// Render content for each card based on index
function renderCardContent(index: number) {
  switch (index) {
    case 0:
      return <Card1 />;
    case 1:
      return <Card2 />;
    case 2:
      return <Card3 />;
    case 3:
      return <Card4 />;
    case 4:
      return <Card5 />;
    default:
      return null;
  }
}

// Feature Card Component
function FeatureCard({
  title,
  description,
  children,
  className,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card
      className={cn(
        'to-muted/10 via-muted/5 relative justify-between gap-2 overflow-hidden rounded-xl bg-gradient-to-b from-transparent p-8 md:h-[400px]',
        className,
      )}
    >
      <CardContent className="relative p-0">{children}</CardContent>
      <CardHeader className="card-header p-0">
        <h3 className="text-accent-foreground text-xl font-bold">{title}</h3>
        <p className="text-muted-foreground text-lg leading-snug">
          {description}
        </p>
      </CardHeader>
    </Card>
  );
}

function Card1() {
  const performanceData = [
    { label: '0ms', startOffset: 0, width: 85, delay: 0.2 },
    { label: '166ms', startOffset: 15, width: 55, delay: 0.4 },
    { label: '333ms', startOffset: 25, width: 70, delay: 0.6 },
    { label: '500ms', startOffset: 5, width: 40, delay: 0.8 },
    { label: '', startOffset: 30, width: 35, delay: 1.0 },
    { label: '', startOffset: 45, width: 25, delay: 1.2 },
    { label: '', startOffset: 55, width: 40, delay: 1.4 },
  ];

  return (
    <div className="relative overflow-hidden rounded-xl border-t p-5 shadow-lg">
      <div className="text-muted-foreground flex items-center gap-4">
        <button className="bg-muted/30 flex items-center gap-2 rounded-sm border px-2 py-1">
          <FaDroplet className="size-2" />
          <span className="text-xs font-medium">Button</span>
        </button>

        <button className="bg-muted/30 flex items-center gap-2 rounded-sm border px-2 py-1">
          <FaDroplet className="size-2" />
          <span className="text-xs font-medium">Button</span>
        </button>
      </div>

      <div className="mt-6 space-y-4">
        {/* Time labels */}
        <div className="flex justify-between text-[0.625rem]">
          <span>0ms</span>
          <span>166ms</span>
          <span>333ms</span>
          <span>500ms</span>
        </div>

        {/* Performance bars */}
        <div className="space-y-2.5">
          {performanceData.map((item, index) => (
            <div key={index} className="relative h-2">
              {/* Animated gradient progress bar */}
              <motion.div
                className={`from-chart-1 to-chart-3 absolute top-0 h-2 origin-left rounded-xs bg-gradient-to-r`}
                style={{
                  left: `${item.startOffset}%`,
                  width: `${item.width}%`,
                }}
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.8,
                  ease: 'easeOut',
                  delay: item.delay,
                }}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Card2() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  const exportOptions = [
    { label: 'Share URL', icon: Share, shortcut: '⌘ T' },
    { label: 'Export to XLS', icon: FileSpreadsheet, shortcut: '⌘ A' },
    { label: 'Export to CSV', icon: Download, shortcut: '⌘ J' },
    { label: 'AI Adjust', icon: FaWandSparkles, shortcut: '⌘ Q' },
  ];

  const chartData = [
    { name: 'Jan', value1: 400, value2: 240 },
    { name: 'Feb', value1: 300, value2: 139 },
    { name: 'Mar', value1: 200, value2: 300 },
    { name: 'Apr', value1: 278, value2: 390 },
    { name: 'May', value1: 189, value2: 480 },
    { name: 'Jun', value1: 239, value2: 380 },
  ];

  return (
    <div className="relative h-full overflow-hidden px-5 pb-5">
      {/* Background Chart */}
      <div className="absolute inset-5 border mask-b-from-50% mask-b-to-100% p-2 opacity-30">
        <ChartContainer
          config={{
            value1: {
              label: 'Series 1',
              color: 'var(--chart-1)',
            },
            value2: {
              label: 'Series 2',
              color: 'var(--chart-2)',
            },
          }}
          className="h-full w-full"
        >
          <LineChart data={chartData} margin={{ left: -24 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border)"
              opacity={0.3}
            />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="value1"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="value2"
              stroke="var(--chart-2)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartContainer>
      </div>

      {/* Header */}
      <div ref={ref} className="mx-auto w-fit">
        <motion.div
          className="bg-accent relative z-10 mb-4 flex w-fit items-center gap-2 rounded-sm border-s-2 border-t-2 px-3 py-1.5 text-xs"
          initial={{ opacity: 0, y: -10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{
            duration: 0.4,
            ease: 'easeOut',
          }}
        >
          <motion.div
            animate={isInView ? { rotate: 180 } : { rotate: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            <ChevronsUpDown className="size-3" />
          </motion.div>
          10 days ago
        </motion.div>

        {/* Export Options List - Dropdown Animation */}
        <motion.div
          className="bg-accent relative z-10 max-w-fit space-y-2 rounded-md border p-1 backdrop-blur-sm"
          initial={{
            opacity: 0,
            scaleY: 0,
            transformOrigin: 'top center',
          }}
          whileInView={{
            opacity: 1,
            scaleY: 1,
          }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{
            duration: 0.4,
            delay: 0.3,
            ease: [0.25, 0.46, 0.45, 0.94], // Custom easing for dropdown feel
          }}
        >
          {exportOptions.map((option, index) => {
            const isAIAdjust = option.label === 'AI Adjust';
            return (
              <motion.div
                key={index}
                className={cn(
                  'flex cursor-pointer items-center gap-3 rounded-sm px-2 py-1.5 text-xs transition-colors',
                  isAIAdjust
                    ? 'hover:bg-card/50 focus:bg-card/40'
                    : 'focus:bg-muted focus:text-accent-foreground hover:bg-muted/50',
                )}
                initial={{ opacity: 0, x: -5 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{
                  duration: 0.3,
                  delay: 0.6 + index * 0.1, // Start after dropdown opens
                  ease: 'easeOut',
                }}
              >
                <option.icon
                  className={cn(
                    'size-4',
                    isAIAdjust ? 'text-chart-1' : 'text-muted-foreground',
                  )}
                />
                <span
                  className={cn(
                    'flex-1',
                    isAIAdjust ? 'text-gradient font-medium' : '',
                  )}
                >
                  {option.label}
                </span>
                <span
                  className={cn(
                    'ms-2 text-xs',
                    isAIAdjust ? 'text-gradient' : 'text-muted-foreground',
                  )}
                >
                  {option.shortcut}
                </span>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </div>
  );
}

function Card3() {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount: 0.3 });

  return (
    <div ref={ref} className="relative overflow-hidden px-5 pb-5 lg:h-full">
      <div className="absolute">
        <span className="text-muted-foreground text-xl">Successful Runs</span>
        <span className="flex items-center gap-3">
          {isInView && (
            <NumberTicker
              startValue={3600}
              value={3812}
              className="text-4xxl font-bold"
            />
          )}
          <Badge variant="info" className="rounded-full text-sm">
            +6%
          </Badge>
        </span>
      </div>
      {isInView && (
        <ChartContainer
          config={{
            runs: {
              label: 'Runs',
              color: 'var(--chart-2)',
            },
          }}
          className="h-full"
        >
          <AreaChart
            data={[
              { month: 'Jan', runs: 2000 },
              { month: 'Feb', runs: 3100 },
              { month: 'Mar', runs: 3600 },
              { month: 'Apr', runs: 3400 },
              { month: 'May', runs: 4600 },
              { month: 'Jun', runs: 5000 },
              { month: 'Jul', runs: 6812 },
            ]}
          >
            <defs>
              <linearGradient id="runGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--chart-2)"
                  stopOpacity={0.4}
                />
                <stop
                  offset="100%"
                  stopColor="var(--chart-2)"
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <Area
              dataKey="runs"
              stroke="var(--chart-2)"
              fill="url(#runGradient)"
              strokeWidth={2}
              dot={false}
              type="monotone"
            />
          </AreaChart>
        </ChartContainer>
      )}
    </div>
  );
}

function Card4() {
  const ref = useRef<HTMLDivElement>(null);
  const integrationLogos = [
    { icon: FaSlack, name: 'Slack', color: '#4A154B' },
    { icon: FaGithub, name: 'GitHub', color: '#909090' },
    { icon: FaGoogle, name: 'Google', color: '#4285F4' },
    { icon: FaAws, name: 'AWS', color: '#FF9900' },
    { icon: FaMicrosoft, name: 'Microsoft', color: '#00A1F1' },
    { icon: FaDiscord, name: 'Discord', color: '#5865F2' },
    { icon: FaLinkedin, name: 'LinkedIn', color: '#0A66C2' },
    { icon: FaTwitter, name: 'Twitter', color: '#1DA1F2' },
    { icon: FaFigma, name: 'Figma', color: '#F24E1E' },
    { icon: FaDropbox, name: 'Dropbox', color: '#0061FF' },
    { icon: FaSpotify, name: 'Spotify', color: '#1DB954' },
    { icon: FaTrello, name: 'Trello', color: '#0079BF' },
    { icon: FaApple, name: 'Apple', color: '#000000' },
    { icon: FaStripe, name: 'Stripe', color: '#635BFF' },
    { icon: FaSalesforce, name: 'Salesforce', color: '#00A1E0' },
    { icon: FaMailchimp, name: 'Mailchimp', color: '#FFE01B' },
    { icon: FaIntercom, name: 'Intercom', color: '#0049C7' },
    { icon: FaShopify, name: 'Shopify', color: '#7AB55C' },
  ];

  return (
    <div ref={ref} className="relative h-full overflow-hidden">
      <div className="grid w-fit grid-cols-9 gap-1 sm:gap-x-2 sm:gap-y-3 md:grid-cols-6">
        {integrationLogos.map((logo, index) => (
          <motion.div
            key={logo.name}
            className="bg-muted/40 hover:bg-accent/50 flex aspect-square size-6 items-center justify-center rounded-sm border transition-colors sm:size-8.5"
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{
              duration: 0.3,
              delay: index * 0.05,
              ease: 'easeOut',
            }}
          >
            <logo.icon className="size-2.5" fill={logo.color} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function Card5() {
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div className="relative">
      <motion.div
        ref={ref}
        className="after:bg-accent relative overflow-hidden rounded-sm before:absolute before:inset-0 before:bg-gradient-to-tr before:from-[var(--chart-1)]/10 before:via-[var(--chart-2)] before:to-[var(--chart-3)] after:absolute after:inset-[1px] after:rounded-sm"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{
          duration: 0.5,
          ease: 'easeOut',
        }}
      >
        <div className="relative z-10 space-y-1.5 px-3 py-2.5">
          {/* Title with folder icon */}
          <motion.div
            className="flex items-center gap-1.5"
            initial={{ opacity: 0, x: -15 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{
              duration: 0.4,
              delay: 0.2,
              ease: 'easeOut',
            }}
          >
            <Folder className="fill-destructive text-destructive size-3" />
            <h3 className="text-[0.625rem] font-bold">File Watcher</h3>
          </motion.div>

          {/* Description with check icon */}
          <motion.div
            className="flex items-center gap-1.5"
            initial={{ opacity: 0, x: -15 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{
              duration: 0.4,
              delay: 0.3,
              ease: 'easeOut',
            }}
          >
            <BadgeCheck className="size-3 text-emerald-500" />
            <p className="text-muted-foreground text-[0.625rem]">
              New change in file or new file in folder?
            </p>
          </motion.div>
        </div>
      </motion.div>
      <motion.p
        className="text-muted-foreground mt-4 text-[0.625rem]"
        initial={{ opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{
          duration: 0.4,
          delay: 0.4,
          ease: 'easeOut',
        }}
      >
        AI Action:{' '}
        <span className="text-gradient">Trigger new lead automation flow</span>
      </motion.p>
      <motion.div
        className="bg-accent absolute right-0 bottom-0 z-10 -translate-x-1/4 translate-y-1/4 rounded-sm border border-s border-t p-2 shadow-xl lg:right-auto lg:left-0"
        initial={{ opacity: 0, x: 30, y: -30 }}
        whileInView={{ opacity: 1, x: 0, y: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{
          duration: 0.6,
          delay: 0.5,
          ease: [0.25, 0.46, 0.45, 0.94],
        }}
      >
        <div className="text-muted-foreground text-[0.625rem]">
          Successful Run
        </div>
        <div className="mt-1 flex items-center gap-1.5">
          <NumberTicker startValue={3600} value={3812} className="text-sm" />
          <span className="rounded-full bg-green-600/10 px-1.5 py-0.25 text-[0.6rem] font-medium text-green-600">
            +6%
          </span>
        </div>
      </motion.div>
    </div>
  );
}
