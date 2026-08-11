(function () {
  'use strict';

  var form = document.getElementById('ledger-filters');
  var records = document.getElementById('ledger-records');
  var status = document.getElementById('ledger-filter-status');
  if (!form || !records || !status) return;

  var data = [];

  function human(value) {
    return String(value || '').replaceAll('_', ' ');
  }

  function addText(parent, tag, value, className) {
    var element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value;
    parent.appendChild(element);
    return element;
  }

  function option(select, value, label) {
    var item = document.createElement('option');
    item.value = value;
    item.textContent = label;
    select.appendChild(item);
  }

  function populateSelect(id, values) {
    var select = document.getElementById(id);
    Array.from(new Set(values)).sort().forEach(function (value) {
      option(select, value, human(value));
    });
  }

  function card(item) {
    var article = document.createElement('article');
    article.className = 'content-card ledger-record';
    var tags = document.createElement('div');
    tags.className = 'tag-list';
    addText(tags, 'span', human(item.status), item.status === 'externally_confirmed_correction' ? 'tag tag-green' : 'tag tag-amber');
    addText(tags, 'span', item.jurisdiction.toUpperCase(), 'tag');
    addText(tags, 'span', human(item.record_type), 'tag');
    article.appendChild(tags);
    addText(article, 'p', item.case_id, 'as-of');
    addText(article, 'h3', item.work || (String(item.count) + ' reported candidate records'));
    addText(article, 'p', item.claim);
    var details = document.createElement('dl');
    details.className = 'status-list';
    [['Reviewability', human(item.reviewability)], ['Evidence type', human(item.evidence_type)]].forEach(function (pair) {
      var row = document.createElement('div');
      row.className = 'status-row';
      addText(row, 'dt', pair[0]);
      addText(row, 'dd', pair[1]);
      details.appendChild(row);
    });
    article.appendChild(details);
    if (item.case_url) {
      var linkLabel = item.record_type === 'individual_public_case'
        ? 'Inspect this public case →'
        : item.record_type === 'public_candidate_packet'
          ? 'Inspect the candidate packet →'
          : 'Inspect the aggregate context →';
      var link = addText(article, 'a', linkLabel);
      link.href = item.case_url;
    }
    return article;
  }

  function render() {
    var selectedStatus = document.getElementById('ledger-status').value;
    var selectedJurisdiction = document.getElementById('ledger-jurisdiction').value;
    var selectedType = document.getElementById('ledger-type').value;
    var visible = data.filter(function (item) {
      return (!selectedStatus || item.status === selectedStatus) &&
        (!selectedJurisdiction || item.jurisdiction === selectedJurisdiction) &&
        (!selectedType || item.record_type === selectedType);
    });
    records.replaceChildren();
    visible.forEach(function (item) { records.appendChild(card(item)); });
    records.setAttribute('aria-busy', 'false');
    status.textContent = visible.length + ' of ' + data.length + ' public records shown.';
  }

  fetch('/assets/data/evidence.json')
    .then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    })
    .then(function (ledger) {
      data = ledger.cases || [];
      populateSelect('ledger-status', data.map(function (item) { return item.status; }));
      populateSelect('ledger-jurisdiction', data.map(function (item) { return item.jurisdiction; }));
      populateSelect('ledger-type', data.map(function (item) { return item.record_type; }));
      form.addEventListener('change', render);
      render();
    })
    .catch(function (reason) {
      status.textContent = 'The public ledger could not be loaded: ' + reason.message;
      records.setAttribute('aria-busy', 'false');
      records.replaceChildren();
      var fallback = addText(records, 'p', 'Open the confirmed Estonia case or the reported candidate packet directly.');
      var caseLink = addText(fallback, 'a', ' Open confirmed case →');
      caseLink.href = '/cases/estonia-audiitors-95-2';
    });
}());
