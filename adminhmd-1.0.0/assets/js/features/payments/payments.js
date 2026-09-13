"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.payments = function () {
  var table = document.querySelector("[data-payments-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "payments/");
};
