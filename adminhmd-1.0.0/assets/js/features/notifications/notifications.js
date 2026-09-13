"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.notifications = function () {
  var list = document.querySelector("[data-notifications-list]");
  if (!list || !window.NexoraAPI) return;
  list.setAttribute("data-api-resource", "notifications/");
};
