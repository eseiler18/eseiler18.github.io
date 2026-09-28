// Merged CV data (profile + cv.yaml + publications with overrides), written to
// dist/cv/data.json at build time. The Typst templates in cv/ read this file,
// so the PDFs use exactly the same content as the website.
import type { APIRoute } from 'astro';
import { profile, cv, getPublications, isMe, venueLine } from '../../lib/data';

export const GET: APIRoute = async ({ site }) => {
  const pubs = await getPublications();
  const abs = (href: string) => new URL(href, site).toString();
  const data = {
    site: site?.toString().replace(/\/$/, '') ?? '',
    profile: {
      name: profile.name,
      role: profile.role,
      affiliation: profile.affiliation,
      location: profile.location,
      interests: profile.interests,
      links: profile.links,
    },
    cv,
    publications: pubs.map((p) => ({
      title: p.title,
      authors: p.authors.map((a) => ({ name: a, me: isMe(a), equal: p.equalContribution.includes(a) })),
      venue: venueLine(p),
      venueShort: p.venueShort,
      year: p.year,
      featured: p.featured,
      firstAuthor: p.firstAuthor,
      url: abs(p.href),
    })),
  };
  return new Response(JSON.stringify(data, null, 2), { headers: { 'Content-Type': 'application/json' } });
};
