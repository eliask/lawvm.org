(function () {
  'use strict';

  var form = document.getElementById('assessment-form');
  var result = document.getElementById('assessment-result');
  if (!form || !result) return;

  var latest = null;
  var decisionChain = 'Declared sources and model → declared QA checks → strict or observe-only disposition → named human decision. LawVM never edits or publishes legal text.';
  var frontendCodes = {
    fi: 'Finland', ee: 'Estonia', uk: 'United Kingdom', nz: 'New Zealand',
    no: 'Norway', se: 'Sweden', eu: 'European Union', us: 'United States federal',
    jp: 'Japan', kr: 'South Korea', pl: 'Poland', ch: 'Switzerland'
  };
  var requestedFrontendCode = new URLSearchParams(window.location.search).get('frontend');
  var requestedFrontend = frontendCodes[requestedFrontendCode] || '';
  var context = document.getElementById('frontend-context');
  if (requestedFrontend && context) {
    context.textContent = 'Selected frontend context: ' + requestedFrontend + '. The questions below still define the actual evidence boundary.';
    context.hidden = false;
  }
  var jurisdictionInput = document.getElementById('assessment-jurisdiction');
  if (requestedFrontend && jurisdictionInput) jurisdictionInput.value = requestedFrontend;

  function selected(name) {
    var input = form.querySelector('[name="' + name + '"]:checked');
    return input ? input.value : null;
  }

  function checkedValues(name) {
    return Array.from(form.querySelectorAll('[name="' + name + '"]:checked')).map(function (item) {
      return item.value;
    });
  }

  function has(values, value) { return values.indexOf(value) !== -1; }

  function unique(values) { return Array.from(new Set(values)); }

  function putList(id, values) {
    var list = document.getElementById(id);
    list.replaceChildren();
    unique(values).forEach(function (value) {
      var item = document.createElement('li');
      item.textContent = value;
      list.appendChild(item);
    });
  }

  function objectiveLabel(value) {
    return {
      consolidation: 'consolidation assurance',
      history: 'point-in-time reconstruction',
      multilingual: 'parallel official-language review',
      publication: 'drafting/publication checks',
      recovery: 'source bootstrap and readiness',
      frontend: 'jurisdiction frontend development'
    }[value];
  }

  function assess(data) {
    var immediate = [];
    var potential = [];
    var blocked = [];
    var structured = ['api', 'xml', 'html'].indexOf(data.format) !== -1;
    var sourcePoor = ['pdf', 'scan', 'mixed'].indexOf(data.format) !== -1;

    if (data.format === 'scan') {
      immediate.push('Source bootstrap: exact-image preservation, hashes, page locators, and OCR witness measurement.');
      blocked.push('Scanned pages do not yet establish correct legal structure or amendment semantics.');
      blocked.push('A legitimate stop is recorded when extraction, structure, identity, or authority evidence cannot support the next claim.');
    } else if (data.format === 'pdf') {
      immediate.push('Manifestation preservation, layout-aware extraction, segmentation, and citation-anchor assessment.');
      blocked.push('PDF extraction alone cannot authorize amendment replay.');
    } else if (structured) {
      immediate.push('Structure, identifier, version, language-expression, and schema-drift inventory.');
    } else {
      immediate.push('Mixed-source census and a representative extraction/structure benchmark.');
    }

    if (has(data.evidence, 'identifiers')) immediate.push('Stable work/version identity and manifestation linkage checks.');
    else potential.push('Stable identifiers would make version, source, and cross-system joins durable.');

    if (has(data.evidence, 'links')) immediate.push('Amendment/effect relationship inventory and unresolved-link accounting.');
    else potential.push('Explicit amendment-to-law links would reduce dependency-discovery work.');

    if (has(data.evidence, 'originals') && has(data.evidence, 'amendments')) {
      immediate.push('Source dependency closure and typed amendment-operation candidate extraction.');
      if (has(data.evidence, 'versions')) immediate.push('Before/after transition bundles and bounded dry-run comparison.');
      else potential.push('Historical before/after versions would enable independent dry-run verification.');
    } else {
      if (!has(data.evidence, 'originals')) blocked.push('Original enactments are missing from the declared evidence set.');
      if (!has(data.evidence, 'amendments')) blocked.push('Amendment publications are missing; historical replay is not presently supportable.');
    }

    if (has(data.evidence, 'dates')) immediate.push('Explicit legal-time and version-selection diagnostics.');
    else blocked.push('Effective-date evidence is absent; point-in-time state must remain qualified or blocked.');

    if (data.languages === 'multiple') {
      immediate.push('Official-expression availability and structural correspondence inventory.');
      if (structured) immediate.push('Candidate invariant-fact review across aligned expressions.');
      else potential.push('Structured expression units would enable precise parallel review.');
      blocked.push('Semantic equivalence is outside automated assessment and requires bilingual legal review.');
    } else if (data.languages === 'translations') {
      immediate.push('Authority-aware inventory separating the authoritative expression from translations.');
    } else if (data.languages === 'unknown') {
      blocked.push('Language-expression authority must be established before a conformance claim is scoped.');
    }

    if (!data.reviewer) blocked.push('No local legal/source reviewer is identified; institutional and drafting-practice questions remain unadjudicated.');
    if (!data.institution_role) potential.push('Name the institution and requesting role before pilot scoping.');
    if (!data.source_contact) potential.push('Name a source or IT contact who can explain access, formats, versions, and custody.');
    if (!data.decision_owner) blocked.push('No decision owner is identified for scope approval and finding disposition.');
    if (!data.data_boundary) potential.push('State whether the first tranche uses public links, an isolated environment, or restricted material.');
    if (data.confidential) blocked.push('Non-public material requires an agreed processing, retention, and disclosure boundary before transfer.');
    if (data.authority === 'unknown') blocked.push('The authority role of the consolidated text is unresolved.');
    if (data.authority === 'authoritative') immediate.push('Consistency checking can be scoped without treating replay as replacement authority.');
    if (sourcePoor) potential.push('A structured source or publisher export would move work from extraction evidence toward transition assurance.');

    var pilots = {
      consolidation: ['Bounded consolidation shadow audit', 'Select a source-complete transition corpus, freeze the comparison surface, test a small set of operation families, and return a classified source-linked review queue. Differences remain candidates until a named human disposition; LawVM never writes to the official text.'],
      history: ['Point-in-time reconstruction feasibility tranche', 'Choose one amended legal work or domain and a closed time interval; inventory source closure, effective dates, before/after witnesses, and the first transition families that can support bounded checks. Scope this through the consolidation pilot route.'],
      multilingual: ['Parallel-expression review tranche', 'Choose one domain and all required official expressions; inventory manifestations, align structural units, run a narrow invariant-fact profile, and route candidates to a bilingual legal reviewer.'],
      publication: ['Read-only publication QA adapter', 'Freeze one drafting or publication export and test target validity, references, legal-time metadata, expression completeness, and mutation boundaries without writing to production. Any move from observe-only evidence to a blocking workflow gate must be declared and owned by a human reviewer.'],
      recovery: ['Source-bootstrap feasibility pilot', 'Measure a representative sample for preservation, extraction, structure, identity, amendment-chain feasibility, and blocked sources before promising replay. OCR is an extraction witness, and a legitimate stop is an acceptable result.'],
      frontend: ['Bounded frontend tranche', 'Implement one evidence-producing phase—normally acquisition/source account first—with a pinned corpus, typed residuals, claim ceiling, and an explicit next promotion gate owned by a named human reviewer.']
    };

    return {
      generated_at: new Date().toISOString(),
      inputs: data,
      objective_label: objectiveLabel(data.objective),
      immediate: unique(immediate),
      potential: unique(potential),
      blocked: unique(blocked),
      pilot: {
        title: pilots[data.objective][0],
        body: pilots[data.objective][1],
        url: {
          consolidation: '/pilots#consolidation',
          history: '/pilots#consolidation',
          multilingual: '/pilots#multilingual',
          publication: '/pilots#publication',
          recovery: '/pilots#source-readiness',
          frontend: '/pilots#frontend'
        }[data.objective]
      },
      decision_chain: decisionChain,
      disclaimer: 'Browser-generated first-pass assessment; no legal or technical feasibility guarantee.'
    };
  }

  function brief(value) {
    return [
      'LawVM jurisdiction assessment',
      '',
      'Jurisdiction/source regime: ' + value.inputs.jurisdiction,
      'Institution/requesting role: ' + (value.inputs.institution_role || 'not identified'),
      'Source or IT contact role: ' + (value.inputs.source_contact || 'not identified'),
      'Decision owner role: ' + (value.inputs.decision_owner || 'not identified'),
      'Data boundary: ' + (value.inputs.data_boundary || 'not stated'),
      'Objective: ' + value.objective_label,
      'Authority model: ' + value.inputs.authority,
      'Strongest format: ' + value.inputs.format,
      'Evidence available: ' + (value.inputs.evidence.join(', ') || 'none declared'),
      'Language context: ' + value.inputs.languages,
      'Local reviewer: ' + (value.inputs.reviewer ? 'available' : 'not identified'),
      'Non-public material: ' + (value.inputs.confidential ? 'yes — agree a processing boundary before transfer' : 'no'),
      value.inputs.confidential ? 'Do not attach confidential or restricted files to this email.' : '',
      'Decision chain: ' + value.decision_chain,
      '',
      'Immediate capability:',
      value.immediate.map(function (x) { return '- ' + x; }).join('\n'),
      '',
      'Potential with more evidence:',
      value.potential.map(function (x) { return '- ' + x; }).join('\n'),
      '',
      'Blocked or qualified:',
      value.blocked.map(function (x) { return '- ' + x; }).join('\n'),
      '',
      'Recommended pilot: ' + value.pilot.title,
      value.pilot.body,
      '',
      value.disclaimer
    ].join('\n');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var data = {
      jurisdiction: jurisdictionInput.value.trim(),
      institution_role: document.getElementById('assessment-institution-role').value.trim(),
      source_contact: document.getElementById('assessment-source-contact').value.trim(),
      decision_owner: document.getElementById('assessment-decision-owner').value.trim(),
      data_boundary: document.getElementById('assessment-data-boundary').value.trim(),
      objective: selected('objective'),
      authority: selected('authority'),
      format: selected('format'),
      evidence: checkedValues('evidence'),
      languages: selected('languages'),
      reviewer: selected('reviewer') === 'yes',
      confidential: selected('confidential') === 'yes'
    };
    data.frontend_registry_context = requestedFrontendCode || null;
    latest = assess(data);
    document.getElementById('result-title').textContent = latest.pilot.title;
    document.getElementById('result-summary').textContent = 'For ' + latest.objective_label + ', the declared sources support the following first-pass boundary.';
    document.getElementById('result-boundary').textContent = latest.decision_chain;
    putList('immediate-list', latest.immediate);
    putList('potential-list', latest.potential.length ? latest.potential : ['No additional enabling source was inferred from these answers.']);
    putList('blocked-list', latest.blocked.length ? latest.blocked : ['No first-pass blocker was inferred; corpus inspection is still required.']);
    document.getElementById('pilot-title').textContent = latest.pilot.title;
    document.getElementById('pilot-body').textContent = latest.pilot.body;
    document.getElementById('result-next-action').href = latest.pilot.url;
    document.getElementById('email-assessment').href = 'mailto:hello@lawvm.org?subject=' + encodeURIComponent('LawVM assessment: ' + latest.pilot.title) + '&body=' + encodeURIComponent(brief(latest));
    document.getElementById('result-status').textContent = 'Assessment ready: ' + latest.pilot.title + '.';
    result.hidden = false;
    result.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    document.getElementById('result-title').focus({ preventScroll: true });
  });

  form.addEventListener('reset', function () {
    latest = null;
    result.hidden = true;
    document.getElementById('result-status').textContent = '';
    document.getElementById('copy-status').textContent = '';
  });

  document.getElementById('copy-assessment').addEventListener('click', function () {
    if (!latest) return;
    var text = brief(latest);
    var status = document.getElementById('copy-status');
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { status.textContent = 'Pilot brief copied.'; }, function () { status.textContent = 'Copy was blocked by the browser; use Download JSON instead.'; });
    } else {
      status.textContent = 'Clipboard access is unavailable; use Download JSON instead.';
    }
  });

  document.getElementById('download-assessment').addEventListener('click', function () {
    if (!latest) return;
    var blob = new Blob([JSON.stringify(latest, null, 2) + '\n'], { type: 'application/json' });
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'lawvm-jurisdiction-assessment.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
  });
}());
