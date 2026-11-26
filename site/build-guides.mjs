import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import MarkdownIt from "markdown-it";

const site = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(site);
const output = path.join(site, "dist", "guides");
const release = JSON.parse(await readFile(path.join(site, "release-assets.json"), "utf8"));
const brand = "Even R1 Ring Exporter for Mac";

const guides = [
  {
    slug: "install", source: "docs/installation.md", title: "Install the Mac app",
    summary: "Check your equipment, allow the collector and run your first export.",
    related: ["chatgpt", "troubleshooting"],
  },
  {
    slug: "chatgpt", source: "docs/chatgpt.md", title: "Connect ChatGPT",
    summary: "Create a private tunnel and connect your own ChatGPT workspace to the Mac.",
    related: ["ask", "privacy"],
  },
  {
    slug: "ask", source: "docs/ask-about-readings.md", title: "Ask about your readings",
    summary: "Ask about seven nights of sleep or the six health cards, without attaching a file.",
    related: ["troubleshooting", "chatgpt"],
  },
  {
    slug: "troubleshooting", source: "docs/troubleshooting.md", title: "Troubleshoot missing readings",
    summary: "Follow a missing night from the iPhone to the Mac and ChatGPT.",
    related: ["install", "ask"],
  },
  {
    slug: "privacy", source: "docs/privacy.md", title: "Understand your privacy",
    summary: "See what stays on your Mac, what ChatGPT receives and how to stop collection.",
    related: ["chatgpt", "install"],
  },
  {
    slug: "glasses", source: "evenhub/README.md", title: "Use the G2 glasses guide",
    summary: "Download the optional offline guide and move through its five cards.",
    related: ["install", "build"],
  },
  {
    slug: "test", source: "docs/alpha-testing.md", title: "Test the public alpha",
    summary: "Check an export on a second Mac and compare it with Even on your phone.",
    related: ["install", "troubleshooting"],
  },
  {
    slug: "build", source: "docs/build-from-source.md", title: "Build from source",
    summary: "Download the release source, build the Mac app or G2 guide and preview the website.",
    related: ["test", "glasses"],
  },
];

const markdown = new MarkdownIt({ html: false });
const escape = markdown.utils.escapeHtml;
const guideBySource = new Map(guides.map(guide => [guide.source, guide]));
const guideBySlug = new Map(guides.map(guide => [guide.slug, guide]));
const releaseFiles = new Set([...release.assets.map(asset => asset.file), "SHA256SUMS", "source.zip"]);
const projectUrl = "https://github.com/" + release.repository;
const providerHosts = new Set([
  "apps.apple.com", "support.apple.com", "chatgpt.com", "developers.openai.com",
  "platform.openai.com", "hub.evenrealities.com", "support.evenrealities.com",
]);

function sourceLink(source, hash, base) {
  const guide = guideBySource.get(source);
  if (guide) return base + "guides/" + guide.slug + "/" + hash;
  if (source === "README.md" || source === "") return base + hash;
  throw new Error("No website route for repository path " + source);
}

function releaseLink(name, base) {
  if (!releaseFiles.has(name)) throw new Error("Unknown release file " + name);
  return base + "downloads/" + encodeURIComponent(name);
}

function websiteLink(href, guide, base) {
  if (href.startsWith("#")) return href;
  const url = new URL(href, "https://source.invalid/" + guide.source);
  if (url.origin === "https://source.invalid") {
    return sourceLink(decodeURIComponent(url.pathname.slice(1)), url.hash, base);
  }

  if (url.origin + url.pathname === projectUrl) return base + url.hash;
  if ((url.origin + url.pathname).startsWith(projectUrl + "/")) {
    const target = decodeURIComponent((url.origin + url.pathname).slice(projectUrl.length + 1));
    const binaryPrefix = "releases/download/" + release.tag + "/";
    if (target.startsWith(binaryPrefix)) return releaseLink(target.slice(binaryPrefix.length), base);
    if (target === "archive/refs/tags/" + release.tag + ".zip") return releaseLink("source.zip", base);
    if (target === "releases/tag/" + release.tag || target === "releases") return base + "guides/install/#install-the-mac-app";
    for (const ref of ["main", release.tag]) {
      const blob = "blob/" + ref + "/";
      if (target.startsWith(blob)) return sourceLink(target.slice(blob.length), url.hash, base);
    }
    if (target === "") return base + url.hash;
  }
  if (url.protocol === "https:" && providerHosts.has(url.hostname)) return url.href;
  throw new Error(guide.source + " has an unmapped link: " + href);
}

function inlineText(token) {
  return token.children.filter(child => ["text", "code_inline"].includes(child.type))
    .map(child => child.content).join("");
}

