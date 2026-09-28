import fs from 'node:fs';
import path from 'node:path';
import { load } from 'js-yaml';
import { getCollection } from 'astro:content';

const DATA = path.resolve('src/data');
const readYaml = <T>(file: string): T => load(fs.readFileSync(path.join(DATA, file), 'utf8')) as T;

// ---------------------------------------------------------------- simple data files
export interface Profile {
  name: string;
  role: string;
  affiliation: string;
  affiliation_url: string;
  advisor: string;
  advisor_url: string;
  location: string;
  photo?: string;
  bio: string[];
  interests: string[];
  name_variants: string[];
  links: Record<'email' | 'scholar' | 'github' | 'linkedin' | 'orcid' | 'cv', string>;
}
export interface NewsItem { date: string; text: string }
export interface CvEntry { period: string; title: string; org?: string; place?: string; details?: string[] }
export interface Cv {
  education: CvEntry[];
  awards: CvEntry[];
  experience: CvEntry[];
  teaching: CvEntry[];
  skills: { group: string; items: string[] }[];
}

export const profile = readYaml<Profile>('profile.yaml');
export const news = readYaml<NewsItem[]>('news.yaml');
export const cv = readYaml<Cv>('cv.yaml');
export const coauthors = readYaml<Record<string, string>>('coauthors.yaml') ?? {};

/** A link is usable when set, not a TODO placeholder, and uses a safe scheme
 * (URLs partly come from external sources: never allow javascript: or data: links). */
