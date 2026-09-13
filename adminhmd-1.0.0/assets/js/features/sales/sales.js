"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.sales = function () {
  var form = document.querySelector("[data-sale-form]");
  if (!form || !window.NexoraAPI) return;
  form.setAttribute("data-api-resource", "sales/");
};
