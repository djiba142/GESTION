"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.products = function () {
  var table = document.querySelector("[data-products-table] tbody");
  if (!table || !window.NexoraAPI) return;
  window.NexoraAPI.getProducts().then(function (products) {
    table.dataset.loaded = String(products.length);
  });
};
