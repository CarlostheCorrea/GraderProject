const state = {
  sessionId: null,
  rubricsById: {},
};
const DEFAULT_ORCHESTRATOR = "pydanticai";

const els = {
  createForm: document.getElementById("create-form"),
  gradeForm: document.getElementById("grade-form"),
  editForm: document.getElementById("edit-form"),
  askForm: document.getElementById("ask-form"),
  rubricSelect: document.getElementById("rubric-select"),
  rubricSummary: document.getElementById("rubric-summary"),
  docText: document.getElementById("document-text"),
  documentFile: document.getElementById("document-file"),
  uploadDocumentBtn: document.getElementById("upload-document-btn"),
  sessionId: document.getElementById("session-id"),
  gradeInstruction: document.getElementById("grade-instruction"),
  grammarOnly: document.getElementById("grammar-only"),
  editInstruction: document.getElementById("edit-instruction"),
  askQuestion: document.getElementById("ask-question"),
  gradeResult: document.getElementById("grade-result"),
  editResult: document.getElementById("edit-result"),
  askResult: document.getElementById("ask-result"),
  toast: document.getElementById("toast"),
};

function notify(message, error = false) {
  els.toast.textContent = message;
  els.toast.style.background = error ? "#991b1b" : "#111827";
  els.toast.classList.add("show");
  setTimeout(() => els.toast.classList.remove("show"), 2000);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : "Request failed";
    throw new Error(String(detail));
  }

  return payload;
}

async function extractDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/documents/extract", {
    method: "POST",
    body: formData,
  });

  let payload;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : "Failed to extract file text";
    throw new Error(String(detail));
  }

  return payload;
}

function toBullet(items) {
  if (!Array.isArray(items) || items.length === 0) return "- None";
  return items.map((item) => `- ${item}`).join("\n");
}

function formatGradeResult(data) {
  const criteria = Array.isArray(data.criteria) ? data.criteria : [];
  const criteriaText = criteria.length
    ? criteria
        .map((criterion) => {
          const quotes = toBullet(criterion.evidence_quotes);
          return [
            `${criterion.criterion_id} (${criterion.label})`,
            `Score: ${criterion.score}/4`,
            `Justification: ${criterion.justification}`,
            `Evidence:`,
            quotes,
          ].join("\n");
        })
        .join("\n\n")
    : "No criteria returned.";

  return [
    `Overall Score: ${data.overall_score_1_to_4 ?? "N/A"}/4`,
    `Letter Grade: ${data.letter_grade ?? "N/A"}`,
    `Confidence: ${data.confidence ?? "N/A"}%`,
    "",
    "Summary Strengths:",
    toBullet(data.summary_strengths),
    "",
    "Priority Revisions:",
    toBullet(data.priority_revisions),
    "",
    "Criteria:",
    criteriaText,
  ].join("\n");
}

function formatEditResult(data) {
  const edits = Array.isArray(data.edits) ? data.edits : [];
  const editText = edits.length
    ? edits
        .map((edit, index) =>
          [
            `${index + 1}.`,
            `Original: ${edit.original}`,
            `Suggested: ${edit.suggested}`,
            `Reason: ${edit.reason}`,
          ].join("\n")
        )
        .join("\n\n")
    : "No edits returned.";

  return [
    "Top 5 Writing Fixes:",
    toBullet(data.top_5_writing_fixes),
    "",
    "Edits:",
    editText,
  ].join("\n");
}

function formatAskResult(data) {
  return [
    "Answer:",
    data.answer ?? "No answer returned.",
    "",
    "Citations:",
    toBullet(data.citations),
  ].join("\n");
}

function renderResult(node, data, type) {
  if (type === "grade") {
    node.textContent = formatGradeResult(data);
    return;
  }
  if (type === "edit") {
    node.textContent = formatEditResult(data);
    return;
  }
  if (type === "ask") {
    node.textContent = formatAskResult(data);
    return;
  }
  node.textContent = String(data);
}

