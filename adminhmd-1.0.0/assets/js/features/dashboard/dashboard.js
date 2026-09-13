"use strict";

window.NexoraFeatures = window.NexoraFeatures || {};
window.NexoraFeatures.dashboard = function () {
  var values = document.querySelectorAll("[data-dashboard-value]");
  if (!values.length || !window.NexoraAPI) return;
  window.NexoraAPI.getDashboard().then(function (data) {
    var map = { sales: data.total_sales, products: data.total_products, customers: data.total_customers, stock: data.total_stock_items, lowStock: data.low_stock_products, received: data.total_received };
    values.forEach(function (element) {
      var value = map[element.getAttribute("data-dashboard-value")];
      if (value !== undefined) element.textContent = value;
    });
  });
};
