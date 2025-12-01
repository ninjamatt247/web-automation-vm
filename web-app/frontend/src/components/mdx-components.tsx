// Import individual fumadocs-ui components
import { Accordion, Accordions } from 'fumadocs-ui/components/accordion';
import { Banner } from 'fumadocs-ui/components/banner';
import { CodeBlock, Pre } from 'fumadocs-ui/components/codeblock';
import { File, Files, Folder } from 'fumadocs-ui/components/files';
import { Step, Steps } from 'fumadocs-ui/components/steps';
import { Tab, Tabs } from 'fumadocs-ui/components/tabs';
import { TypeTable } from 'fumadocs-ui/components/type-table';
import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { MDXComponents } from 'mdx/types';

import { Badge } from './ui/badge';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from './ui/card';

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    // Fumadocs UI Components (following recommended structure)
    Accordion,
    Accordions,
    Banner,
    CodeBlock,
    Files,
    File,
    Folder,
    Step,
    Steps,
    Tab,
    Tabs,
    TypeTable,
    // Custom components using your design system
    Badge,
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    // Enhanced code blocks with proper responsive behavior and background
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    pre: ({ ref: _ref, ...props }) => (
      <CodeBlock {...props}>
        <Pre>{props.children}</Pre>
      </CodeBlock>
    ),
    // Custom callouts using semantic tokens
    blockquote: ({ children, ...props }) => (
      <blockquote
        className="border-accent bg-muted/20 text-muted-foreground rounded-r-lg border-l-4 py-2 pl-4 italic"
        {...props}
      >
        {children}
      </blockquote>
    ),
    ...components,
  };
}

// Default export for Next.js MDX
export default getMDXComponents;
