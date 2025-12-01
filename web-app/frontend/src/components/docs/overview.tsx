'use client';

import { create } from '@orama/orama';
import { motion } from 'framer-motion';
import { useDocsSearch } from 'fumadocs-core/search/client';
import {
  BookOpen,
  Bug,
  Cpu,
  FileText,
  Hash,
  Package,
  Search,
  Terminal,
  X,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';

const QUICK_START_SECTIONS = [
  {
    title: 'Installation',
    description:
      'Get started with Plasma by installing the necessary dependencies and setting up your environment.',
    icon: Package,
    href: '/docs/installation',
  },
  {
    title: 'Core Concepts',
    description:
      'Learn the fundamental concepts and architecture behind Plasma to build better applications.',
    icon: BookOpen,
    href: '/docs/core-concepts',
  },
  {
    title: 'AI Prompts',
    description:
      'Discover how to leverage AI capabilities and create effective prompts for your use cases.',
    icon: Cpu,
    href: '/docs/ai-prompts',
  },
  {
    title: 'File Systems',
    description:
      'Understand how to manage and organize files efficiently within the Plasma ecosystem.',
    icon: FileText,
    href: '/docs/file-systems',
  },
  {
    title: 'CRM CSV',
    description:
      'Learn how to manage and import CRM data using CSV files for efficient data processing.',
    icon: Bug,
    href: '/docs/crm-csv',
  },
  {
    title: 'CLI Commands',
    description:
      'Master the command-line interface and available commands for efficient development.',
    icon: Terminal,
    href: '/docs/cli',
  },
];

const POPULAR_SEARCHES = ['Billing', 'AI Build', 'Integrations'];

// Initialize Orama for static search mode
function initOrama() {
  return create({
    schema: { _: 'string' },
    // https://docs.orama.com/open-source/supported-languages
    language: 'english',
  });
}

export function DocsOverview() {
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const { search, setSearch, query } = useDocsSearch({
    type: 'static', // Uses client-side search for static export compatibility
    initOrama,
  });

  // Handle global Cmd+K to open our custom search instead of default Fumadocs search
  useEffect(() => {
    const handleGlobalKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        event.stopPropagation();
        setIsSearchExpanded(true);
      }
    };

    // Add event listener with capture to intercept before other handlers
    document.addEventListener('keydown', handleGlobalKeyDown, true);

    return () => {
      document.removeEventListener('keydown', handleGlobalKeyDown, true);
    };
  }, []);

  return (
    <div className="text-center">
      <div className="mx-auto flex max-w-2xl flex-1 flex-col items-center gap-5">
        <div className="flex items-center rounded-full border p-1 text-xs">
          <span className="bg-muted rounded-full px-3 py-1">
            What&apos;s New?
          </span>
          <span className="px-3">Join the next workshop on May 6</span>
        </div>

        <h1 className="!mb-0 text-balance text-4xl leading-none md:text-5xl lg:text-6xl">
          Welcome to the <span className="text-gradient">Plasma Docs</span>
        </h1>

        <p className="text-muted-foreground !my-0 leading-snug md:text-lg">
          Get answers to common questions on all things Plasma
        </p>
      </div>
      <div className="mx-auto mt-10 max-w-xl md:mt-12">
        <InlineSearchDialog
          search={search}
          setSearch={setSearch}
          query={query}
          isExpanded={isSearchExpanded}
          onExpand={() => setIsSearchExpanded(true)}
          onClose={() => setIsSearchExpanded(false)}
        />

        {/* Popular Searches - only show when not expanded */}
        <div className="mt-3 flex items-center justify-center gap-3 text-start">
          <div className="text-sm">Popular searches</div>
          <div className="flex justify-center gap-3">
            {POPULAR_SEARCHES.map((tag) => (
              <Badge
                key={tag}
                variant="muted"
                className="bg-muted/40 rounded-sm border-0"
              >
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Getting Started Section */}
      <div className="mt-18 md:mt-21 mx-auto grid gap-4 text-start md:grid-cols-2 lg:grid-cols-3">
        {QUICK_START_SECTIONS.map((section, index) => {
          const IconComponent = section.icon;
          return (
            <Link key={index} href={section.href} className="no-underline">
              <Card className="hover:bg-muted/20 bg-muted/40 group h-full cursor-pointer gap-3 transition-colors">
                <CardHeader className="gap-2.5">
                  <IconComponent className="size-6" />
                  <CardTitle className="text-lg">{section.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-muted-foreground text-base">
                    {section.description}
                  </CardDescription>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function InlineSearchDialog({
  search,
  setSearch,
  query,
  isExpanded,
  onExpand,
  onClose,
}: {
  search: string;
  setSearch: (value: string) => void;
  query: { data?: unknown[] | 'empty' };
  isExpanded: boolean;
  onExpand: () => void;
  onClose: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isExpanded]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleInputClick = () => {
    if (!isExpanded) {
      onExpand();
    }
  };

  return (
    <div className="relative text-start">
      <motion.div
        layoutId="search-container"
        className="bg-muted/40 relative h-12 w-full rounded-md"
      >
        <Input
          ref={inputRef}
          placeholder="Search guide"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          onClick={handleInputClick}
          readOnly={!isExpanded}
          className="!focus-visible:ring-0 text-foreground placeholder:text-muted-foreground h-full cursor-pointer !border-none !bg-transparent ps-12 !shadow-none"
        />
        <Search className="absolute left-6 top-1/2 size-4 -translate-y-1/2" />
        {isExpanded ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-muted-foreground absolute right-4 top-1/2 -translate-y-1/2 !px-0"
          >
            <X className="h-4 w-4" />
          </Button>
        ) : (
          <kbd className="text-muted-foreground pointer-events-none absolute right-4 top-1/2 inline-flex -translate-y-1/2 transform select-none items-center gap-1 rounded border border-none py-1.5 text-xs">
            ⌘<span className=""> K</span>
          </kbd>
        )}
      </motion.div>

      {/* Search Results Dropdown */}
      {isExpanded && search.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.15 }}
          className="bg-muted/20 absolute left-0 right-0 top-full z-50 mt-2 max-h-96 overflow-y-auto rounded-md border shadow-lg backdrop-blur-sm"
        >
          <div className="p-2">
            {query.data &&
            Array.isArray(query.data) &&
            query.data.length > 0 ? (
              <div className="space-y-2">
                {query.data.map((result: unknown, index: number) => {
                  const item = result as {
                    id?: string;
                    url?: string;
                    content?: string;
                    type?: string;
                  };

                  // Parse the actual Fumadocs search result format
                  const title =
                    item.content ||
                    item.id?.split('/').pop()?.replace(/-/g, ' ') ||
                    'Untitled';
                  const url = item.url || item.id || '#';
                  const isPage = item.type === 'page';

                  // For page types, use a cleaner title format
                  const displayTitle = isPage
                    ? title
                        .split(' ')
                        .map(
                          (word) =>
                            word.charAt(0).toUpperCase() + word.slice(1),
                        )
                        .join(' ')
                    : title;

                  return (
                    <Link
                      key={index}
                      href={url}
                      className="hover:bg-muted/40 block rounded-md p-3 no-underline transition-colors"
                      onClick={onClose}
                    >
                      <div className="flex items-start gap-3">
                        <div className="text-muted-foreground mt-0.5 flex-shrink-0">
                          {item.type === 'page' ? (
                            <FileText className="h-4 w-4" />
                          ) : (
                            <Hash className="h-4 w-4" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="text-sm font-medium">
                            {displayTitle}
                          </div>
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            ) : (
              <div className="text-muted-foreground py-8 text-center text-sm">
                No results found for &ldquo;{search}&rdquo;
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
