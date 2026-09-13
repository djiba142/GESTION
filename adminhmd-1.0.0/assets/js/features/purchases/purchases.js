"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.purchases = function () {
  var table = document.querySelector("[data-purchases-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "purchases/orders/");
};