function requireSession() {
  if (!state.sessionId) {
    throw new Error("Create a session first.");
  }
}

function setLoading(form, loading) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = loading;
}

function selectedOrchestrator() {
  const maybeSelect = document.getElementById("orchestrator-select");
  if (maybeSelect && typeof maybeSelect.value === "string" && maybeSelect.value.trim()) {
    return maybeSelect.value;
  }
  return DEFAULT_ORCHESTRATOR;
}

async function loadRubrics() {
  const rubrics = await api("/rubrics");
  state.rubricsById = {};
  els.rubricSelect.innerHTML = "";
  for (const rubric of rubrics) {
    state.rubricsById[rubric.rubric_id] = rubric;
    const option = document.createElement("option");
    option.value = rubric.rubric_id;
    const shortTitle = rubric.short_title || rubric.name || rubric.rubric_id;
    option.textContent = shortTitle;
    option.title = option.textContent;
    els.rubricSelect.append(option);
  }
  updateRubricSummary();
}

function updateRubricSummary() {
  const selected = state.rubricsById[els.rubricSelect.value];
  if (!selected) {
    els.rubricSummary.textContent = "";
    return;
  }
  const shortTitle = selected.short_title || selected.name || selected.rubric_id;
  const summary = selected.summary || "Evaluates writing quality using structured criteria.";
  els.rubricSummary.textContent = `${shortTitle}: ${summary}`;
}

els.createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(els.createForm, true);
  try {
    const payload = {
      document_text: els.docText.value.trim(),
      rubric_id: els.rubricSelect.value,
      orchestrator: selectedOrchestrator(),
    };
    const result = await api("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.sessionId = result.session_id;
    els.sessionId.textContent = state.sessionId;
    notify("Session created.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    setLoading(els.createForm, false);
  }
});

els.gradeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(els.gradeForm, true);
  try {
    requireSession();
    const payload = {
      orchestrator: selectedOrchestrator(),
      user_instruction: els.gradeInstruction.value.trim() || null,
      grammar_only: els.grammarOnly.checked,
      reasoning_mode: "on",
    };
    const result = await api(`/sessions/${state.sessionId}/grade`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderResult(els.gradeResult, result, "grade");
    notify("Grading complete.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    setLoading(els.gradeForm, false);
  }
});

els.editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(els.editForm, true);
  try {
    requireSession();
    const payload = {
      orchestrator: selectedOrchestrator(),
      instruction: els.editInstruction.value.trim() || null,
    };
    const result = await api(`/sessions/${state.sessionId}/edit`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderResult(els.editResult, result, "edit");
    notify("Edits generated.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    setLoading(els.editForm, false);
  }
});

els.askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(els.askForm, true);
  try {
    requireSession();
    const payload = {
      orchestrator: selectedOrchestrator(),
      question: els.askQuestion.value.trim(),
      reasoning_mode: "off",
    };
    const result = await api(`/sessions/${state.sessionId}/ask`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderResult(els.askResult, result, "ask");
    notify("Follow-up answered.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    setLoading(els.askForm, false);
  }
});

loadRubrics().catch((error) => {
  notify(`Failed to load rubrics: ${error.message}`, true);
});

els.rubricSelect.addEventListener("change", updateRubricSummary);

els.uploadDocumentBtn.addEventListener("click", async () => {
  const file = els.documentFile.files && els.documentFile.files[0];
  if (!file) {
    notify("Choose a file first (.pdf, .txt, .docx).", true);
    return;
  }

  els.uploadDocumentBtn.disabled = true;
  try {
    const result = await extractDocument(file);
    els.docText.value = result.document_text;
    notify(`Loaded ${result.filename} (${result.chars} chars).`);
  } catch (error) {
    notify(error.message, true);
  } finally {
    els.uploadDocumentBtn.disabled = false;
  }
});
