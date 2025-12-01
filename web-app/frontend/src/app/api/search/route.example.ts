// Example route for SERVER-SIDE search functionality (non-static)
//
// This is an example of how to set up server-side search that PREVENTS static export.
// The current route.ts uses staticGET for static export compatibility.
//
// To switch to server-side search:
// 1. Replace the contents of route.ts with this code
// 2. Update src/components/docs/overview.tsx to use type: 'fetch' instead of 'static'
// 3. Remove the initOrama import and function from the component
// 4. Note: This will prevent static export (cannot use output: 'export' in next.config.js)

import { createFromSource } from 'fumadocs-core/search/server';

import { source } from '@/lib/source';

export const { GET } = createFromSource(source, {
  // https://docs.orama.com/open-source/supported-languages
  language: 'english',
});
