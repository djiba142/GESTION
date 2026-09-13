"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.expenses = function () {
  var table = document.querySelector("[data-expenses-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "expenses/");
};
