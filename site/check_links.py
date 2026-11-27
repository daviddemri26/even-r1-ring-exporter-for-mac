"""Check the generated Pages site's internal links and HTML fragments offline."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import quote, unquote, urljoin, urlsplit


SITE = Path(__file__).resolve().parent
TECHNICAL_NOTES = {
    "docs/alpha-testing.md", "docs/build-from-source.md", "docs/privacy.md",
    "docs/troubleshooting.md", "evenhub/README.md",
}


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.duplicates = set()
        self.links = []
        self.feed(path.read_text(encoding="utf-8"))
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        anchor = attrs.get("id") or (attrs.get("name") if tag == "a" else None)
        if anchor:
            if anchor in self.ids:
                self.duplicates.add(anchor)
            self.ids.add(anchor)
        for attr in ("href", "src"):
            if attr in attrs and attrs[attr] is not None:
                self.links.append((tag, attrs[attr]))


def check_links(root):
    repository = json.loads((SITE / "release-assets.json").read_text())["repository"]
    owner, slug = repository.split("/")
    host = owner.lower() + ".github.io"
    prefix = "/" + slug + "/"
    root = root.resolve()
    pages = {path: Page(path) for path in root.rglob("*.html")}
    errors = []
    install = root / "guides/install/index.html"
    for entry in ("index.html", "guides/index.html", "guides/install/index.html",
                  "guides/chatgpt/index.html", "guides/ask/index.html"):
        if root / entry not in pages:
            errors.append(f"Missing site entry point: {entry}")
    if install in pages:
        for anchor in {"install", "connect", "ask"} - pages[install].ids:
            errors.append(f"Missing setup section: #{anchor}")
    homepage = pages.get(root / "index.html")
    site_url = f"https://{host}{prefix}"
    if homepage and not any(tag == "a" and urljoin(site_url, href) == site_url + "guides/install/"
                            for tag, href in homepage.links):
        errors.append("The homepage needs a direct link to the setup guide.")
    repository_docs = f"https://github.com/{repository}/blob/main/"
    allowed_docs = {repository_docs + name for name in TECHNICAL_NOTES}
    documentation_index = repository_docs + "README.md#technical-documentation"
    for file, page in sorted(pages.items()):
        local = file.relative_to(root)
        errors.extend(f"{local}: duplicate anchor #{anchor}" for anchor in sorted(page.duplicates))
        base = f"https://{host}{prefix}{quote(local.as_posix())}"
        for tag, value in page.links:
            url = urlsplit(urljoin(base, value))
            if local.parts[0] == "guides" and url.hostname in {
                "github.com", "www.github.com", "raw.githubusercontent.com",
            }:
                allowed = url._replace(fragment="").geturl() in allowed_docs or url.geturl() == documentation_index
                if not allowed or tag not in {"a", "link"}:
                    errors.append(f"{local}: GitHub links are limited to the project's technical notes: {value}")
                continue
            if url.hostname != host:
                continue
            path = unquote(url.path)
            if not path.startswith(prefix):
                errors.append(f"{local}: link leaves the GitHub Pages project prefix: {value}")
                continue
            target = (root / path[len(prefix):]).resolve()
            if not target.is_relative_to(root):
                errors.append(f"{local}: link escapes the staged site: {value}")
                continue
            if target.is_dir():
                target /= "index.html"
            if not target.is_file():
                errors.append(f"{local}: missing target: {value}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f"{local}: missing HTML fragment: {value}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    count = sum(len(page.links) for page in pages.values())
    print(f"Checked {len(pages)} HTML pages and {count} link references.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SITE / "dist", help="Staged site directory.")
    sys.exit(check_links(parser.parse_args().root))