function headingId(label) {
  return label.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase()
    .replace(/[’']/g, "").replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
}

function readGuide(guide, source, base) {
  const env = {};
  const tokens = markdown.parse(source, env);
  if (tokens[0]?.type !== "heading_open" || tokens[0].tag !== "h1") {
    throw new Error(guide.source + " must start with a top-level title.");
  }
  const title = inlineText(tokens[1]);
  const content = tokens.slice(3);
  const sections = [];
  const ids = new Set(["content", "page-title", "toc-title", "related-title"]);
  for (const [index, token] of content.entries()) {
    for (const child of token.children ?? []) {
      if (child.type === "link_open") child.attrSet("href", websiteLink(child.attrGet("href"), guide, base));
    }
    if (token.type !== "heading_open") continue;
    if (token.tag === "h1") throw new Error(guide.source + " contains a second top-level title.");
    const label = inlineText(content[index + 1]);
    const prefix = headingId(label);
    let id = prefix;
    for (let n = 2; ids.has(id); n++) id = prefix + "-" + n;
    ids.add(id);
    token.attrSet("id", id);
    sections.push({ label, id, level: Number(token.tag.slice(1)) });
  }
  return { title, sections, html: markdown.renderer.render(content, markdown.options, env) };
}

function brandLink(base) {
  return '<a class="brand" href="' + base + '" aria-label="' + brand + ' home"><span class="mark" aria-hidden="true"></span><span>' + brand + '</span></a>';
}

function card(guide, base) {
  return '<a class="docs-card" href="' + base + "guides/" + guide.slug + '/"><h3>' + escape(guide.title) +
    '</h3><p>' + escape(guide.summary) + '</p><span aria-hidden="true">→</span></a>';
}

function breadcrumb(base, title) {
  const guidesCrumb = title ? '<li><a href="' + base + 'guides/">Guides</a></li><li aria-current="page">' + escape(title) + '</li>' : '<li aria-current="page">Guides</li>';
  return '<nav class="docs-breadcrumb" aria-label="Breadcrumb"><ol><li><a href="' + base + '">Home</a></li>' + guidesCrumb + '</ol></nav>';
}

function tableOfContents(sections) {
  let items = "";
  for (const { label, id, level } of sections) {
    items += '<li class="docs-toc-level-' + level + '"><a href="#' + id + '">' + escape(label) + '</a></li>';
  }
  return '<nav class="docs-toc" aria-labelledby="toc-title"><h2 id="toc-title">On this page</h2><ol>' + items + '</ol></nav>';
}

function template(base, title, description, main) {
  return '<!doctype html>\n<html lang="en">\n<head>\n' +
    '  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1">\n' +
    '  <meta name="theme-color" content="#f9faf6">\n  <meta name="description" content="' + escape(description) + '">\n' +
    '  <title>' + escape(title) + ' · ' + brand + '</title>\n' +
    '  <link rel="stylesheet" href="' + base + 'style.css">\n  <link rel="stylesheet" href="' + base + 'guides.css">\n' +
    '</head>\n<body class="docs-page">\n  <a class="skip" href="#content">Skip to content</a>\n' +
    '  <header class="site-header"><div class="wrap nav">' + brandLink(base) +
    '<nav aria-label="Main navigation"><a href="' + base + '#how-it-works">How it works</a><a href="' + base +
    '#requirements">Requirements</a><a href="' + base + 'guides/" aria-current="' +
    (base === "../" ? "page" : "location") + '">Guides</a></nav></div></header>\n' +
    '  <main id="content" class="wrap docs-shell">\n' + main + '\n  </main>\n' +
    '  <footer class="wrap footer">' + brandLink(base) +
    '<p>An independent project. Even Realities, Apple and OpenAI are unaffiliated.</p>' +
    '<a class="repo" href="' + base + 'guides/">All guides <span aria-hidden="true">→</span></a></footer>\n</body>\n</html>\n';
}

function indexPage() {
  const base = "../";
  const summary = "Set up your Mac, connect ChatGPT and read the dates and units that Even reports.";
  const main = breadcrumb(base) + '\n<header class="docs-hero"><h1 id="page-title">Guides</h1><p>' + summary + '</p></header>\n' +
    '<section class="docs-index" aria-labelledby="browse-title"><h2 id="browse-title">Browse the guides</h2><div class="docs-grid">' +
    guides.map(guide => card(guide, base)).join("\n") + '</div></section>';
  return template(base, "Guides", summary, main);
}

function guidePage(guide, source) {
  const base = "../../";
  const { title, sections, html } = readGuide(guide, source, base);
  const main = breadcrumb(base, guide.title) + '\n<header class="docs-hero"><h1 id="page-title">' + escape(title) + '</h1></header>\n' +
    '<div class="docs-layout">\n' + tableOfContents(sections) + '\n<article class="docs-article" aria-labelledby="page-title">\n' + html +
    '</article>\n</div>\n<section class="docs-related" aria-labelledby="related-title"><h2 id="related-title">Related guides</h2><div class="docs-grid">' +
    guide.related.map(slug => card(guideBySlug.get(slug), base)).join("\n") + '</div></section>';
  return template(base, title, guide.summary, main);
}

const pages = new Map([["index.html", indexPage()]]);
for (const guide of guides) {
  const source = await readFile(path.join(root, guide.source), "utf8");
  pages.set(guide.slug + "/index.html", guidePage(guide, source));
}

const check = process.argv.includes("--check");
for (const [file, page] of pages) {
  const destination = path.join(output, file);
  if (check) {
    if (await readFile(destination, "utf8") !== page) throw new Error("Rebuild stale page: guides/" + file);
  } else {
    await mkdir(path.dirname(destination), { recursive: true });
    await writeFile(destination, page);
  }
}
console.log((check ? "Verified " : "Built ") + pages.size + " guide pages.");
