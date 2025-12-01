import { createFromSource } from 'fumadocs-core/search/server';

import { source } from '@/lib/source';

// Static search for static export compatibility
// This generates search indexes at build time that can be downloaded by the client
export const revalidate = false;

export const { staticGET: GET } = createFromSource(source, {
  // https://docs.orama.com/open-source/supported-languages
  language: 'english',
});
