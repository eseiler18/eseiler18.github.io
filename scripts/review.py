#!/usr/bin/env python3
"""Email review of newly added papers, through GitHub issues.

GitHub emails the notified user for every issue that mentions them, and replying to that
email posts a comment on the issue. So:

    python3 scripts/review.py notify new.json   # one issue per new paper (called by the sync workflow)
    python3 scripts/review.py decide <issue-number> "<comment text>"
                                                 # "non" -> hide the paper, "oui" -> keep it

`decide` prints `changed` when files were modified (the workflow then commits and redeploys).
Requires the GitHub CLI (`gh`), available on GitHub runners.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "src" / "data"
OVERRIDES = DATA / "publications.overrides.yaml"
PROJECTS = ROOT / "src" / "content" / "projects"
LABEL = "new-publication"
MARKER = re.compile(r"<!--\s*pub-id:\s*([\w-]+)\s*-->")

REJECT = re.compile(r"^\s*(non|no|nope|refus[ée]?e?|reject(ed)?|remove|supprimer?|retire[rz]?)\b", re.I)
ACCEPT = re.compile(r"^\s*(oui|yes|ok|okay|valid[ée]?e?|accept(ed)?|garder?|keep)\b", re.I)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def notify(report_path: str) -> None:
    cfg = yaml.safe_load((DATA / "sync.yaml").read_text()) or {}
    user = cfg.get("notify_github_user", "")
    new = json.loads(Path(report_path).read_text())
    if not new:
        print("Nothing to notify.")
        return
    subprocess.run(["gh", "label", "create", LABEL, "--color", "a3192e", "--force",
                    "--description", "Paper added automatically, awaiting review"], check=False)
    for pub in new:
        authors = ", ".join(pub["authors"][:8]) + (", et al." if len(pub["authors"]) > 8 else "")
        where = pub["page"] or pub["link"]
        body = f"""@{user} un nouveau papier a été ajouté au site :

**{pub['title']}**
{authors}
*{pub['venue']}{f", {pub['year']}" if pub.get('year') else ''}*

{"Sa page sur le site : " + pub['page'] if pub['page'] else "Sur le site, il pointe vers : " + (pub['link'] or '(aucun lien trouvé)')}

---
**Réponds à ce mail :**
- **non** : retirer ce papier du site
- **oui** : le garder (ferme cette issue)

Sans réponse, le papier reste en ligne.
Pour corriger la venue, les liens ou l'image : `src/data/publications.overrides.yaml`.

<!-- pub-id: {pub['id']} -->"""
        args = ["issue", "create", "--title", f"Nouveau papier : {pub['title'][:90]}", "--body", body, "--label", LABEL]
        if user:
            args += ["--assignee", user]
        print(gh(*args).strip())


def hide(pub_id: str) -> None:
    """Set `hidden: true` for this id in the overrides (keeping the file's comments) and
    delete the page / images the sync created for it."""
    text = OVERRIDES.read_text()
    data = yaml.safe_load(text) or {}
    entry = (data.get("publications") or {}).get(pub_id)
    if entry is None:
        text = text.rstrip("\n") + f"\n\n  {pub_id}:\n    hidden: true   # rejected by email\n"
    elif not entry.get("hidden"):
        text = re.sub(rf"^(  {re.escape(pub_id)}:[^\n]*\n)", r"\1    hidden: true   # rejected by email\n", text, count=1, flags=re.M)
    OVERRIDES.write_text(text)

    slug = (entry or {}).get("slug", pub_id)
    (ROOT / "public" / "projects" / slug / "thumbnail.jpg").unlink(missing_ok=True)  # auto-extracted image
    page = PROJECTS / f"{slug}.md"
    if page.exists() and re.search(r"^auto:\s*true", page.read_text(), re.M):
        page.unlink()
        shutil.rmtree(ROOT / "public" / "projects" / slug, ignore_errors=True)


def decide(issue: str, comment: str) -> None:
    body = json.loads(gh("issue", "view", issue, "--json", "body"))["body"]
    m = MARKER.search(body)
    if not m:
        print("not a publication issue")
        return
    # Email replies quote the original message below: only the first line matters.
    first = next((l for l in comment.splitlines() if l.strip()), "")
    if REJECT.match(first):
        hide(m.group(1))
        gh("issue", "close", issue, "--comment", "Papier retiré du site, redéploiement en cours.")
        print("changed")
    elif ACCEPT.match(first):
        gh("issue", "close", issue, "--comment", "OK, le papier reste sur le site.")
        print("kept")
    else:
        print("no decision")


if __name__ == "__main__":
    cmd, *rest = sys.argv[1:]
    {"notify": notify, "decide": decide}[cmd](*rest)
