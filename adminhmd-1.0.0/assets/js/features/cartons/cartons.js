"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.cartons = function () {
  var table = document.querySelector("[data-cartons-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "inventory/cartons/");
};
