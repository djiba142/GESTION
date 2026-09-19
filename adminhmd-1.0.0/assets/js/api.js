"use strict";

(function (window) {
  var configuredBaseUrl = window.NEXORA_API_URL || "http://127.0.0.1:8000/api";

  function apiUrl(path) {
    return configuredBaseUrl.replace(/\/$/, "") + "/" + path.replace(/^\//, "");
  }

  async function request(path, options) {
    var response;
    try {
      response = await fetch(apiUrl(path), Object.assign({
        credentials: "include",
        headers: { "Content-Type": "application/json" }
      }, options || {}));
    } catch (error) {
      throw new Error("Impossible de joindre le serveur. Vérifiez que le backend NEXORA est démarré, puis réessayez.");
    }
    var payload = await response.json().catch(function () { return {}; });

    if (!response.ok) {
      var message = payload.message || payload.detail || "Une erreur est survenue.";
      throw new Error(message);
    }

    return payload;
  }

  async function requestBlob(path) {
    var response;
    try {
      response = await fetch(apiUrl(path), { credentials: "include" });
    } catch (error) {
      throw new Error("Impossible de joindre le serveur pour télécharger le PDF.");
    }

    if (!response.ok) {
      throw new Error("Le PDF de la facture n’est pas disponible.");
    }

    return response.blob();
  }

  window.NexoraAPI = {
    baseUrl: configuredBaseUrl,
    get: function (path) { return request(path); },
    list: function (resource, search) {
      var query = search ? "?search=" + encodeURIComponent(search) : "";
      return request(resource + query).then(function (payload) {
        return Array.isArray(payload) ? payload : (payload.results || []);
      });
    },
    post: function (path, body) {
      return request(path, { method: "POST", body: JSON.stringify(body) });
    },
    remove: function (path) {
      return request(path, { method: "DELETE", body: JSON.stringify({}) });
    },
    upload: function (path, formData) {
      return request(path, { method: "POST", headers: {}, body: formData });
    },
    getCurrentUser: function () { return request("users/me/"); },
    getDashboard: function () { return request("core/dashboard/"); },
    getProducts: function (search) { return this.list("products/", search); },
    getCategories: function () { return this.list("products/categories/"); },
    scanProduct: function (code) { return request("products/scan/?code=" + encodeURIComponent(code)); },
    getCustomers: function (search) { return this.list("customers/", search); },
    getSuppliers: function (search) { return this.list("suppliers/", search); },
    getExchangeRates: function () { return this.list("suppliers/exchange-rates/"); },
    getUsers: function (search) { return this.list("users/", search); },
    getUtilisateurs: function (search) { return this.getUsers(search); },
    getSales: function () { return this.list("sales/"); },
    getPayments: function () { return this.list("payments/"); },
    getCredits: function () { return this.list("payments/credits/"); },
    getCustomerPaymentSummary: function (customerId) { return request("payments/customer/" + customerId + "/"); },
    getCustomerCreditDetail: function (customerId) { return request("payments/customer/" + customerId + "/credits/"); },
    getStock: function () { return this.list("inventory/stock/"); },
    getLocations: function () { return this.list("inventory/locations/"); },
    getCartons: function () { return this.list("inventory/cartons/"); },
    getTransfers: function () { return this.list("inventory/transfers/"); },
    getMovements: function () { return this.list("inventory/movements/"); },
    getNotifications: function () { return this.list("notifications/"); },
    getNotificationHistory: function () { return request("notifications/history/"); },
    exportNotificationsCsv: function () { return fetch(apiUrl("notifications/export/?format=csv"), { credentials: "include" }); },
    markNotificationRead: function (id) { return request("notifications/" + id + "/read/", { method: "POST", body: JSON.stringify({}) }); },
    dispatchNotification: function (id) { return request("notifications/" + id + "/dispatch/", { method: "POST", body: JSON.stringify({}) }); },
    getExpenses: function () { return this.list("expenses/"); },
    getExpenseCategories: function () { return this.list("expenses/categories/"); },
    getPurchaseOrders: function () { return this.list("purchases/orders/"); },
    getReceipts: function () { return this.list("purchases/receipts/"); },
    getInvoices: function () { return this.list("invoices/"); },
    getInvoice: function (id) { return request("invoices/" + id + "/"); },
    getInvoicePdf: function (id) { return requestBlob("invoices/" + id + "/pdf/"); },
    getDocuments: function () { return this.list("documents/"); },
    updateCurrentUser: function (body) { return request("users/me/", { method: "PATCH", body: JSON.stringify(body) }); },
    getReports: function (filters) {
      var query = new URLSearchParams(filters || {}).toString();
      return request("core/reports/" + (query ? "?" + query : ""));
    },
    getCashflow: function () { return request("core/cashflow/"); },
    getAudit: function () { return this.list("core/audit/"); },
    getSettings: function () { return this.list("core/settings/"); },
    getParamètres: function () { return this.getSettings(); },
    saveSetting: function (body) { return request("core/settings/", { method: "POST", body: JSON.stringify(body) }); },
    login: function (identifier, pin) { return request("users/login/", { method: "POST", body: JSON.stringify({ identifier: identifier, pin: pin }) }); },
    requestPinReset: function (email) { return request("users/pin-reset/request/", { method: "POST", body: JSON.stringify({ email: email }) }); },
    confirmPinReset: function (uid, token, pin) { return request("users/pin-reset/confirm/", { method: "POST", body: JSON.stringify({ uid: Number(uid), token: token, pin: pin }) }); },
    logout: function () { return request("users/logout/", { method: "POST", body: JSON.stringify({}) }); }
  };
})(window);
