"""Small helpers shared by the pipeline scripts. Standard library only."""
import pathlib
import re
import urllib.parse

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
# The project folder you run from holds .env and data/. The skill folder
# holds code and policy, so it works in this repo or copied into
# .claude/skills/.
ROOT = pathlib.Path.cwd()
DATA = ROOT / "data"

# Two-part public suffixes we are likely to meet. Not a full list; good
# enough for US small-business sites. Production would use the public
# suffix list.
_TWO_PART = {"co.uk", "com.au", "co.nz", "org.uk"}

# Website builders that host many businesses under one domain. For these the
# business is the full host (studio.square.site), not the platform.
_SHARED_HOSTS = {"square.site", "wixsite.com", "squarespace.com", "weebly.com",
                 "godaddysites.com", "business.site", "wordpress.com",
                 "blogspot.com", "myshopify.com", "mindbodyonline.com"}


def normalize_url(url):
    """Add a scheme, lowercase the host, drop 'www.', the path's trailing
    slash, query and fragment. Used as the cache key, so the same site
    written two ways is fetched once."""
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/")
    return urllib.parse.urlunsplit(("https", host, path, "", ""))


def registered_domain(url):
    """'https://www.foo.example.com/x' -> 'example.com'."""
    host = urllib.parse.urlsplit(normalize_url(url)).hostname or ""
    parts = host.split(".")
    if ".".join(parts[-2:]) in _SHARED_HOSTS:
        return host
    if len(parts) >= 3 and ".".join(parts[-2:]) in _TWO_PART:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def load_config():
    import json
    return json.loads((SKILL_DIR / "config.json").read_text())


# Words too generic to show two names are the same company.
_GENERIC = {"the", "and", "of", "at", "a", "an", "inc", "llc", "co", "corp",
            "company", "group", "fitness", "gym", "club", "center", "centre",
            "health", "wellness", "studio", "athletic", "training", "sport",
            "sports", "llp", "ltd"}


def name_words(name):
    out = set()
    for w in re.findall(r"[a-z0-9]+", (name or "").lower()):
        if len(w) < 2 or w in _GENERIC:
            continue
        stem = w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 3 else w
        if stem not in _GENERIC:
            out.add(stem)
    return out


def names_agree(crm_name, apollo_name):
    """True when the names share a meaningful word, or when one name with
    spaces and punctuation removed contains the other (FitClub, OrthoIllinois)."""
    if name_words(crm_name) & name_words(apollo_name):
        return True
    a, b = (re.sub(r"[^a-z0-9]", "", (n or "").lower()) for n in (crm_name, apollo_name))
    return bool(a and b) and (a in b or b in a)


def load_env(name):
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
