(() => {
  const choices = document.querySelector(".choices");
  const questions = [...document.querySelectorAll("[data-question]")];
  const copyLine = document.querySelector(".copy-line");
  const copyStatus = document.querySelector(".copy-status");
  const copyButton = document.querySelector(".copy");

  function selectQuestion() {
    const selected = choices.querySelector("input:checked").value;
    questions.forEach((item) => {
      item.hidden = item.dataset.question !== selected;
    });
    copyStatus.textContent = "";
  }

  choices.addEventListener("change", selectQuestion);
  choices.hidden = false;
  selectQuestion();

  if (!navigator.clipboard?.writeText) return;
  copyLine.hidden = false;
  copyButton.addEventListener("click", async () => {
    const item = questions.find((question) => !question.hidden);
    const prompt = item
      .querySelector(".example-prompt")
      .textContent.trim()
      .replace(/^«\s*|\s*»$/g, "");
    try {
      await navigator.clipboard.writeText(prompt);
      copyStatus.textContent = "Question copiée.";
    } catch {
      copyStatus.textContent =
        "Sélectionnez le texte de la question pour le copier.";
    }
  });
})();
