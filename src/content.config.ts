import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// One Markdown file per internal paper page: src/content/projects/<slug>.md.
// Title, authors, venue and abstract come from the publication data (`pub` id);
// the frontmatter only adds what is specific to the page.
const figure = z.object({ src: z.string(), caption: z.string().optional(), wide: z.boolean().optional() });

const projects = defineCollection({
  loader: glob({ pattern: '*.md', base: './src/content/projects' }),
  schema: z.object({
    pub: z.string(),
    draft: z.boolean().default(false),
    auto: z.boolean().optional(), // created by the sync script
    tldr: z.string().optional(),
    teaser: figure.optional(),
    video: z
      .object({ src: z.string(), poster: z.string().optional(), caption: z.string().optional() })
      .optional(),
    // Side-by-side comparisons, e.g. gradient descent vs. ours.
    comparisons: z
      .object({
        title: z.string().optional(),
        caption: z.string().optional(),
        labels: z.tuple([z.string(), z.string()]),
        rows: z.array(z.object({ name: z.string(), left: z.string(), right: z.string() })),
      })
      .optional(),
    figures: z.array(figure).default([]),
  }),
});

export const collections = { projects };
