(function () {
  "use strict";

  const artifactUrl = "/assets/data/interactive-replay-explainer.json";
  const phaseOrder = ["source", "parse", "payload", "target", "op", "replay", "timeline", "evidence"];
  const phaseLabels = {
    source: "source",
    parse: "parse",
    payload: "payload",
    target: "target",
    op: "op",
    replay: "replay",
    timeline: "timeline",
    evidence: "evidence"
  };

  const root = document.querySelector("[data-explainer-root]");
  if (!root) return;

  const state = {
    artifact: null,
    activePhase: "source",
    scrubberBound: false
  };

  const byId = (selector) => root.querySelector(selector);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  })[char]);

  function listById(items) {
    return new Map((items || []).map((item) => [item.id, item]));
  }

  function renderError(message) {
    const error = byId("[data-explainer-error]");
    const content = byId("[data-explainer-content]");
    if (content) content.hidden = true;
    if (!error) return;
    error.hidden = false;
    error.innerHTML = `
      <h2>Explainer data did not load</h2>
      <p>${escapeHtml(message)}</p>
      <p>The page is static; this usually means the JSON artifact was not copied or the browser blocked the request.</p>
    `;
  }

  function highlightSpans(source) {
    const text = source.source_text || "";
    const spans = [...(source.spans || [])].sort((a, b) => a.start - b.start);
    let cursor = 0;
    let html = "";
    for (const span of spans) {
      html += escapeHtml(text.slice(cursor, span.start));
      html += `<mark class="source-mark ${escapeHtml(span.kind)}" data-span-id="${escapeHtml(span.id)}">${escapeHtml(text.slice(span.start, span.end))}</mark>`;
      cursor = span.end;
    }
    html += escapeHtml(text.slice(cursor));
    return html;
  }

  function findSnapshot(kind) {
    return (state.artifact.document_snapshots || []).find((snapshot) => snapshot.kind === kind);
  }

  function phaseIndex(phase) {
    return phaseOrder.indexOf(phase);
  }

  function replayHasRun() {
    return phaseIndex(state.activePhase) >= phaseIndex("replay");
  }

  function operation() {
    return (state.artifact.typed_operations || [])[0];
  }

  function mutation() {
    return (state.artifact.mutation_events || [])[0];
  }

  function targetResolution() {
    return (state.artifact.target_resolution || [])[0];
  }

  function clauseSurface() {
    return (state.artifact.clause_surfaces || [])[0];
  }

  function payload() {
    return (state.artifact.payloads || [])[0];
  }

  function observationsByPhase() {
    const observations = state.artifact.evidence?.observations || [];
    if (state.activePhase === "evidence") return observations;
    return observations.filter((obs) => obs.phase === state.activePhase);
  }

  function pathClass(path, snapshotRole) {
    const op = operation();
    const event = mutation();
    const changed = new Set(event?.changed_paths || []);
    const targetResolved = phaseIndex(state.activePhase) >= phaseIndex("target");
    if (snapshotRole === "after" && replayHasRun() && changed.has(path)) return "changed";
    if (targetResolved && op?.target_path === path) return "target";
    return "stable";
  }

  function renderTreeNode(node, snapshotRole) {
    const status = pathClass(node.path, snapshotRole);
    const children = node.children || [];
    return `
      <div class="tree-node ${status}" data-path="${escapeHtml(node.path)}">
        <div class="tree-node-line">
          <span class="node-type">${escapeHtml(node.node_type)}</span>
          <span class="node-label">${escapeHtml(node.label)}</span>
          <code>${escapeHtml(node.path)}</code>
        </div>
        <p>${escapeHtml(node.text || "")}</p>
        ${children.length ? `<div class="tree-children">${children.map((child) => renderTreeNode(child, snapshotRole)).join("")}</div>` : ""}
      </div>
    `;
  }

  function renderTree() {
    const before = findSnapshot("before_replay");
    const after = findSnapshot("after_replay");
    const afterReady = replayHasRun();
    const afterPhaseCopy = {
      source: "No replay output exists yet. The compiler has only loaded witnessed amendment text.",
      parse: "No replay output exists yet. The operative clause is classified, but no tree mutation is executable.",
      payload: "No replay output exists yet. The replacement payload is known, but it has not been bound to a live target.",
      target: "No replay output exists yet. The live tree is shown with the resolved target path.",
      op: "No replay output exists yet. The canonical operation has been built, but replay has not applied it.",
      replay: "Replay has applied the replacement to the target path.",
      timeline: "The replay result is now represented as a point-in-time timeline state.",
      evidence: "The final replayed tree is shown as evidence linked back to source, operation, and mutation records."
    };
    const beforeHeading = byId("[data-tree-before-heading]");
    const afterHeading = byId("[data-tree-after-heading]");
    if (beforeHeading) beforeHeading.textContent = afterReady ? "Before replay" : "Live tree before replay";
    if (afterHeading) afterHeading.textContent = afterReady ? "After replay" : "Replay output pending";
    byId("[data-tree-before]").innerHTML = before ? renderTreeNode(before.root, "before") : "<p>No before snapshot.</p>";
    byId("[data-tree-after]").innerHTML = `
      <p class="tree-phase-note">${escapeHtml(afterPhaseCopy[state.activePhase] || "")}</p>
      ${afterReady && after ? renderTreeNode(after.root, "after") : before ? renderTreeNode(before.root, "pending") : "<p>No pending snapshot.</p>"}
    `;
  }

  function renderSourcePanel() {
    const source = (state.artifact.source_witnesses || [])[0];
    const current = (state.artifact.phase_steps || []).find((phase) => phase.phase === state.activePhase);
    const copy = state.artifact.copy?.phase_copy?.[state.activePhase] || current?.short_explanation || "";
    const index = phaseOrder.indexOf(state.activePhase);
    const headingNumber = byId(".source-panel .panel-heading span");
    const headingTitle = byId(".source-panel .panel-heading h2");
    if (headingNumber) headingNumber.textContent = String(index + 1).padStart(2, "0");
    if (headingTitle) headingTitle.textContent = current?.title || phaseLabels[state.activePhase];
    byId("[data-phase-copy]").innerHTML = `
      <h2>${escapeHtml(current?.title || phaseLabels[state.activePhase])}</h2>
      <p>${escapeHtml(current?.short_explanation || "")}</p>
      <p class="compiler-note">${escapeHtml(copy)}</p>
    `;
    byId("[data-source-meta]").innerHTML = `
      <span>${escapeHtml(source.role)}</span>
      <span>${escapeHtml(source.citation)}</span>
      <span>${escapeHtml(source.authority_note)}</span>
    `;
    byId("[data-source-witness]").innerHTML = source ? highlightSpans(source) : "No source witness.";

    const activePayload = payload();
    const unitRows = (activePayload?.units || []).map((unit) => `
      <div>
        <strong>${escapeHtml(unit.node_type)} ${escapeHtml(unit.label)}</strong>
        <p>${escapeHtml(unit.text_en)}</p>
        <code>${escapeHtml((unit.source_backing?.span_ids || []).join(", "))}</code>
      </div>
    `).join("");
    byId("[data-payload-box]").innerHTML = `
      <h3>Extracted payload</h3>
      ${unitRows || "<p>No payload units.</p>"}
    `;
  }

  function renderOperationCard() {
    const op = operation();
    const event = mutation();
    const target = targetResolution();
    const clause = clauseSurface();
    if (!op) {
      byId("[data-operation-card]").innerHTML = "<p>No operation.</p>";
      return;
    }
    const phaseLead = {
      source: "No operation exists yet at the source-witness phase. The compiler is still reading witnessed text.",
      parse: "The operation is not executable yet. The clause has only been classified as a replace instruction.",
      payload: "The operation is still waiting for extracted payload and target evidence.",
      target: "Target resolution supplies the live tree path needed before lowering.",
      op: "This is the canonical operation replay will consume.",
      replay: "Replay applies this operation to the target path.",
      timeline: "The operation becomes a timeline entry for point-in-time materialization.",
      evidence: "The operation remains linked to source, payload, target, mutation, timeline, and evidence records."
    }[state.activePhase];
    byId("[data-operation-card]").innerHTML = `
      <h3>${escapeHtml(op.canonical_action)} <span>${escapeHtml(op.id)}</span></h3>
      <p class="compiler-note">${escapeHtml(phaseLead)}</p>
      <dl>
        <dt>Action family</dt><dd>${escapeHtml(clause?.action_family || op.canonical_action)}</dd>
        <dt>Target</dt><dd><code>${escapeHtml(op.target_path)}</code></dd>
        <dt>Payload</dt><dd><code>${escapeHtml(op.payload_id)}</code></dd>
        <dt>Effective date</dt><dd>${escapeHtml(op.effective_date)}</dd>
        <dt>Target confidence</dt><dd>${escapeHtml(target?.scope_confidence || "unknown")}</dd>
        <dt>Replay outcome</dt><dd>${escapeHtml(event?.outcome || "unknown")}</dd>
      </dl>
      <p>Provenance refs: ${(op.provenance_refs || []).map((ref) => `<code>${escapeHtml(ref)}</code>`).join(" ")}</p>
    `;
  }

  function renderStrictness() {
    const strictness = operation()?.strictness;
    if (!strictness) return;
    byId("[data-strictness-card]").innerHTML = `
      <h3>Strict vs quirks</h3>
      <div class="mode-grid">
        <div><span>strict</span><strong>${escapeHtml(strictness.strict_mode)}</strong></div>
        <div><span>quirks</span><strong>${escapeHtml(strictness.quirks_mode)}</strong></div>
      </div>
      <p>${escapeHtml(strictness.reason)}</p>
    `;
  }

  function renderPhaseEvidence() {
    const event = mutation();
    const target = targetResolution();
    const timeline = state.artifact.timeline || {};
    const phaseObservations = observationsByPhase();
    const allObservations = state.artifact.evidence?.observations || [];
    const oracleComparisons = state.artifact.evidence?.oracle_comparisons || [];
    const claims = state.artifact.evidence?.outward_claims || [];
    const phaseSpecific = {
      parse: [
        ["parse status", clauseSurface()?.parse_status],
        ["target expression", clauseSurface()?.target_expression],
        ["temporal expression", clauseSurface()?.temporal_expression]
      ],
      target: [
        ["selected path", target?.selected_path],
        ["status", target?.status],
        ["candidates", (target?.candidate_paths || []).map((candidate) => `${candidate.path}: ${candidate.reason}`).join("; ")]
      ],
      op: [
        ["operation id", operation()?.id],
        ["canonical action", operation()?.canonical_action],
        ["provenance refs", (operation()?.provenance_refs || []).join(", ")]
      ],
      replay: [
        ["mutation event", event?.id],
        ["changed paths", (event?.changed_paths || []).join(", ")],
        ["boundary evidence", "changed_paths is covered by the operation target path"]
      ],
      timeline: [
        ["timeline entries", (timeline.entries || []).map((entry) => `${entry.path} active from ${entry.valid_from}`).join("; ")],
        ["PIT query", (timeline.pit_queries || []).map((query) => `${query.as_of} ${query.projection}`).join("; ")],
        ["materialized text", (timeline.pit_queries || []).map((query) => query.materialized_text).filter(Boolean).join(" ")]
      ],
      evidence: [
        ["findings", `${(state.artifact.evidence?.findings || []).length} finding(s)`],
        ["oracle comparison", oracleComparisons.map((item) => `${item.status}: ${item.detail}`).join("; ")],
        ["outward claim", claims.map((claim) => claim.text).join(" ")]
      ]
    };
    const detailRows = (phaseSpecific[state.activePhase] || []).filter((row) => row[1]).map((row) => `
      <div class="evidence-row"><span>${escapeHtml(row[0])}</span><p>${escapeHtml(row[1])}</p></div>
    `).join("");
    const observationRows = (phaseObservations.length ? phaseObservations : allObservations).map((obs) => `
      <div class="observation">
        <code>${escapeHtml(obs.id)}</code>
        <strong>${escapeHtml(obs.kind)}</strong>
        <p>${escapeHtml(obs.detail)}</p>
      </div>
    `).join("");
    byId("[data-evidence-stack]").innerHTML = `
      <h3>Phase evidence</h3>
      ${detailRows || "<p>No extra phase-local records for this step.</p>"}
      <h3>Observations</h3>
      ${observationRows || "<p>No observations recorded for this phase.</p>"}
    `;
  }

  function renderNotices() {
    const notices = state.artifact.copy?.notices || [];
    const status = state.artifact.example?.status || "unknown";
    byId("[data-notices]").innerHTML = `
      <strong>${escapeHtml(status)}</strong>
      ${notices.map((notice) => `<p>${escapeHtml(notice.text)}</p>`).join("")}
    `;
    byId("[data-example-status]").textContent = `${state.artifact.example?.id || "example"} · ${status}`;
  }

  function renderScrubber() {
    const scrubber = byId("[data-phase-scrubber]");
    if (!scrubber.children.length) {
      scrubber.innerHTML = phaseOrder.map((phase, index) => `
        <button type="button" data-phase="${escapeHtml(phase)}" aria-pressed="false">
          <span>${String(index + 1).padStart(2, "0")}</span>
          ${escapeHtml(phaseLabels[phase])}
        </button>
      `).join("");
    }
    if (!state.scrubberBound) {
      scrubber.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-phase]");
        if (!button || button.dataset.phase === state.activePhase) return;
        state.activePhase = button.dataset.phase;
        render();
      });
      state.scrubberBound = true;
    }
    scrubber.querySelectorAll("button[data-phase]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.phase === state.activePhase));
    });
  }

  function render() {
    renderScrubber();
    renderNotices();
    renderSourcePanel();
    renderTree();
    renderOperationCard();
    renderStrictness();
    renderPhaseEvidence();
    const index = phaseOrder.indexOf(state.activePhase) + 1;
    byId("[data-phase-counter]").textContent = `phase ${index} of ${phaseOrder.length}: ${phaseLabels[state.activePhase]}`;
    byId("[data-explainer-content]").hidden = false;
  }

  fetch(artifactUrl, { headers: { Accept: "application/json" } })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status} while loading ${artifactUrl}`);
      return response.json();
    })
    .then((artifact) => {
      state.artifact = artifact;
      render();
    })
    .catch((error) => {
      renderError(error.message || String(error));
    });
})();
