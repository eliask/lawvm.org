(function () {
  'use strict';
  var names = {
    fi: 'Finland', ee: 'Estonia', uk: 'United Kingdom', nz: 'New Zealand',
    no: 'Norway', se: 'Sweden', eu: 'European Union', us: 'United States federal',
    jp: 'Japan', kr: 'South Korea', pl: 'Poland', ch: 'Switzerland',
    'open-law': 'Open Law Library'
  };
  var code = new URLSearchParams(window.location.search).get('frontend');
  var name = names[code];
  if (!name) return;
  var context = document.getElementById('frontend-context');
  if (context) {
    context.textContent = 'Selected frontend context: ' + name + '. The pilot scope still depends on the declared sources, objective, and local reviewer.';
    context.hidden = false;
  }
  var email = document.getElementById('pilot-email');
  if (email) {
    email.href = 'mailto:hello@lawvm.org?subject=' + encodeURIComponent('LawVM ' + name + ' pilot') +
      '&body=' + encodeURIComponent('Frontend / source regime: ' + name + '\nInstitution and requesting role:\nSource or IT contact role:\nDecision owner role:\nObjective:\nSource links:\nBounded corpus:\nData boundary:\nLocal reviewer:\n');
  }
}());
