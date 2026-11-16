#!/usr/bin/env python3
"""Step 2: gather website evidence for every account.

For each account: fetch the homepage, then up to MAX_SUBPAGES same-site pages
whose links look useful (about, membership, amenities...). Strip scripts and
styles, keep visible text. The record sent to the grader has four parts:

  1. the opening text of each page (cookie banners and menu text repeated
     across pages removed),
  2. [META] the meta description,
  3. [ALT] image alt text,
  4. [SNIPPETS] about 150 characters each side of every equipment or facility
     word (config.json evidence_words) found anywhere on any fetched page.

Part 4 exists because a plain character cap cut real evidence deep in long
pages. The total is still capped so one account costs a bounded amount to
grade. Every failure gets a named status. Results are cached per normalized
URL in data/cache/web/, so re-runs are free.

Writes data/evidence.jsonl: one record per account (CRM fields, Apollo tag
for cross-checking, scrape status, text).

Fetches through curl: macOS's built-in Python has an old TLS library that
some servers refuse.

Run from the project folder:  python3 <skill>/scripts/fetch_evidence.py
"""
import csv
import hashlib
import html.parser
import json
import re
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import DATA, load_config, normalize_url, need

CACHE = DATA / "cache" / "web"
WORKERS = 8            # one site per worker, so each domain is hit serially
MAX_SUBPAGES = 3
HOME_CHARS = 1500      # opening text kept from the homepage
SUBPAGE_CHARS = 500    # opening text kept from each subpage
META_CHARS = 300
ALT_CHARS = 600
SNIPPET_SIDE = 150     # characters kept each side of an evidence word
MAX_SNIPPETS = 12
TOTAL_CHARS = 7000     # hard cap on text sent to the grader per account
EVIDENCE_WORDS = load_config()["evidence_words"]["words"]
WORD_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(
    re.escape(w) for w in sorted(EVIDENCE_WORDS, key=len, reverse=True)) + r")",
    re.I)
COOKIE_RE = re.compile(r"cookie|consent preferences|privacy preference|"
                       r"accept all|reject all|we use cookies", re.I)
THIN_CHARS = 200
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")
LINK_WORDS = ["member", "join", "pricing", "rates", "amenit", "facilit",
              "equipment", "about", "gym", "class", "service", "tour"]
PARKED = ["domain is for sale", "buy this domain", "domain may be for sale",
          "this domain is parked", "hugedomains", "domain has expired",
          "website coming soon", "under construction"]


class TextAndLinks(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "template"}

    def __init__(self):
        super().__init__()
        self.depth, self.text, self.links = 0, [], []
        self.alts, self.meta = [], ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and not self.meta:
            key = (a.get("name") or a.get("property") or "").lower()
            if key in ("description", "og:description") and a.get("content"):
                self.meta = a["content"].strip()
        if tag == "img" and (a.get("alt") or "").strip():
            self.alts.append(a["alt"].strip())
        if tag in self.SKIP:
            self.depth += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth and data.strip():
            self.text.append(data.strip())


def curl(url):
    """Return (status, final_url, html). status: ok, timeout, dns_failure,
    connect_failed, http_<code>."""
    r = subprocess.run(
        ["curl", "-sL", "--compressed", "-m", "20", "--max-filesize", "3000000",
         "-A", USER_AGENT, "-w", "\n%{http_code} %{url_effective}", url],
        capture_output=True)
    out = r.stdout.decode("utf-8", "replace")
    body, _, tail = out.rpartition("\n")
    code, _, final = tail.partition(" ")
    if r.returncode == 28:
        return "timeout", url, ""
    if r.returncode == 6:
        return "dns_failure", url, ""
    if r.returncode != 0:
        return "connect_failed", url, ""
    if not code.startswith("2"):
        return f"http_{code}", final or url, ""
    return "ok", final or url, body


def parse(html):
    """Return (text, links). Plain visible text, nothing removed."""
    p = _feed(html)
    return re.sub(r"\s+", " ", " ".join(p.text)).strip(), p.links


def _feed(html):
    p = TextAndLinks()
    try:
        p.feed(html)
    except Exception:
        pass
    return p


def clean_segments(segments, seen):
    """Drop cookie-banner text and text segments already seen on an earlier
    page (menus, footers). Updates `seen`."""
    out = []
    for seg in segments:
        seg = re.sub(r"\s+", " ", seg).strip()
        key = seg.lower()
        if not seg or COOKIE_RE.search(seg) or (len(seg) > 2 and key in seen):
            continue
        seen.add(key)
        out.append(seg)
    return " ".join(out)


