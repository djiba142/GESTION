"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.transfers = function () {
  var table = document.querySelector("[data-transfers-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "inventory/transfers/");
};
