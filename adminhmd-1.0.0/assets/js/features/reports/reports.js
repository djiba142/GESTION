"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.reports = function () {
  var summary = document.querySelector("[data-report-summary]");
  if (!summary || !window.NexoraAPI) return;
  summary.setAttribute("data-api-resource", "core/reports/");
};
