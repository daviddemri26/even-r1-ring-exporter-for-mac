import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import MarkdownIt from "markdown-it";

const site = path.dirname(fileURLToPath(import.meta.url));
const output = path.join(site, "dist", "guides");
const release = JSON.parse(await readFile(path.join(site, "release-assets.json"), "utf8"));
const [owner, repository] = release.repository.split("/");
const siteUrl = `https://${owner.toLowerCase()}.github.io/${repository}/`;
const repoDocs = `https://github.com/${release.repository}/blob/main/`;
const diskImages = release.assets.filter(asset => asset.file.endsWith(".dmg"));
if (diskImages.length !== 1) throw new Error("Expected one Mac disk image in release-assets.json.");
const urls = {
  SITE_URL: siteUrl,
  DMG_URL: siteUrl + "downloads/" + encodeURIComponent(diskImages[0].file),
  CHECKSUMS_URL: siteUrl + "downloads/SHA256SUMS",
};
const brand = "Even R1 Ring Exporter for Mac";
const markdown = new MarkdownIt({ html: false });
const escape = markdown.utils.escapeHtml;
const renderFence = markdown.renderer.rules.fence;
const previousAnchors = {
  "page-title": ["set-up-automatic-collection-with-codex", "set-up-everything-with-codex"],
  install: ["check-the-mac-and-sync-the-ring", "install-the-mac-app", "verify-your-first-export", "turn-on-automatic-collection", "schedule-future-exports-optional"],
};
markdown.renderer.rules.heading_open = (tokens, index, options, env, renderer) => {
  const anchors = previousAnchors[tokens[index].attrGet("id")] ?? [];
  return renderer.renderToken(tokens, index, options) +
    anchors.map(id => `<span id="${id}" aria-hidden="true"></span>`).join("");
};

markdown.renderer.rules.fence = (tokens, index, options, env, renderer) => {
  const token = tokens[index];
  if (token.info.trim() !== "codex-prompt") return renderFence(tokens, index, options, env, renderer);
  const prompt = token.content.trim();
  if (!prompt) throw new Error("The setup prompt is empty.");
  return `<div class="setup-prompt" data-prompt>
  <button type="button" class="primary copy-prompt" hidden aria-controls="setup-prompt"><span class="copy-mark" aria-hidden="true"></span>Copy setup prompt</button>
  <span class="copy-status" role="status"></span>
  <noscript>Open the prompt below and copy its text into Codex.</noscript>
  <details><summary>Read or select the prompt</summary><pre tabindex="0" id="setup-prompt">${escape(prompt)}</pre></details>
</div>\n`;
};

function setupPage(source) {
  const base = "../../";
  const resolved = source.replace(/\{\{(\w+)\}\}/g, (_, name) => {
    if (!Object.hasOwn(urls, name)) throw new Error("Unknown setup placeholder " + name);
    return urls[name];
  });
  const tokens = markdown.parse(resolved, {});
  if (tokens[0]?.tag !== "h1" || tokens.filter(t => t.type === "heading_open" && t.tag === "h1").length !== 1) {
    throw new Error("Start setup.md with its single page title.");
  }
  if (tokens.filter(t => t.type === "fence" && t.info.trim() === "codex-prompt").length !== 1) {
    throw new Error("Include one complete Codex setup prompt.");
  }
  for (const [index, token] of tokens.entries()) {
    if (token.type === "heading_open") {
      const heading = tokens[index + 1];
      const last = heading.children.at(-1);
      const anchor = last?.type === "text" && last.content.match(/\s+\{#([a-z][a-z0-9-]*)\}$/);
      if (anchor) {
        token.attrSet("id", anchor[1]);
        last.content = last.content.slice(0, -anchor[0].length);
      } else if (token.tag === "h1") {
        token.attrSet("id", "page-title");
      } else {
        token.attrSet("id", heading.content.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
      }
    }
    for (const child of token.children ?? []) {
      if (child.type !== "link_open") continue;
      const href = child.attrGet("href");
      if (href.startsWith(siteUrl)) child.attrSet("href", base + href.slice(siteUrl.length));
    }
  }
  const title = escape(tokens[1].content);
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#fafbf7">
  <meta name="description" content="Set up the Even R1 ring exporter on your Mac and ask ChatGPT about your readings.">
  <title>${title} · ${brand}</title>
  <link rel="stylesheet" href="${base}style.css?v=4">
  <link rel="stylesheet" href="${base}guides.css?v=4">
  <script defer src="${base}guide-prompts.js?v=4"></script>
</head>
<body class="setup-page">
  <a class="skip" href="#content">Skip to content</a>
  <header class="site-header"><div class="wrap nav"><a class="brand" href="${base}" aria-label="${brand} home"><span class="mark" aria-hidden="true"></span><span>${brand}</span></a><nav aria-label="Main navigation"><a href="./" aria-current="page">Setup guide</a></nav></div></header>
  <main id="content" class="setup-content">
${markdown.renderer.render(tokens, markdown.options, {})}  </main>
</body>
</html>
`;
}

function redirectPage(target, label, base) {
  const link = escape(target);
  return `<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=${link}">
  <link rel="canonical" href="${link}">
  <link rel="stylesheet" href="${base}style.css?v=4">
  <link rel="stylesheet" href="${base}guides.css?v=4">
  <title>${escape(label)} · ${brand}</title>
</head><body><main class="setup-content"><p><a href="${link}">${escape(label)}</a></p></main></body></html>
`;
}

const source = await readFile(path.join(site, "setup.md"), "utf8");
const pages = new Map([
  ["install/index.html", setupPage(source)],
  ["index.html", redirectPage("install/", "Open the setup guide", "../")],
  ["chatgpt/index.html", redirectPage("../install/#connect", "Connect your Mac to ChatGPT", "../../")],
  ["ask/index.html", redirectPage("../install/#ask", "Ask about your readings", "../../")],
]);
const technicalNotes = [
  ["build", "docs/build-from-source.md", "Build from source"],
  ["test", "docs/alpha-testing.md", "Test the alpha"],
  ["privacy", "docs/privacy.md", "Data and privacy"],
  ["troubleshooting", "docs/troubleshooting.md", "Troubleshoot an export"],
  ["glasses", "evenhub/README.md", "Read the G2 companion notes"],
];
for (const [slug, file, title] of technicalNotes) {
  pages.set(slug + "/index.html", redirectPage(repoDocs + file, title, "../../"));
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
console.log((check ? "Verified" : "Built") + " the setup page and " + (pages.size - 1) + " redirects.");
