"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.inventory = function () {
  var table = document.querySelector("[data-stock-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "inventory/stock/");
};
