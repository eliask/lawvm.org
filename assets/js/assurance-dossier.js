(function () {
  'use strict';

  var tabs = document.getElementById('scenario-tabs');
  var panel = document.getElementById('dossier-panel');
  var error = document.getElementById('dossier-error');
  if (!tabs || !panel || !error) return;

  function text(value) {
    if (value === null || value === undefined || value === '') return 'not available';
    if (Array.isArray(value)) return value.length ? value.join(', ') : 'none';
    return String(value);
  }

  function detailRow(term, value) {
    var row = document.createElement('div');
    row.className = 'status-row';
    var dt = document.createElement('dt');
    var dd = document.createElement('dd');
    dt.textContent = term;
    dd.textContent = text(value);
    row.append(dt, dd);
    return row;
  }

  function putDetails(id, values) {
    var list = document.getElementById(id);
    list.replaceChildren();
    Object.keys(values).forEach(function (key) {
      list.appendChild(detailRow(key.replaceAll('_', ' '), values[key]));
    });
  }

  function renderAccount(account) {
    var meter = document.getElementById('account-meter');
    meter.replaceChildren();
    ['emitted', 'rejected', 'typed_observation', 'unaccounted'].forEach(function (key) {
      var value = account[key];
      var segment = document.createElement('span');
      segment.className = 'account-segment account-' + key;
      segment.style.setProperty('--account-share', String(Math.max(value, 0)));
      segment.textContent = key + ' ' + value;
      segment.hidden = value === 0;
      meter.appendChild(segment);
    });
    var accounted = account.emitted + account.rejected + account.typed_observation;
    var equation = document.getElementById('account-equation');
    equation.textContent = accounted + ' accounted + ' + account.unaccounted + ' unaccounted = ' + account.declared + ' declared';
    equation.className = 'account-equation ' + (accounted + account.unaccounted === account.declared && account.unaccounted === 0 ? 'account-clean' : 'account-gap');
  }

  function render(scenario, selectedButton) {
    tabs.querySelectorAll('button').forEach(function (button) {
      button.setAttribute('aria-pressed', button === selectedButton ? 'true' : 'false');
    });
    document.getElementById('dossier-fixture-label').textContent = 'Synthetic fixture · ' + scenario.id;
    document.getElementById('dossier-title').textContent = scenario.label;
    document.getElementById('dossier-summary').textContent = scenario.summary;
    var outcome = document.getElementById('dossier-outcome');
    outcome.textContent = scenario.outcome.replaceAll('_', ' ');
    outcome.className = 'outcome-chip outcome-' + scenario.outcome;
    putDetails('source-details', scenario.source);
    putDetails('operation-details', scenario.operation);
    putDetails('mutation-details', scenario.mutation);
    putDetails('resolution-details', scenario.resolution);
    putDetails('temporal-details', scenario.temporal);
    putDetails('checker-details', scenario.checker);
    putDetails('receipt-details', scenario.receipt);
    putDetails('observation-details', scenario.observation);
    putDetails('root-details', scenario.roots);
    document.getElementById('dossier-wording').textContent = scenario.permitted_wording;
    renderAccount(scenario.account);
    panel.hidden = false;
  }

  fetch('/assets/data/assurance-demo.json')
    .then(function (response) {
      if (!response.ok) throw new Error('HTTP ' + response.status);
      return response.json();
    })
    .then(function (data) {
      if (data.status !== 'synthetic_teaching_fixture_not_certificate' || !Array.isArray(data.scenarios)) {
        throw new Error('unexpected fixture schema');
      }
      data.scenarios.forEach(function (scenario, index) {
        var button = document.createElement('button');
        button.className = 'scenario-tab';
        button.type = 'button';
        button.textContent = scenario.label;
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', function () { render(scenario, button); });
        tabs.appendChild(button);
        if (index === 0) render(scenario, button);
      });
    })
    .catch(function (reason) {
      error.textContent = 'The synthetic assurance fixture could not be loaded: ' + reason.message;
    });
}());
