"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.locations = function () {
  var table = document.querySelector("[data-locations-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "inventory/locations/");
};
