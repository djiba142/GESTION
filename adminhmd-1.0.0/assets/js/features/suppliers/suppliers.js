"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.suppliers = function () {
  var table = document.querySelector("[data-suppliers-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "suppliers/");
};
