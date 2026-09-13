"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.invoices = function () {
  var table = document.querySelector("[data-invoices-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "invoices/");
};
