"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.receipts = function () {
  var table = document.querySelector("[data-receipts-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "purchases/receipts/");
};
