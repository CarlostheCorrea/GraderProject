const state = {
  sessionId: null,
  rubricsById: {},
};
const DEFAULT_ORCHESTRATOR = "pydanticai";

const els = {
  createForm: document.getElementById("create-form"),
  factcheckForm: document.getElementById("factcheck-form"),
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
  factcheckResult: document.getElementById("factcheck-result"),
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

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function scoreBarClass(score) {
  if (score >= 4) return "bar-great";
  if (score >= 3) return "bar-good";
  if (score >= 2) return "bar-fair";
  return "bar-poor";
}

function bulletListHtml(items, cls) {
  if (!Array.isArray(items) || items.length === 0) return `<li class="result-li ${cls}">None</li>`;
  return items.map((item) => `<li class="result-li ${cls}">${esc(item)}</li>`).join("");
}

function pillsHtml(items, pillClass) {
  if (!Array.isArray(items) || items.length === 0) {
    return `<span class="pill ${pillClass}">None</span>`;
  }
  return items.map((item) => `<span class="pill ${pillClass}">${esc(item)}</span>`).join(" ");
}

function formatGradeResult(data) {
  const score = data.overall_score_1_to_4 ?? "—";
  const grade = data.letter_grade ?? "—";
  const confidence = data.confidence != null ? `${data.confidence}%` : "—";

  const strengthItems = bulletListHtml(data.summary_strengths, "li-green");
  const revisionItems = bulletListHtml(data.priority_revisions, "li-orange");

  const criteria = Array.isArray(data.criteria) ? data.criteria : [];
  const criteriaHtml = criteria
    .map((c) => {
      const name = esc(c.criterion_name || "Unnamed");
      const category = esc(c.category_name || c.category_id || "");
      const s = c.score ?? 0;
      const pct = Math.round((s / 4) * 100);
      const barClass = scoreBarClass(s);
      const label = esc(c.label || "");
      const justification = esc(c.justification || "");
      const quotes = Array.isArray(c.evidence_quotes) ? c.evidence_quotes : [];
      const quotesHtml = quotes
        .map((q) => `<div class="evidence-quote">${esc(q)}</div>`)
        .join("");

      return `
        <details class="criterion-row">
          <summary>
            <span class="criterion-name">${name}</span>
            <span class="criterion-level-badge ${barClass}-badge">${s}/4 · ${label}</span>
          </summary>
          <div class="criterion-detail">
            ${category ? `<span class="criterion-category">${category}</span>` : ""}
            <div class="score-bar-wrap full-bar">
              <div class="score-bar-fill ${barClass}" style="width:${pct}%"></div>
            </div>
            <p class="criterion-justification">${justification}</p>
            ${quotesHtml ? `<div class="evidence-list">${quotesHtml}</div>` : ""}
          </div>
        </details>`;
    })
    .join("");

  return `
    <div class="score-badge">
      <div class="score-left">
        <span class="score-num">${esc(String(score))}<span class="score-denom">/4</span></span>
        <span class="score-grade-badge">${esc(grade)}</span>
      </div>
      <div class="score-right">
        <span class="score-conf-label">Confidence</span>
        <span class="score-conf-value">${esc(confidence)}</span>
      </div>
    </div>
    <div class="result-two-col">
      <div class="result-section">
        <h4 class="section-label section-label-green">&#10003; Strengths</h4>
        <ul class="result-list">${strengthItems}</ul>
      </div>
      <div class="result-section">
        <h4 class="section-label section-label-orange">&#9650; Priority Revisions</h4>
        <ul class="result-list">${revisionItems}</ul>
      </div>
    </div>
    ${criteriaHtml ? `<h4 class="section-label section-label-muted criteria-heading">Criteria Breakdown</h4><div class="criteria-list">${criteriaHtml}</div>` : ""}`;
}

function formatEditResult(data) {
  const fixes = Array.isArray(data.top_5_writing_fixes) ? data.top_5_writing_fixes : [];
  const fixPills = pillsHtml(fixes, "pill-orange");

  const edits = Array.isArray(data.edits) ? data.edits : [];
  const editsHtml = edits
    .map(
      (edit) => `
      <div class="edit-item">
        <div class="edit-original">${esc(edit.original)}</div>
        <div class="edit-suggested">${esc(edit.suggested)}</div>
        <div class="edit-reason">${esc(edit.reason)}</div>
      </div>`
    )
    .join("");

  return `
    <div class="result-section edits-fixes">
      <h4 class="section-label section-label-orange">Top Writing Fixes</h4>
      <div class="pill-list">${fixPills}</div>
    </div>
    ${editsHtml || "<p>No edits returned.</p>"}`;
}

function formatAskResult(data) {
  const answer = esc(data.answer ?? "No answer returned.");
  const citations = Array.isArray(data.citations) ? data.citations : [];
  const citationsHtml = citations
    .map((c) => `<div class="citation-item">${esc(c)}</div>`)
    .join("");

  return `
    <div class="chat-bubble">${answer}</div>
    ${
      citationsHtml
        ? `<div class="citations-section">
            <h4>Citations</h4>
            ${citationsHtml}
           </div>`
        : ""
    }`;
}

function renderResult(node, data, type) {
  if (type === "grade") {
    node.innerHTML = formatGradeResult(data);
    return;
  }
  if (type === "edit") {
    node.innerHTML = formatEditResult(data);
    return;
  }
  if (type === "ask") {
    node.innerHTML = formatAskResult(data);
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

function formatFactCheckResult(data) {
  const claims = Array.isArray(data.claims) ? data.claims : [];
  if (claims.length === 0) return `<p style="color:var(--muted);font-size:0.88rem;">No verifiable claims found.</p>`;

  const verdictLabel = { Supported: "✓ Supported", Contradicted: "✗ Contradicted", Unverifiable: "? Unverifiable" };
  const verdictClass = { Supported: "verdict-supported", Contradicted: "verdict-contradicted", Unverifiable: "verdict-unverifiable" };

  const cardsHtml = claims.map((c) => {
    const vClass = verdictClass[c.verdict] || "verdict-unverifiable";
    const vLabel = verdictLabel[c.verdict] || c.verdict;
    const sourceHtml = c.source_url
      ? `<a class="claim-source" href="${esc(c.source_url)}" target="_blank" rel="noopener">
           <span class="claim-source-icon">↗</span>${esc(c.source_title || c.source_url)}
         </a>`
      : c.source_title
      ? `<span class="claim-source" style="cursor:default;border:none;">${esc(c.source_title)}</span>`
      : "";

    return `
      <div class="claim-card ${vClass}">
        <div class="claim-header">
          <span class="claim-verdict-badge">${vLabel}</span>
          <span class="claim-text">${esc(c.claim)}</span>
        </div>
        <div class="claim-body">
          <div class="claim-explanation">${esc(c.explanation)}</div>
          ${sourceHtml}
        </div>
      </div>`;
  }).join("");

  return `<div class="factcheck-list">${cardsHtml}</div>`;
}

els.factcheckForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(els.factcheckForm, true);
  try {
    requireSession();
    const result = await api(`/sessions/${state.sessionId}/factcheck`, { method: "POST" });
    els.factcheckResult.innerHTML = formatFactCheckResult(result);
    notify("Fact check complete.");
  } catch (error) {
    notify(error.message, true);
  } finally {
    setLoading(els.factcheckForm, false);
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
