"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.documents = function () {
  var table = document.querySelector("[data-documents-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "documents/");
};
