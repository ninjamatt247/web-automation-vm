import { Bell } from 'lucide-react';
import { MDXRemote } from 'next-mdx-remote/rsc';
import remarkGfm from 'remark-gfm';

import { Button } from '@/components/ui/button';
import { getChangelogEntries } from '@/lib/changelog';
import { cn } from '@/lib/utils';

// MDX components for rendering
const components = {
  h2: ({ children }: { children: React.ReactNode }) => (
    <h3 className="text-accent-foreground mt-6 mb-3 text-lg font-medium">
      {children}
    </h3>
  ),
  p: ({ children }: { children: React.ReactNode }) => (
    <p className="text-muted-foreground text-base leading-relaxed md:text-lg">
      {children}
    </p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul className="text-muted-foreground text-base md:text-lg">{children}</ul>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li className="flex items-center gap-3">
      <span className="bg-muted-foreground flex size-1.5 rounded-full" />
      <span>{children}</span>
    </li>
  ),
  img: ({ src, alt }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} className="my-4 invert dark:invert-0" />
  ),
};

export default async function ChangelogPage() {
  const changelogEntries = await getChangelogEntries();

  return (
    <section className="section-padding container max-w-5xl space-y-24">
      {/* Dark header banner */}
      <div className="flex flex-wrap items-center justify-between gap-10">
        <div className="space-y-3">
          <h1 className="text-4xxl leading-tight font-medium tracking-tight">
            Changelog
          </h1>
          <p className="text-muted-foreground text-lg leading-snug">
            New updates and product improvements
          </p>
        </div>
        <Button
          variant="muted"
          size="sm"
          className="bg-muted/40 h-12 gap-2 !px-4 text-base font-normal"
        >
          Subscribe for updates
          <Bell className="h-4 w-4" />
        </Button>
      </div>

      <div className="[--sidebar-width:150px]">
        {/* Changelog entries with timeline */}
        <div className="relative">
          {changelogEntries.map((entry, index) => (
            <div key={entry.id} className="flex gap-5 md:gap-12">
              {/* Date column with dot */}
              <div className="relative mt-0.5 shrink-0 md:mt-1.5 md:w-[var(--sidebar-width)]">
                <time className="text-muted-foreground hidden md:inline-block">
                  {entry.date}
                </time>
                <div className="bg-background border-input absolute top-0 right-0 z-10 grid size-5 translate-x-1/2 place-items-center rounded-full border">
                  <div className="bg-secondary size-2 rounded-full" />
                </div>
                <div className="absolute top-0 right-0 h-full w-0.25 bg-[repeating-linear-gradient(to_bottom,var(--input)_0px,var(--input)_8px,transparent_12px,transparent_20px)]" />
              </div>

              {/* Content */}
              <div
                className={cn(
                  'mb-16 flex-1',
                  index === changelogEntries.length - 1 && 'mb-0',
                )}
              >
                <time className="text-muted-foreground mb-10 inline-block md:hidden">
                  {entry.date}
                </time>
                <h2 className="text-2xl leading-tight font-medium">
                  {entry.title}
                </h2>

                {/* MDX Content */}
                <div className="mt-4 space-y-4">
                  <MDXRemote
                    source={entry.content}
                    components={components}
                    options={{
                      mdxOptions: {
                        remarkPlugins: [remarkGfm],
                      },
                    }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end">
          <Button
            variant="muted"
            className="mt-25 h-12 w-full md:w-[calc(100%-var(--sidebar-width))]"
          >
            Load more
          </Button>
        </div>
      </div>
    </section>
  );
}
