"use strict";

(function (window, document) {
  var featureNames = ["dashboard", "products", "customers", "suppliers", "inventory", "locations", "transfers", "cartons", "sales", "payments", "notifications", "reports", "users", "expenses", "purchases", "invoices", "receipts", "documents"];
  var loader = document.currentScript;
  var basePath = loader ? loader.src.substring(0, loader.src.lastIndexOf("/")) : "../assets/js/features";

  function loadFeature(name) {
    var script = document.createElement("script");
    script.src = basePath + "/" + name + "/" + name + ".js";
    script.onload = function () {
      if (window.NexoraFeatures && typeof window.NexoraFeatures[name] === "function") {
        window.NexoraFeatures[name]();
      }
    };
    document.head.appendChild(script);
  }

  featureNames.forEach(loadFeature);
})(window, document);