export const isSet = (url?: string) =>
  !!url && !url.includes('TODO') && /^(https?:\/\/|mailto:|\/(?!\/)|#)/i.test(url.trim());

// ---------------------------------------------------------------- publications
export interface Publication {
  id: string;
  slug: string;
  title: string;
  authors: string[];
  year: number;
  date: string;
  venue: string;
  venueShort: string;
  type: string;
  doi: string;
  arxiv: string;
  url: string;
  abstract: string;
  citations: number;
  featured: boolean;
  thumbnail?: string;
  equalContribution: string[];
  links: Record<string, string>;
  bibtex: string;
  firstAuthor: boolean;
  /** Internal page when it exists, else the best external page. */
  href: string;
  external: boolean;
  hasPage: boolean;
}

const squash = (s: string) => s.toLowerCase().normalize('NFD').replace(/[^a-z]/g, '');
const myNames = new Set(profile.name_variants.map(squash));
export const isMe = (name: string) => myNames.has(squash(name));

function bibtexFor(p: Publication): string {
  const last = (p.authors[0] ?? 'anon').split(' ').pop()!.toLowerCase().normalize('NFD').replace(/[^a-z]/g, '');
  const key = `${last}${p.year}${p.title.split(/\W+/)[0].toLowerCase()}`;
  const authors = p.authors
    .map((a) => {
      const parts = a.trim().split(/\s+/);
      return parts.length > 1 ? `${parts.pop()}, ${parts.join(' ')}` : a;
    })
    .join(' and ');
  const preprint = p.type === 'preprint';
  const kind = preprint || /journal|reports|nature|science|studies/i.test(p.venue) ? 'article' : 'inproceedings';
  const fields: [string, string][] = [
    ['title', p.title],
    ['author', authors],
    [kind === 'article' ? 'journal' : 'booktitle', preprint && p.arxiv ? `arXiv preprint arXiv:${p.arxiv}` : p.venue],
    ['year', String(p.year)],
  ];
  if (p.doi) fields.push(['doi', p.doi]);
  const width = Math.max(...fields.map(([k]) => k.length));
  return `@${kind}{${key},\n${fields.map(([k, v]) => `  ${k.padEnd(width)} = {${v}}`).join(',\n')}\n}`;
}

const isPreprint = (p: Publication) =>
  p.type === 'preprint' || /arxiv|preprint|research square|biorxiv|medrxiv/i.test(p.venue);

/** "NeurIPS 2026", "Scientific Reports, 2024", or just "2025" for preprints. */
export const venueLine = (p: Publication) =>
  !p.venue ? String(p.year) : /\d{4}/.test(p.venue) ? p.venue : `${p.venue}, ${p.year}`;

let cache: Publication[] | undefined;

/** Publications from the sync, merged with manual overrides, newest first. */
export async function getPublications(): Promise<Publication[]> {
  if (cache) return cache;
  const synced = JSON.parse(fs.readFileSync(path.join(DATA, 'publications.json'), 'utf8')).publications as any[];
  const overrides: Record<string, any> = readYaml<any>('publications.overrides.yaml')?.publications ?? {};
  const pages = new Set(
    (await getCollection('projects', ({ data }) => import.meta.env.DEV || !data.draft)).map((e) => e.id),
  );

  const raw = [
    ...synced,
    ...Object.entries(overrides)
      .filter(([id, o]) => o?.manual && !synced.some((s) => s.id === id))
      .map(([id]) => ({ id })),
  ];

  cache = raw
    .map((s) => {
      const o = overrides[s.id] ?? {};
      if (o.hidden) return null;
      const p = { ...s, ...o } as any;
      const authors: string[] = p.authors ?? [];
      const firstAuthor = authors.length > 0 && isMe(authors[0]);
      const slug: string = o.slug ?? s.id;
      const wantsPage: boolean = o.page ?? firstAuthor;
      const hasPage = wantsPage && pages.has(slug);
      const arxivUrl = p.arxiv ? `https://arxiv.org/abs/${p.arxiv}` : '';
      const doiUrl = p.doi ? `https://doi.org/${p.doi}` : '';
      // project_url / code may come from the sync (found on arXiv) or from the overrides.
      const externalHref = [p.project_url, arxivUrl, doiUrl, p.url].find(isSet) ?? '#';

      const pub: Publication = {
        id: s.id,
        slug,
        title: p.title,
        authors,
        year: p.year,
        date: p.date ?? '',
        venue: p.venue ?? '',
        venueShort: p.venue_short ?? '',
        type: p.type ?? 'paper',
        doi: p.doi ?? '',
        arxiv: p.arxiv ?? '',
        url: p.url ?? '',
        abstract: p.abstract ?? '',
        citations: p.citations ?? 0,
        featured: !!p.featured,
        thumbnail: p.thumbnail,
        equalContribution: p.equal_contribution ?? [],
        links: {
          ...(arxivUrl && { arXiv: arxivUrl }),
          ...(doiUrl && { Paper: doiUrl }),
          ...(isSet(p.project_url) && { Project: p.project_url }),
          ...(isSet(s.code) && { Code: s.code }),
          ...Object.fromEntries(
            Object.entries(o.links ?? {})
              .filter(([, v]) => isSet(v as string))
              .map(([k, v]) => [k[0].toUpperCase() + k.slice(1), v as string]),
          ),
        },
        bibtex: '',
        firstAuthor,
        href: hasPage ? `/projects/${slug}` : externalHref,
        external: !hasPage,
        hasPage,
      };
      pub.bibtex = (o.bibtex as string | undefined)?.trim() ?? bibtexFor(pub);
      // Preprints: no "arXiv preprint" label on the site (the arXiv button is enough).
      // The BibTeX above still cites them properly.
      if (isPreprint(pub)) {
        pub.venue = '';
        pub.venueShort = '';
      }
      return pub;
    })
    .filter((p): p is Publication => p !== null)
    .sort((a, b) => (b.date || String(b.year)).localeCompare(a.date || String(a.year)));
  return cache;
}

export async function getPublicationById(id: string) {
  return (await getPublications()).find((p) => p.id === id);
}

// ---------------------------------------------------------------- tiny Markdown (inline only)
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
/** Inline Markdown for YAML strings: [links](url), **bold**, *italic*. */
export function md(s: string): string {
  return esc(s)
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => {
      if (!isSet(u)) return t;
      const ext = /^https?:/.test(u);
      return `<a href="${u}"${ext ? ' target="_blank" rel="noopener"' : ''}>${t}</a>`;
    })
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}