def snippets(pages_text):
    """Short windows around evidence words, overlapping windows merged, at
    most MAX_SNIPPETS, spread across different words first."""
    found = []   # (word, snippet)
    for text in pages_text:
        spans = []
        for m in WORD_RE.finditer(text):
            a, b = max(0, m.start() - SNIPPET_SIDE), m.end() + SNIPPET_SIDE
            if spans and a <= spans[-1][1]:
                spans[-1][1] = b
                spans[-1][2].append(m.group(1).lower())
            else:
                spans.append([a, b, [m.group(1).lower()]])
        for a, b, words in spans:
            found.append((words[0], text[a:b].strip()))
    picked, used_words, seen = [], set(), set()
    for first_pass in (True, False):   # one per word first, then the rest
        for word, snip in found:
            if len(picked) >= MAX_SNIPPETS:
                break
            if snip in seen or (first_pass and word in used_words):
                continue
            picked.append(snip)
            seen.add(snip)
            used_words.add(word)
    return picked


def pick_subpages(base, links):
    host = urllib.parse.urlsplit(base).hostname
    seen, picks = set(), []
    for href in links:
        u = urllib.parse.urljoin(base, href).split("#")[0]
        s = urllib.parse.urlsplit(u)
        if s.scheme not in ("http", "https") or s.hostname != host:
            continue
        path = s.path.lower().rstrip("/")
        if not path or path in seen or re.search(r"\.(pdf|jpg|png|zip)$", path):
            continue
        if any(w in path for w in LINK_WORDS):
            seen.add(path)
            picks.append(u)
        if len(picks) >= MAX_SUBPAGES:
            break
    return picks


def gather(url):
    """Fetch one site. Cached by normalized URL."""
    key = normalize_url(url)
    if not key:
        return {"scrape_status": "no_website", "pages": [], "text": ""}
    path = CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    if path.exists():
        return json.loads(path.read_text())

    status, final, html = curl(key)
    if status != "ok":
        result = {"scrape_status": status, "pages": [key], "text": ""}
    else:
        home = _feed(html)
        home_text = re.sub(r"\s+", " ", " ".join(home.text)).strip()
        seen = set()
        parts = [f"[HOME] {clean_segments(home.text, seen)[:HOME_CHARS]}"]
        pages, full_texts = [final], [home_text]
        metas, alts = [home.meta] if home.meta else [], list(home.alts)
        for sub in pick_subpages(final, home.links):
            s, f, h = curl(sub)
            if s != "ok":
                continue
            p = _feed(h)
            full = re.sub(r"\s+", " ", " ".join(p.text)).strip()
            if not full:
                continue
            opening = clean_segments(p.text, seen)[:SUBPAGE_CHARS]
            if opening:
                parts.append(f"[{urllib.parse.urlsplit(f).path}] {opening}")
            pages.append(f)
            full_texts.append(full)
            if p.meta and p.meta not in metas:
                metas.append(p.meta)
            alts += p.alts
        if metas:
            parts.append("[META] " + " | ".join(metas)[:META_CHARS])
        alts = list(dict.fromkeys(a for a in alts if len(a) > 3))
        if alts:
            parts.append("[ALT] " + " | ".join(alts)[:ALT_CHARS])
        snips = snippets(full_texts)
        if snips:
            parts.append("[SNIPPETS] " + " ... ".join(snips))
        text = " ".join(parts)[:TOTAL_CHARS]
        low = home_text.lower()
        if any(p in low for p in PARKED) and len(home_text) < 1500:
            st = "parked"
        elif len(home_text) < THIN_CHARS:
            st = "thin_content"
        else:
            st = "ok"
        result = {"scrape_status": st, "pages": pages, "text": text}
    path.write_text(json.dumps(result))
    return result


def main():
    need('accounts.csv')
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(DATA / "accounts.csv", newline="") as f:
        accounts = list(csv.DictReader(f))
    only = set(sys.argv[1:])   # optional: limit to given account IDs
    if only:
        accounts = [a for a in accounts if a["account_id"] in only]

    results = {}
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(gather, a["website"]): a for a in accounts}
        for i, fut in enumerate(as_completed(futures), 1):
            a = futures[fut]
            results[a["account_id"]] = fut.result()
            print(f"{i:>3}/{len(accounts)} {a['domain']:<38} "
                  f"{results[a['account_id']]['scrape_status']}", flush=True)

    out_path = DATA / ("evidence_subset.jsonl" if only else "evidence.jsonl")
    counts = {}
    with open(out_path, "w") as out:
        for a in accounts:
            ev = results[a["account_id"]]
            counts[ev["scrape_status"]] = counts.get(ev["scrape_status"], 0) + 1
            out.write(json.dumps({
                "account_id": a["account_id"],
                "name": a["name"],
                "website": a["website"],
                "crm_city": a["city"], "crm_state": a["state"],
                "apollo_industry_tag": a["apollo_industry"],
                "apollo_keywords": a["apollo_keywords"],
                "scrape_status": ev["scrape_status"],
                "pages": ev["pages"],
                "text": ev["text"],
            }) + "\n")
    print("\nScrape status counts:", counts)
    print(f"Wrote {out_path.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
