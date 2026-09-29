#!/usr/bin/env python3
"""Refresh src/data/publications.json from Google Scholar and OpenAlex.

Google Scholar has no official API and often blocks CI runners, so it is tried first
(if a Scholar ID is configured) and OpenAlex is always queried as well. Results are
merged by normalized title with what is already in publications.json:
entries are added or updated, never deleted. If every source fails, nothing is written.

New papers are enriched automatically:
  - project page / code links found in the arXiv comment or abstract,
  - an illustration (Figure 1 extracted from the arXiv / open-access PDF),
  - for first-authored papers, a published page src/content/projects/<id>.md (marked `auto: true`).
Pages that already exist are never touched.

Usage:
    python3 scripts/sync_scholar.py                       # update files
    python3 scripts/sync_scholar.py --dry-run             # print the result, write nothing
    python3 scripts/sync_scholar.py --report new.json     # also list the added papers (used by CI)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"
PUBS_JSON = DATA / "publications.json"
PROJECTS = ROOT / "src" / "content" / "projects"
PUBLIC = ROOT / "public"
USER_AGENT = "emilienseiler-website-sync/1.0"

# Fields a source may fill in. Order of preference when two sources disagree is
# handled in merge_into(): non-empty values win, published venues beat preprints.
FIELDS = ["title", "authors", "year", "date", "venue", "type", "doi", "arxiv", "url", "pdf", "abstract", "citations"]


# ---------------------------------------------------------------- helpers
def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.lower())


def slugify(title: str, words: int = 6) -> str:
    tokens = re.findall(r"[a-z0-9]+", title.lower())
    return "-".join(tokens[:words])


def is_preprint(pub: dict) -> bool:
    venue = (pub.get("venue") or "").lower()
    return pub.get("type") == "preprint" or "arxiv" in venue or "research square" in venue


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str) -> bytes:
    """Large files (PDFs): curl copes better than urllib with big / throttled responses."""
    return subprocess.run(
        ["curl", "-sSfL", "--retry", "3", "--max-time", "180", "-A", USER_AGENT, url],
        check=True, capture_output=True,
    ).stdout


def http_json(url: str) -> dict:
    return json.loads(http_get(url))


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text()) if path.exists() else None


# ---------------------------------------------------------------- OpenAlex
def openalex_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


def fetch_openalex(cfg: dict) -> list[dict]:
    filters = []
    if cfg.get("openalex_author_id"):
        filters.append(f"author.id:{cfg['openalex_author_id']}")
    elif cfg.get("orcid"):
        filters.append(f"author.orcid:{cfg['orcid']}")
    else:
        return []
    filters.append(f"publication_year:>{cfg.get('min_year', 2000) - 1}")
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {"filter": ",".join(filters), "per-page": 100, "sort": "publication_date:desc"}
    )
    pubs = []
    for w in http_json(url)["results"]:
        loc = w.get("primary_location") or {}
        source = (loc.get("source") or {}).get("display_name") or ""
        doi = (w.get("doi") or "").replace("https://doi.org/", "")
        arxiv = ""
        for l in w.get("locations") or []:
            m = re.search(r"arxiv\.org/abs/([\w.]+?)(v\d+)?$", l.get("landing_page_url") or "")
            if m:
                arxiv = m.group(1)
        if not arxiv and doi.lower().startswith("10.48550/arxiv."):
            arxiv = doi.split("arxiv.", 1)[1]
        pub = {
            "title": w["title"],
            "authors": [a["author"]["display_name"] for a in w["authorships"]],
            "year": w["publication_year"],
            "date": w.get("publication_date") or "",
            "venue": "arXiv" if "arxiv" in source.lower() else source,
            "type": "preprint" if w.get("type") == "preprint" else "paper",
            "doi": "" if doi.lower().startswith("10.48550/") else doi,
            "arxiv": arxiv,
            "url": loc.get("landing_page_url") or "",
            "pdf": (w.get("best_oa_location") or {}).get("pdf_url") or "",
            "abstract": openalex_abstract(w.get("abstract_inverted_index")),
            "citations": w.get("cited_by_count") or 0,
        }
        pubs.append(pub)
    return pubs


# ---------------------------------------------------------------- Google Scholar
def fetch_scholar(cfg: dict, known: set[str]) -> list[dict]:
    if not cfg.get("scholar_id"):
        return []
    from scholarly import scholarly  # imported lazily: optional dependency

    author = scholarly.search_author_id(cfg["scholar_id"])
    author = scholarly.fill(author, sections=["publications"])
    pubs = []
    for p in author.get("publications", []):
        bib = p.get("bib", {})
        title = bib.get("title", "")
        if not title:
            continue
        # Filling a publication costs one request each: only do it for unknown papers.
        if norm_title(title) not in known:
            try:
                p = scholarly.fill(p)
                bib = p.get("bib", {})
            except Exception as exc:  # keep the partial record
                print(f"  scholar: could not fill '{title[:50]}': {exc}", file=sys.stderr)
        authors = [a.strip() for a in re.split(r"\s+and\s+|,\s*", bib.get("author", "")) if a.strip()]
        venue = bib.get("journal") or bib.get("conference") or bib.get("venue") or bib.get("citation") or ""
        if "…" in venue or "..." in venue:  # Scholar truncates long venue names
            venue = ""
        year = int(bib["pub_year"]) if str(bib.get("pub_year", "")).isdigit() else None
        arxiv = ""
        m = re.search(r"arxiv\.org/(?:abs|pdf)/([\w.]+?)(v\d+)?(\.pdf)?$", p.get("eprint_url") or p.get("pub_url") or "")
        if m:
            arxiv = m.group(1)
        pubs.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "type": "preprint" if "arxiv" in venue.lower() else "paper",
            "arxiv": arxiv,
            "url": p.get("pub_url") or "",
            "abstract": bib.get("abstract", ""),
            "citations": p.get("num_citations") or 0,
        })
    return pubs


# ---------------------------------------------------------------- merge
def merge_into(base: dict, new: dict) -> None:
    """Merge `new` into `base` in place. A published version beats a preprint for
    venue/type/doi/url; otherwise empty fields are filled; citations take the max."""
    upgrade = is_preprint(base) and not is_preprint(new)
    for key in FIELDS:
        val = new.get(key)
        if val in (None, "", []):
            continue
        if key == "citations":
            base[key] = max(base.get(key) or 0, val)
        elif key in ("venue", "type", "doi", "url", "year", "date") and upgrade:
            base[key] = val
        elif key == "authors":
            # prefer full names ("Emilien Seiler") over initials ("E Seiler")
            if len(" ".join(val)) > len(" ".join(base.get(key) or [])):
                base[key] = val
        elif not base.get(key):
            base[key] = val


def merge_all(existing: list[dict], batches: list[list[dict]], cfg: dict) -> tuple[list[dict], list[str]]:
    excl = [e.lower() for e in cfg.get("exclude_titles") or []]
    min_year = cfg.get("min_year", 0)
    by_key = {norm_title(p["title"]): p for p in existing}
    new_ids = []
    for batch in batches:
        for pub in batch:
            if any(e in pub["title"].lower() for e in excl):
                continue
            if pub.get("year") and pub["year"] < min_year:
                continue
            key = norm_title(pub["title"])
            if key in by_key:
                merge_into(by_key[key], pub)
            else:
                rec = {"id": slugify(pub["title"])}
                merge_into(rec, pub)
                rec["title"] = pub["title"]
                by_key[key] = rec
                new_ids.append(rec["id"])
                print(f"  + new: {pub['title']}")
    pubs = list(by_key.values())
    for p in pubs:
        for key in FIELDS:
            p.setdefault(key, [] if key == "authors" else 0 if key == "citations" else "")
    pubs.sort(key=lambda p: (p.get("date") or str(p.get("year") or ""), p["title"]), reverse=True)
    return pubs, new_ids


# ---------------------------------------------------------------- enrichment of new papers
URL_RE = re.compile(r"https?://[^\s,;)\]}>\"']+")


def arxiv_text(arxiv_id: str) -> str:
    """Comment + abstract of an arXiv entry (where authors put project / code links)."""
    xml = http_get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}")
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    entry = ET.fromstring(xml).find("a:entry", ns)
    if entry is None:
        return ""
    parts = [entry.findtext("x:comment", "", ns), entry.findtext("a:summary", "", ns)]
    return " ".join(p for p in parts if p)


def find_links(text: str) -> dict:
    """Guess a code repository and a project page from free text."""
    links = {}
    for url in URL_RE.findall(text):
        url = url.rstrip(".")
        if re.search(r"(github|gitlab)\.com/", url):
            links.setdefault("code", url)
        elif not re.search(r"arxiv\.org|doi\.org|creativecommons", url):
            links.setdefault("project_url", url)
    return links


def flatten_transparency(doc, page) -> None:
    """Composite transparent images (soft masks) onto white before rendering. Otherwise
    the renderer blends their edges with the black RGB hidden under the mask, which
    draws thin grey frames around the sub-figures."""
    import io
    from PIL import Image

    for img in page.get_images(full=True):
        xref, smask = img[0], img[1]
        if not smask:
            continue
        try:
            import pymupdf
            rgb = Image.open(io.BytesIO(pymupdf.Pixmap(doc, xref).tobytes("png"))).convert("RGB")
            alpha = Image.open(io.BytesIO(pymupdf.Pixmap(doc, smask).tobytes("png"))).convert("L")
            if alpha.size != rgb.size:
                alpha = alpha.resize(rgb.size)
            flat = Image.composite(rgb, Image.new("RGB", rgb.size, "white"), alpha)
            buf = io.BytesIO()
            flat.save(buf, "PNG")
            page.replace_image(xref, stream=buf.getvalue())
        except Exception as exc:  # keep the original image
            print(f"    (could not flatten image {xref}: {exc})", file=sys.stderr)


def extract_figure(pdf: bytes, out: Path) -> bool:
    """Render 'Figure 1' of a paper (graphics above its caption) to a JPEG thumbnail."""
    try:
        import pymupdf
    except ImportError:
        print("  (pymupdf not installed: no thumbnail)", file=sys.stderr)
        return False
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    for page in list(doc)[:5]:
        cap = next(
            (b for b in page.get_text("blocks") if re.match(r"\s*(Figure|Fig\.?)\s*1\s*[:.|]", b[4])), None
        )
        if not cap:
            continue
        top = max(36, cap[1] - 480)  # a figure is at most ~2/3 of a page tall
        boxes = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
        boxes += [d["rect"] for d in page.get_drawings() if d["rect"].width > 5]
        boxes = [b for b in boxes if b.y1 <= cap[1] + 2 and b.y0 >= top and b.x1 > cap[0] - 60 and b.x0 < cap[2] + 60]
        if not boxes:
            return False
        clip = pymupdf.Rect(boxes[0])
        for b in boxes[1:]:
            clip |= b
        if clip.width * clip.height < 8000:
            return False
        # Labels inside/next to the figure are text, not graphics: grow the box to include them.
        for w in page.get_text("words"):
            r = pymupdf.Rect(w[:4])
            if r.y0 >= clip.y0 - 14 and r.y1 <= cap[1] and r.x0 >= clip.x0 - 30 and r.x1 <= clip.x1 + 30:
                clip |= r
        clip.y1 = min(clip.y1, cap[1] - 6)  # never include the caption itself
        clip = pymupdf.Rect(clip.x0 - 4, clip.y0 - 4, clip.x1 + 4, clip.y1 + 2) & page.rect
        flatten_transparency(doc, page)
        out.parent.mkdir(parents=True, exist_ok=True)
        pix = page.get_pixmap(dpi=180, clip=clip)
        pix.save(str(out), jpg_quality=85)
        return True
    return False


def enrich(pub: dict, slug: str) -> None:
    """Add project/code links and a thumbnail to a newly found paper (best effort)."""
    try:
        text = pub.get("abstract", "")
        if pub.get("arxiv"):
            text = arxiv_text(pub["arxiv"]) + " " + text
        for key, url in find_links(text).items():
            pub.setdefault(key, url)
            print(f"    {key}: {url}")
    except Exception as exc:
        print(f"    links: {exc}", file=sys.stderr)
    pdf_url = f"https://arxiv.org/pdf/{pub['arxiv']}" if pub.get("arxiv") else pub.get("pdf")
    if not pdf_url:
        return
    try:
        out = PUBLIC / "projects" / slug / "thumbnail.jpg"
        if extract_figure(download(pdf_url), out):
            pub["thumbnail"] = "/" + out.relative_to(PUBLIC).as_posix()
            print(f"    thumbnail: {pub['thumbnail']}")
    except Exception as exc:
        print(f"    thumbnail: {exc}", file=sys.stderr)


# ---------------------------------------------------------------- pages for first-authored papers
def is_me(name: str, variants: list[str]) -> bool:
    n = re.sub(r"[^a-z]", "", name.lower())
    return any(re.sub(r"[^a-z]", "", v.lower()) == n for v in variants)


def slug_of(pub: dict, overrides: dict) -> str:
    return (overrides.get(pub["id"]) or {}).get("slug", pub["id"])


def wants_page(pub: dict, overrides: dict, variants: list[str]) -> bool:
    ov = overrides.get(pub["id"]) or {}
    first = bool(pub["authors"]) and is_me(pub["authors"][0], variants)
    return not ov.get("hidden") and ov.get("page", first)


def create_page(pub: dict, slug: str) -> None:
    path = PROJECTS / f"{slug}.md"
    if path.exists():
        return
    teaser = f"teaser:\n  src: {pub['thumbnail']}\n" if pub.get("thumbnail") else ""
    path.write_text(
        "---\n"
        f"pub: {pub['id']}\n"
        "auto: true   # created by the sync script; edit freely (it will not be overwritten)\n"
        f"{teaser}"
        "---\n\n"
        "<!-- Optional content (Markdown) shown below the abstract: method, results, figures... -->\n"
    )
    print(f"    page: {path.relative_to(ROOT)}")


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", type=Path, help="write the list of added papers to this JSON file")
    ap.add_argument("--test-paper", action="store_true",
                    help="add a fake first-author paper, to test the email review (reply 'non' to remove it)")
    args = ap.parse_args()

    cfg = load_yaml(DATA / "sync.yaml") or {}
    overrides = (load_yaml(DATA / "publications.overrides.yaml") or {}).get("publications") or {}
    variants = (load_yaml(DATA / "profile.yaml") or {}).get("name_variants") or []
    current = json.loads(PUBS_JSON.read_text()) if PUBS_JSON.exists() else {"publications": []}
    existing = current["publications"]
    known = {norm_title(p["title"]) for p in existing}

    batches, sources = [], []
    # OpenAlex first: its titles and venues are cleaner; Scholar then adds missing papers and citation counts.
    for name, fetch in [("openalex", lambda: fetch_openalex(cfg)), ("scholar", lambda: fetch_scholar(cfg, known))]:
        try:
            got = fetch()
        except Exception as exc:
            print(f"! {name} failed: {exc}", file=sys.stderr)
            continue
        if got:
            print(f"{name}: {len(got)} records")
            batches.append(got)
            sources.append(name)
        else:
            print(f"{name}: skipped (not configured or empty)")

    if args.test_paper:
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H%M")
        batches.append([{
            "title": f"Test Paper {stamp}: Checking the Email Review of New Publications",
            "authors": ["Emilien Seiler", "Test Coauthor"],
            "year": dt.date.today().year,
            "date": dt.date.today().isoformat(),
            "venue": "Test venue (fake paper)",
            "type": "paper",
            "abstract": "This is a fake paper added to test the email review workflow. "
                        "Reply 'non' to the notification email and it should disappear from the site.",
        }])
        sources.append("test")

    if not batches:
        print("No source succeeded: publications.json left unchanged.")
        return 0

    pubs, new_ids = merge_all(json.loads(json.dumps(existing)), batches, cfg)
    report = []
    for pub in pubs:
        if pub["id"] not in new_ids:
            continue
        slug = slug_of(pub, overrides)
        page = wants_page(pub, overrides, variants)
        print(f"  enriching {pub['id']}")
        if not args.dry_run:
            enrich(pub, slug)
            if page:
                create_page(pub, slug)
        site = cfg.get("site_url", "").rstrip("/")
        report.append({
            "id": pub["id"],
            "title": pub["title"],
            "authors": pub["authors"],
            "venue": pub.get("venue", ""),
            "year": pub.get("year"),
            "page": f"{site}/projects/{slug}" if page else "",
            "link": pub.get("project_url") or (f"https://arxiv.org/abs/{pub['arxiv']}" if pub.get("arxiv") else "")
            or (f"https://doi.org/{pub['doi']}" if pub.get("doi") else pub.get("url", "")),
        })

    if pubs == existing:
        print("No changes.")
    else:
        out = {
            "_comment": "Generated by scripts/sync_scholar.py. Edit publications.overrides.yaml instead.",
            "updated": dt.date.today().isoformat(),
            "sources": sources,
            "publications": pubs,
        }
        if args.dry_run:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            PUBS_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
            print(f"Wrote {PUBS_JSON.relative_to(ROOT)} ({len(pubs)} publications).")
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
