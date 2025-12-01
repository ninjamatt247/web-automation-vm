import fs from 'fs';
import matter from 'gray-matter';
import path from 'path';

// Types for changelog entries
export type ChangelogEntry = {
  id: string;
  date: string;
  title: string;
  content: string;
  image?: string;
};

const CHANGELOG_DIR = path.join(process.cwd(), '/content/changelog');

/**
 * Get all changelog entries sorted by date (newest first)
 * @returns Array of changelog entries
 */
export async function getChangelogEntries(): Promise<ChangelogEntry[]> {
  // Check if changelog directory exists
  if (!fs.existsSync(CHANGELOG_DIR)) {
    return [];
  }

  // Read all MDX files from the changelog directory
  const files = fs
    .readdirSync(CHANGELOG_DIR)
    .filter((file) => file.endsWith('.mdx'));

  // Process each MDX file
  const entries: ChangelogEntry[] = files
    .map((file) => {
      const filePath = path.join(CHANGELOG_DIR, file);
      const fileContent = fs.readFileSync(filePath, 'utf8');

      // Parse frontmatter and content
      const { data: frontmatter, content } = matter(fileContent);

      // Validate required frontmatter fields
      if (!frontmatter.title || !frontmatter.date || !frontmatter.id) {
        console.warn(
          `Skipping changelog entry ${file}: missing required frontmatter fields`,
        );
        return null;
      }

      // Check if content contains an image
      const imageMatch = content.match(/!\[.*?\]\((.*?)\)/);
      const image = imageMatch ? imageMatch[1] : undefined;

      return {
        id: frontmatter.id,
        date: frontmatter.date,
        title: frontmatter.title,
        content: content.trim(),
        image,
      };
    })
    .filter(Boolean) as ChangelogEntry[];

  // Sort entries by date (newest first)
  return entries.sort((a, b) => {
    // Extract year from date string (format: "MMM DD YYYY")
    const yearA = parseInt(a.date.split(' ')[2]);
    const yearB = parseInt(b.date.split(' ')[2]);

    if (yearA !== yearB) return yearB - yearA;

    // If same year, compare by month
    const monthA = a.date.split(' ')[0];
    const monthB = b.date.split(' ')[0];
    const months = [
      'JAN',
      'FEB',
      'MAR',
      'APR',
      'MAY',
      'JUN',
      'JUL',
      'AUG',
      'SEP',
      'OCT',
      'NOV',
      'DEC',
    ];

    const monthIndexA = months.indexOf(monthA);
    const monthIndexB = months.indexOf(monthB);

    if (monthIndexA !== monthIndexB) return monthIndexB - monthIndexA;

    // If same month, compare by day
    const dayA = parseInt(a.date.split(' ')[1]);
    const dayB = parseInt(b.date.split(' ')[1]);

    return dayB - dayA;
  });
}

/**
 * Get a specific changelog entry by ID
 * @param id The ID of the changelog entry to retrieve
 * @returns The changelog entry or null if not found
 */
export async function getChangelogEntryById(
  id: string,
): Promise<ChangelogEntry | null> {
  const entries = await getChangelogEntries();
  return entries.find((entry) => entry.id === id) || null;
}
