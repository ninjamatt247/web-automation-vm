'use client';

import { ArrowRight, Search } from 'lucide-react';
import { motion } from 'motion/react';
import Link from 'next/link';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Terminal } from '@/components/ui/terminal';

import { Separator } from '../ui/separator';

export default function ProductLogs() {
  return (
    <section className="section-padding container grid max-w-screen-xl gap-8 lg:grid-cols-2">
      {/* Left: Text & Description */}
      <div className="flex flex-col justify-between gap-3">
        <div className="space-y-6">
          <h2 className="text-4xxl leading-none tracking-tight text-balance md:text-6xl lg:max-w-xs">
            Transparent <br className="hidden lg:block" />
            <span className="text-gradient">
              Execution <br className="hidden lg:block" /> Logs
            </span>
          </h2>
          <span className="text-accent-foreground text-xl font-bold">
            Transparent Execution Logs
          </span>
          <p className="text-muted-foreground mt-3 max-w-lg text-lg leading-snug">
            Every run is tracked in detail - from inputs to outputs to runtime
            errors. Perfect for debugging and transparency.
          </p>
          <div>
            <Button
              variant="ghost"
              asChild
              className="group mt-6 h-12 gap-3 !px-0 font-normal transition-opacity hover:!bg-transparent hover:opacity-95 md:mt-12"
            >
              <Link href="#">
                Explore reporting tools
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <Card className="to-muted/30 via-muted/20 flex h-96 flex-1 overflow-hidden rounded-xl bg-gradient-to-t from-transparent p-0 sm:h-132">
        <CardContent className="relative flex items-center justify-center p-0">
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: 20, filter: 'blur(8px)' }}
            whileInView={{ opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' }}
            viewport={{ once: true, amount: 0.5 }}
            transition={{
              duration: 0.5,
              ease: [0.22, 1, 0.36, 1],
              opacity: { duration: 0.35 },
              scale: { duration: 0.5 },
            }}
            className="w-full origin-bottom-right pt-10 pl-20"
          >
            <TerminalWithHeader />
          </motion.div>
        </CardContent>
      </Card>
    </section>
  );
}

function TerminalWithHeader() {
  const [activeTab, setActiveTab] = useState('logs');

  return (
    <div className="relative w-full">
      {/* Background card - shows partially from the left */}
      <Card className="bg-accent absolute top-5 -left-5 h-full w-full overflow-hidden"></Card>

      {/* Main card */}
      <Card className="bg-accent relative z-10 gap-0 overflow-hidden rounded-e-none border-r-0 shadow-xl">
        <CardHeader className="border-border gap-3 border-b">
          <h3 className="text-foreground font-medium">
            Error Logs - New leads
            <br />
            automation
          </h3>
          <div className="flex items-center gap-2">
            <Badge variant="info">Running</Badge>
            <span className="text-muted-foreground text-[0.625rem]">
              Last run: Apr 19, 2025 — 09:08:11
            </span>
          </div>
          <div className="mt-3 flex items-center justify-between gap-10">
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-auto"
            >
              <TabsList className="bg-input/20 h-7 rounded-md">
                <TabsTrigger
                  value="logs"
                  className="dark:data-[state=active]:bg-accent cursor-pointer rounded-sm border-none text-[0.625rem]"
                >
                  Logs
                </TabsTrigger>
                <TabsTrigger
                  value="errors"
                  disabled
                  className="dark:data-[state=active]:bg-accent cursor-pointer rounded-sm border-none text-[0.625rem]"
                >
                  Errors
                </TabsTrigger>
                <Separator
                  orientation="vertical"
                  className="bg-input mx-2 !h-5"
                />
                <TabsTrigger
                  value="payloads"
                  disabled
                  className="dark:data-[state=active]:bg-accent cursor-pointer rounded-sm border-none text-[0.625rem]"
                >
                  Payloads
                </TabsTrigger>
              </TabsList>
            </Tabs>

            <div className="relative w-40">
              <Search className="text-muted-foreground absolute top-1/2 left-3 size-3 -translate-y-1/2" />
              <Input
                placeholder="Filter Logs"
                className="!bg-background/20 border-input/60 h-7 rounded-sm ps-7 !text-[0.625rem] placeholder:opacity-40"
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <Tabs value={activeTab} className="w-full">
            <TabsContent value="logs" className="m-0">
              <Terminal className="w-full rounded-none border-none" />
            </TabsContent>
            <TabsContent value="errors" className="m-0">
              <div className="flex h-80 items-start justify-start p-4">
                <div className="text-muted-foreground text-sm">
                  No errors found
                </div>
              </div>
            </TabsContent>
            <TabsContent value="payloads" className="m-0">
              <div className="flex h-80 items-start justify-start p-4">
                <div className="text-muted-foreground text-sm">
                  Payload data will appear here
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
