"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.customers = function () {
  var table = document.querySelector("[data-customers-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "customers/");
};
