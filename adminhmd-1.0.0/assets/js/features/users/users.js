"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.users = function () {
  var table = document.querySelector("[data-users-table]");
  if (!table || !window.NexoraAPI) return;
  table.setAttribute("data-api-resource", "users/");
};
