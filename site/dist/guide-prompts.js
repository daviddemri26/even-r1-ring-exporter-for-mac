function copyWithSelection(text) {
  const previous = document.activeElement;
  const field = document.createElement("textarea");
  field.value = text;
  field.readOnly = true;
  field.style.cssText = "position:fixed;top:0;left:-9999px";
  document.body.append(field);
  try {
    field.focus({ preventScroll: true });
    field.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    field.remove();
    previous?.focus({ preventScroll: true });
  }
}

async function copyText(text) {
  if (navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Some embedded browsers only permit copying a visible selection.
    }
  }
  return copyWithSelection(text);
}

for (const box of document.querySelectorAll("[data-prompt]")) {
  const button = box.querySelector("button");
  const details = box.querySelector("details");
  const prompt = box.querySelector("pre");
  const status = box.querySelector('[role="status"]');
  button.hidden = false;
  button.addEventListener("click", async () => {
    if (await copyText(prompt.textContent)) {
      status.textContent = "Copied. Paste into Codex on your Mac.";
      return;
    }
    details.open = true;
    prompt.focus();
    const range = document.createRange();
    range.selectNodeContents(prompt);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = "Press ⌘C or choose Copy to copy the selected prompt.";
  });
}

const contents = document.querySelector(".docs-toc details");
if (contents && window.matchMedia("(min-width: 781px)").matches) contents.open = true;
