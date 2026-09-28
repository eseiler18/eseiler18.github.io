# eseiler18.github.io

Personal academic website built with [Astro](https://astro.build) and hosted on GitHub Pages.

```bash
npm install
npm run dev        # http://localhost:4321 (draft pages are visible in dev)
npm run build      # static site in dist/
npm run preview
```

## Where things live

| What | File |
|---|---|
| Name, bio, links, research interests | `src/data/profile.yaml` |
| News (home page) | `src/data/news.yaml` |
| CV page (education, awards, experience, skills) | `src/data/cv.yaml` |
| PDF CV (1 page) | generated from `cv.yaml` by `cv/resume.typ` (see below) |
| Publications (**generated**, do not edit) | `src/data/publications.json` |
| Manual corrections on publications | `src/data/publications.overrides.yaml` |
| Co-author homepages | `src/data/coauthors.yaml` |
| Paper pages | `src/content/projects/<slug>.md` + assets in `public/projects/<slug>/` |
| Colors, fonts | `src/styles/global.css` (top of file) |

## Publications and paper pages

- **First-author papers** get an internal page (`/projects/<slug>`). All other papers link out, in this order: the `project_url` override (e.g. the first author's project site), then arXiv, then the DOI.
- The `page: true|false` override forces a page on or off, e.g. for equal contribution.
- Title, authors, venue and abstract come from the publication data. The Markdown page adds the TL;DR, a teaser, a video, comparisons, figures, and free Markdown content. See `fcso.md` for a full example.

### Automatic sync

`.github/workflows/sync-publications.yml` runs `scripts/sync_scholar.py` every Monday. You can also start it by hand from the Actions tab.

1. The script queries OpenAlex and Google Scholar, then merges the results into `publications.json`. It adds and updates entries but never removes them.
2. For each new paper, it tries to add:
   - the **project page / code links** found in the arXiv comment or abstract;
   - an **illustration**, i.e. Figure 1 extracted from the arXiv or open-access PDF, saved to `public/projects/<slug>/thumbnail.jpg`.
3. If I am **first author**, it publishes a page directly: `src/content/projects/<id>.md`, marked `auto: true`. You can edit that file freely afterwards; existing pages are never overwritten.
4. If I am **not first author**, the paper links to the project page if one was found, otherwise to arXiv, otherwise to the DOI.
5. It commits the changes, redeploys the site, and opens **one GitHub issue per new paper**.

### Email review

- Each issue mentions `@eseiler18`, so GitHub sends you an email.
- **Reply to the email**:
  - **"non"** (or no / refusé / remove): the paper is hidden (`hidden: true` in the overrides), its automatic page and images are deleted, and the site is redeployed.
  - **"oui"** (or ok / yes): the issue is closed and the paper stays.
- No reply: the paper stays online.
- Handled by `.github/workflows/review-publication.yml` and `scripts/review.py`. Only comments from the repository owner are taken into account.
- The emails go to GitHub's **Default notification email**. To change it, go to **Settings → Notifications**; the address must first be added and verified in **Settings → Emails**.

Run the sync locally:

```bash
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/sync_scholar.py --dry-run
```

### Adding a paper by hand (before it is indexed)

Add an entry with `manual: true` in `publications.overrides.yaml`, giving at least `title`, `authors`, `year` and `venue`.

## PDF CV

The 1-page PDF CV is generated from the same data as the `/cv` page (`src/data/cv.yaml` + publications), with [Typst](https://typst.app). The layout lives in `cv/resume.typ` + `cv/template.typ`, and the fonts in `cv/fonts/`. In `cv.yaml`, `resume: false` leaves an entry out of the PDF and `short:` gives a one-line version.

- `npm run build` (also run by the deploy workflow) builds the site and then `dist/cv/Emilien_Seiler_CV.pdf`. It is published **without a phone number**.
- `npm run cv:private` builds a version **with your phone number** into `cv/out/`, for applications. The number comes from `cv/private.yaml` (`phone: "+41 ..."`). That file is git-ignored and never published.
- Requires Typst locally: `brew install typst`.

## Deploying

1. Create a GitHub repository named `eseiler18.github.io`, then push this folder to it (branch `main`).
2. In the repository, go to **Settings → Pages → Source** and select **GitHub Actions**.
3. `.github/workflows/deploy.yml` builds and publishes the site on every push to `main`.
4. For a custom domain, set `site` in `astro.config.mjs` and add `public/CNAME`.
