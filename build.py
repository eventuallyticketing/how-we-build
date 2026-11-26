#!/usr/bin/env python3
"""Build the site from post.md and its git history.

Each day post.md changed becomes a version: the last commit of that day
(Chicago time), labelled with that commit's first line. The page lays the
versions on a calendar from the first day to today, so days with no change
show as empty days. The newest
version is also written out as plain HTML, so search engines and readers
without JavaScript get the whole post.

Usage: python3 build.py   (writes _site/)
"""
import datetime, html, json, pathlib, re, shutil, subprocess
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "_site"
TZ = ZoneInfo("America/Chicago")
POST = "post.md"
# Set this to the blog post's address once it is live, so search engines treat
# the blog post as the original and this page as its history.
CANONICAL_URL = "https://www.eventuallyticketing.com/how-eventually-gets-built-our-two-person-software-factory"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def history():
    log = git("log", "--format=%H%x1f%cI%x1f%s%x1f%b%x1e", "--", POST)
    commits = []
    for rec in log.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, when, subject, body = (rec.split("\x1f") + [""])[:4]
        day = datetime.datetime.fromisoformat(when).astimezone(TZ).date()
        # Trailers such as Co-Authored-By are credits, not part of the day's summary.
        body = "\n".join(l for l in body.split("\n") if not re.match(r"^(Co-Authored-By|Signed-off-by):", l, re.I))
        commits.append({"sha": sha, "day": day, "subject": subject.strip(), "body": " ".join(body.split())})
    commits.reverse()  # oldest first
    days = {}
    for c in commits:
        days.setdefault(c["day"], []).append(c)
    versions = []
    for i, (day, cs) in enumerate(sorted(days.items()), start=1):
        last = cs[-1]
        # One clean line per day: the last commit's subject and body. A day with
        # several commits and no body on the last one lists the earlier subjects.
        summary = last["body"] or ("Also: " + "; ".join(c["subject"] for c in cs[:-1]) + "." if len(cs) > 1 else "")
        versions.append({
            "rev": i,
            "iso": day.isoformat(),
            "date": f"{day:%b} {day.day}, {day.year}",
            "label": last["subject"],
            "summary": summary,
            "markdown": to_slider_md(git("show", f"{last['sha']}:{POST}")),
        })
    return versions


def to_slider_md(md):
    # The slider's parser knows one picture, written as an @embed line with its caption.
    return re.sub(r"^!\[([^\]]*)\]\([^)]*\)\s*$", lambda m: "@embed " + m.group(1), md, flags=re.M)


def inline(text):
    out, last = [], 0
    for m in re.finditer(r"\*\*(.+?)\*\*", text):
        out.append(html.escape(text[last:m.start()]))
        out.append("<strong>" + html.escape(m.group(1)) + "</strong>")
        last = m.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


def static_html(md):
    """Plain HTML of one version, using the same small Markdown subset as the slider."""
    lines, out, i = md.split("\n"), [], 0
    alt = "Flow chart of an idea's path from a customer ask to shipped, with one loop back for fixes and two human gates: Zack merges, then Zack ships."
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("@embed "):
            out.append(f'<figure class="embed-fig"><img src="life-of-an-idea.png" alt="{html.escape(alt)}"><figcaption>{inline(line[7:])}</figcaption></figure>')
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("- ") or re.match(r"^\d+\.\s", line):
            ordered = not line.startswith("- ")
            items = []
            while i < len(lines) and (lines[i].startswith("- ") if not ordered else re.match(r"^\d+\.\s", lines[i])):
                items.append("<li>" + inline(re.sub(r"^(- |\d+\.\s)", "", lines[i])) + "</li>")
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head, body = cells(rows[0]), [cells(r) for r in rows[2:]]
            t = "<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</table>")
            continue
        else:
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    return "\n".join(out)


def main():
    versions = history()
    if not versions:
        raise SystemExit("post.md has no commits yet")
    page = (ROOT / "src" / "page.html").read_text()
    canonical = f'<link rel="canonical" href="{html.escape(CANONICAL_URL)}">' if CANONICAL_URL else ""
    page = page.replace("__CANONICAL__", canonical)
    page = page.replace("__STATIC_POST__", static_html(versions[-1]["markdown"]))
    page = page.replace("__UPDATED__", versions[-1]["date"])
    page = page.replace("__VERSIONS__", json.dumps(versions, ensure_ascii=False).replace("</", "<\\/"))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(page)
    shutil.copy(ROOT / "life-of-an-idea.png", OUT / "life-of-an-idea.png")
    shutil.copy(ROOT / "og-image.png", OUT / "og-image.png")
    print(f"built {len(versions)} days into {OUT.name}/")


if __name__ == "__main__":
    main()
