"""Small helpers shared by the pipeline scripts. Standard library only."""
import pathlib
import urllib.parse

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
# The repo root holds .env and data/. The skill folder holds code and policy.
ROOT = SKILL_DIR.parent
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


def load_env(name):
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""
