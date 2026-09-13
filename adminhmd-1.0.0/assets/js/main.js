"use strict";

(function () {
  var sidebarStorageKey = "adminHMD.sidebarMini";
  var themeStorageKey = "adminHMD.colorTheme";
  var desktopMedia = "(min-width: 992px)";

  function onReady(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback);
      return;
    }

    callback();
  }

  function isDesktop() {
    return window.matchMedia(desktopMedia).matches;
  }

  function canUseStorage() {
    try {
      var testKey = sidebarStorageKey + ".test";
      window.localStorage.setItem(testKey, "1");
      window.localStorage.removeItem(testKey);
      return true;
    } catch (error) {
      return false;
    }
  }

  function getSavedMiniState(storageAvailable) {
    if (!storageAvailable) {
      return false;
    }

    return window.localStorage.getItem(sidebarStorageKey) === "true";
  }

  function saveMiniState(storageAvailable, isMini) {
    if (storageAvailable) {
      window.localStorage.setItem(sidebarStorageKey, String(isMini));
    }
  }

  function getPreferredTheme(storageAvailable) {
    var savedTheme = storageAvailable ? window.localStorage.getItem(themeStorageKey) : "";

    if (savedTheme === "dark" || savedTheme === "light") {
      return savedTheme;
    }

    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      return "dark";
    }

    return "light";
  }

  onReady(function () {
    var body = document.body;
    var sidebarToggle = document.querySelector("[data-sidebar-toggle]");
    var themeToggles = document.querySelectorAll("[data-theme-toggle]");
    var themeIcons = document.querySelectorAll("[data-theme-icon]");
    var closeButtons = document.querySelectorAll("[data-sidebar-close]");
    var sidebarLinks = document.querySelectorAll(".sidebar-nav .nav-link");
    var mediaQuery = window.matchMedia(desktopMedia);
    var storageAvailable = canUseStorage();

    function initValidation() {
      var forms = document.querySelectorAll(".needs-validation");

      Array.prototype.forEach.call(forms, function (form) {
        form.addEventListener("submit", function (event) {
          if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
          }

          form.classList.add("was-validated");
        });
      });
    }

    function initTableSearch() {
      var searchInputs = document.querySelectorAll("[data-table-search]");

      Array.prototype.forEach.call(searchInputs, function (input) {
        var tableId = input.getAttribute("data-table-search");
        var table = document.getElementById(tableId);

        if (!table) {
          return;
        }

        input.addEventListener("input", function () {
          var query = input.value.trim().toLowerCase();
          var rows = table.querySelectorAll("tbody tr");

          Array.prototype.forEach.call(rows, function (row) {
            row.hidden = query !== "" && row.textContent.toLowerCase().indexOf(query) === -1;
          });
        });
      });
    }

    function updateThemeControls(theme) {
      var nextTheme = theme === "dark" ? "light" : "dark";
      var label = "Switch to " + nextTheme + " mode";
      var iconClass = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";

      Array.prototype.forEach.call(themeToggles, function (button) {
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
      });

      Array.prototype.forEach.call(themeIcons, function (icon) {
        icon.className = iconClass;
      });
    }

    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      document.documentElement.setAttribute("data-bs-theme", theme);

      if (storageAvailable) {
        window.localStorage.setItem(themeStorageKey, theme);
      }

      updateThemeControls(theme);
    }

    function initThemeToggle() {
      applyTheme(getPreferredTheme(storageAvailable));

      Array.prototype.forEach.call(themeToggles, function (button) {
        button.addEventListener("click", function () {
          var currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
          applyTheme(currentTheme === "dark" ? "light" : "dark");
        });
      });
    }

    initValidation();
    initTableSearch();
    initThemeToggle();

    function renderUserProfile(user) {
      var fallbackName = [user.first_name, user.last_name].filter(Boolean).join(" ");
      var profile = {
        name: fallbackName || user.username || user.email || "Utilisateur",
        workspace: user.role || "Espace de travail",
        avatar: user.avatar || "../assets/images/avatar/avatar.jpg"
      };

      var sidebarNameEl = document.querySelector(".sidebar-user strong");
      var sidebarWorkspaceEl = document.querySelector(".sidebar-user small");
      var sidebarAvatar = document.querySelector(".sidebar-user .avatar-img");
      var profileNameEls = document.querySelectorAll(".profile-name");
      var profileAvatarEls = document.querySelectorAll(".profile-button .avatar-img, .profile-button img");

      if (sidebarNameEl) sidebarNameEl.textContent = profile.name;
      if (sidebarWorkspaceEl) sidebarWorkspaceEl.textContent = profile.workspace;
      if (sidebarAvatar) { sidebarAvatar.src = profile.avatar; sidebarAvatar.alt = profile.name; }
      Array.prototype.forEach.call(profileNameEls, function (el) { el.textContent = profile.name; });
      Array.prototype.forEach.call(profileAvatarEls, function (img) { img.src = profile.avatar; img.alt = profile.name; });
      initLanguageSelector(user.preferred_language || "fr");
      applyRoleNavigation(user.role);
    }

    function initLanguageSelector(language) {
      var actions = document.querySelector(".navbar-actions");
      if (!actions || document.querySelector("[data-language-select]")) {
        var existing = document.querySelector("[data-language-select]");
        if (existing) existing.value = language;
        return;
      }
      var wrapper = document.createElement("div");
      wrapper.className = "language-control d-none d-md-block";
      wrapper.innerHTML = '<label class="visually-hidden" for="languageSelect">Langue</label><select class="form-select form-select-sm" id="languageSelect" data-language-select><option value="fr">FR</option><option value="en">EN</option></select>';
      actions.insertBefore(wrapper, actions.firstChild);
      var select = wrapper.querySelector("[data-language-select]");
      select.value = language;
      select.addEventListener("change", function () {
        if (!window.NexoraAPI) return;
        window.NexoraAPI.updateCurrentUser({ preferred_language: select.value }).catch(function () {
          select.value = language;
        });
      });
    }

    function applyRoleNavigation(role) {
      var navigation = document.querySelector(".sidebar-nav");
      if (!navigation) return;

      var brandTitle = document.querySelector(".brand-title");
      var brandSubtitle = document.querySelector(".brand-subtitle");
      if (brandTitle) brandTitle.textContent = "NEXORA";
      if (brandSubtitle) brandSubtitle.textContent = "Gestion commerciale";

      var currentPage = window.location.pathname;
      var links = [
        ["../dashboard/index.html", "speedometer2", "Tableau de bord"],
        ["../catalog/products.html", "box-seam", "Produits"],
        ["../sales/checkout.html", "cart-plus", "Ventes"],
        ["../reports/index.html", "bar-chart-line", "Rapports"],
        ["../inventory/index.html", "boxes", "Stocks"],
        ["../suppliers/index.html", "truck", "Fournisseurs"],
        ["../users/index.html", "people", "Clients"],
        ["../users/index.html", "person-gear", "Utilisateurs", "admin"],
        ["../finance/expenses.html", "cash-stack", "Dépenses", "admin"]
      ];

      navigation.innerHTML = links.filter(function (link) {
        return !link[3] || role === link[3] || role === "admin";
      }).map(function (link) {
        var active = currentPage.indexOf(link[0].replace("..", "")) !== -1;
        return '<a class="nav-link' + (active ? ' active' : '') + '" href="' + link[0] + '"' + (active ? ' aria-current="page"' : '') + '><span class="nav-icon"><i class="bi bi-' + link[1] + '" aria-hidden="true"></i></span><span class="nav-text">' + link[2] + '</span></a>';
      }).join("");
    }

    // Use the API user when this page is connected to the Nexora backend.
    function initUserProfile() {
      var user = window.adminHMDUser || { name: "Admin Hasan", workspace: "Active Workspace", avatar: "../../assets/images/avatar/avatar.jpg" };
      renderUserProfile({ first_name: user.name, role: user.workspace, avatar: user.avatar });

      if (window.NexoraAPI) {
        window.NexoraAPI.getCurrentUser().then(renderUserProfile).catch(function () {
          var currentPath = window.location.pathname;
          var publicPage = currentPath.indexOf("/auth/") !== -1 || currentPath.indexOf("/errors/") !== -1;
          if (!publicPage) window.location.href = "../auth/login.html";
        });
      } else {
        applyRoleNavigation("viewer");
      }
    }

    initUserProfile();

    function formatAmount(value) {
      return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "GNF", maximumFractionDigits: 0 }).format(value || 0);
    }

    function initDashboard() {
      if (!window.NexoraAPI || !document.querySelector("[data-dashboard-value]")) return;

      window.NexoraAPI.getDashboard().then(function (dashboard) {
        var values = {
          sales: formatAmount(dashboard.total_sales),
          products: dashboard.total_products,
          customers: dashboard.total_customers,
          stock: dashboard.total_stock_items,
          lowStock: dashboard.low_stock_products,
          received: formatAmount(dashboard.total_received)
        };

        document.querySelectorAll("[data-dashboard-value]").forEach(function (element) {
          var key = element.getAttribute("data-dashboard-value");
          if (Object.prototype.hasOwnProperty.call(values, key)) element.textContent = values[key];
        });
      }).catch(function (error) {
        document.querySelectorAll("[data-dashboard-error]").forEach(function (element) {
          element.textContent = error.message;
        });
      });
    }

    initDashboard();
    
    function initSalesChart() {
      var charts = document.querySelectorAll("[data-sales-chart], [data-sales-performance-chart]");
      if (!charts.length || !window.NexoraAPI) return;
      window.NexoraAPI.getReports().then(function (report) {
        var points = report.sales_by_period || [];
        var maximum = Math.max.apply(null, points.map(function (point) { return Number(point.value) || 0; }).concat([1]));
        var renderChart = function (chart) {
          chart.innerHTML = points.map(function (point) {
            var height = Math.max(8, Math.round(((Number(point.value) || 0) / maximum) * 100));
            return '<div class="chart-column" style="--bar-size:' + height + '%"><span></span><small>' + point.period.replace(/_/g, " ") + '</small></div>';
          }).join("") || '<div class="text-muted py-4">Aucune donnée.</div>';
        };
        charts.forEach(renderChart);
      }).catch(function () {
        charts.forEach(function (chart) { chart.innerHTML = '<div class="text-muted py-4">Indicateurs indisponibles.</div>'; });
      });
    }

    initSalesChart();

    function initDashboardUsers() {
      var table = document.querySelector("[data-dashboard-users]");
      if (!table || !window.NexoraAPI) return;
      window.NexoraAPI.getUsers().then(function (users) {
        table.innerHTML = users.slice(0, 5).map(function (user) {
          var name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username;
          var status = user.is_active ? "Actif" : "Inactif";
          var badge = user.is_active ? "success" : "secondary";
          return '<tr><td><div class="d-flex align-items-center gap-2"><div class="avatar-img avatar-sm d-grid place-items-center bg-light">' + name.charAt(0).toUpperCase() + '</div><div><p class="fw-semibold mb-0">' + name + '</p><p class="text-muted small mb-0">' + (user.email || user.phone || "-") + '</p></div></div></td><td>' + (user.role || "-") + '</td><td>-</td><td><span class="badge text-bg-' + badge + '">' + status + '</span></td><td>' + (user.created_at ? new Date(user.created_at).toLocaleDateString("fr-FR") : "-") + '</td><td class="text-end"><a class="btn btn-light btn-sm" href="../admin/user-details.html?id=' + user.id + '">Voir</a></td></tr>';
        }).join("") || '<tr><td colspan="6" class="text-muted text-center py-4">Aucun utilisateur.</td></tr>';
      });
    }

    initDashboardUsers();

    function initGlobalSearch() {
      var searchInput = document.querySelector(".admin-navbar .search-input");
      if (!searchInput || !window.NexoraAPI) return;

      var searchForm = searchInput.closest("form");
      var resultsBox = document.createElement("div");
      resultsBox.className = "dropdown-menu search-results-menu";
      resultsBox.hidden = true;
      searchForm.style.position = "relative";
      searchForm.appendChild(resultsBox);

      function escapeHtml(value) {
        return String(value || "").replace(/[&<>'"]/g, function (character) {
          return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character];
        });
      }

      function renderResults(results) {
        var groups = [
          ["Produits", results.products, "name"],
          ["Clients", results.customers, "full_name"],
          ["Fournisseurs", results.suppliers, "name"],
          ["Factures", results.invoices, "invoice_number"],
          ["Paiements", results.payments, "reference"]
        ];
        var html = groups.filter(function (group) { return group[1] && group[1].length; }).map(function (group) {
          return '<h6 class="dropdown-header">' + group[0] + '</h6>' + group[1].slice(0, 5).map(function (item) {
            return '<button class="dropdown-item search-result-item" type="button">' + escapeHtml(item[group[2]] || item.id) + '</button>';
          }).join("");
        }).join("");
        resultsBox.innerHTML = html || '<span class="dropdown-item-text text-muted">Aucun résultat</span>';
        resultsBox.hidden = false;
        resultsBox.classList.add("show");
      }

      searchInput.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" || !searchInput.value.trim()) return;
        event.preventDefault();
        window.NexoraAPI.get("core/search/?q=" + encodeURIComponent(searchInput.value.trim())).then(function (results) {
          searchInput.setAttribute("title", results.total + " résultat(s)");
          renderResults(results);
        }).catch(function (error) {
          searchInput.setAttribute("title", error.message);
          resultsBox.innerHTML = '<span class="dropdown-item-text text-danger">' + escapeHtml(error.message) + '</span>';
          resultsBox.hidden = false;
          resultsBox.classList.add("show");
        });
      });

      document.addEventListener("click", function (event) {
        if (!searchForm.contains(event.target)) {
          resultsBox.hidden = true;
          resultsBox.classList.remove("show");
        }
      });
    }

    initGlobalSearch();

    function initLogout() {
      if (!window.NexoraAPI) return;
      document.querySelectorAll(".dropdown-menu a").forEach(function (link) {
        if (link.textContent.trim() !== "Déconnexion") return;
        link.addEventListener("click", function (event) {
          event.preventDefault();
          window.NexoraAPI.logout().catch(function () {}).finally(function () {
            window.location.href = "../auth/login.html";
          });
        });
      });
    }

    initLogout();

    function initNotifications() {
      var menu = document.querySelector(".notification-menu");
      if (!menu || !window.NexoraAPI) return;
      window.NexoraAPI.getNotifications().then(function (notifications) {
        var unread = notifications.filter(function (notification) { return !notification.is_read; }).length;
        var dot = document.querySelector(".notification-dot");
        if (dot) dot.hidden = unread === 0;
        menu.innerHTML = '<div class="dropdown-header fw-bold text-body">Notifications (' + unread + ')</div>';
        menu.innerHTML += notifications.slice(0, 8).map(function (notification) {
          return '<button class="dropdown-item text-start notification-entry" type="button" data-notification-id="' + notification.id + '"><span class="notification-title">' + (notification.message || notification.event_type || "Notification") + '</span><span class="notification-time">' + (notification.created_at ? new Date(notification.created_at).toLocaleString("fr-FR") : "-") + '</span></button>';
        }).join("") || '<div class="dropdown-item text-muted">Aucune notification</div>';
        menu.querySelectorAll("[data-notification-id]").forEach(function (entry) {
          entry.addEventListener("click", function () {
            window.NexoraAPI.markNotificationRead(entry.getAttribute("data-notification-id")).then(function () {
              entry.classList.add("text-muted");
              if (dot) dot.hidden = true;
            });
          });
        });
      }).catch(function () {
        // The menu keeps its static fallback when no authenticated session exists.
      });
    }

    initNotifications();

    function initLogout() {
      if (!window.NexoraAPI) return;
      document.querySelectorAll(".dropdown-menu a").forEach(function (link) {
        var label = link.textContent.trim().toLowerCase();
        if (label !== "sign out" && label !== "déconnexion") return;
        link.addEventListener("click", function (event) {
          event.preventDefault();
          window.NexoraAPI.logout().catch(function () {}).finally(function () {
            window.location.href = "../auth/login.html";
          });
        });
      });
    }

    initLogout();

    function initCashflowAndAudit() {
      if (!window.NexoraAPI || !document.querySelector("[data-cashflow-summary]")) return;
      function amount(value) { return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "GNF", maximumFractionDigits: 0 }).format(value || 0); }
      window.NexoraAPI.getCashflow().then(function (cashflow) {
        document.querySelector("[data-cash-in]").textContent = amount(cashflow.cash_in);
        document.querySelector("[data-cash-out]").textContent = amount(cashflow.cash_out);
        document.querySelector("[data-cash-net]").textContent = amount(cashflow.net_cash);
      });
      window.NexoraAPI.getAudit().then(function (entries) {
        var list = document.querySelector("[data-audit-list]");
        var renderAudit = function (entry) { return '<div class="list-group-item px-0"><span class="fw-semibold">' + (entry.action || "Opération") + '</span><small class="d-block text-muted">' + (entry.details || entry.model_name || "-") + ' · ' + (entry.created_at ? new Date(entry.created_at).toLocaleString("fr-FR") : "-") + '</small></div>'; };
        list.innerHTML = entries.length ? entries.slice(0, 6).map(renderAudit).join("") : '<div class="text-muted py-3">Aucun événement d’audit.</div>';
        var dashboardActivity = document.querySelector("[data-dashboard-activity]");
        if (dashboardActivity) dashboardActivity.innerHTML = entries.length ? entries.slice(0, 3).map(function (entry) { return '<div class="activity-item"><span class="activity-dot bg-primary"></span><div><p class="mb-1 fw-semibold">' + (entry.action || "Opération") + '</p><p class="text-muted small mb-0">' + (entry.details || entry.model_name || "-") + '</p></div></div>'; }).join("") : '<div class="text-muted py-3">Aucune activité récente.</div>';
      });
    }

    initCashflowAndAudit();

    if (!sidebarToggle) {
      return;
    }

    function setClass(element, className, enabled) {
      if (enabled) {
        element.classList.add(className);
      } else {
        element.classList.remove(className);
      }
    }

    function setToggleExpanded() {
      var expanded = isDesktop()
        ? !body.classList.contains("sidebar-mini")
        : body.classList.contains("sidebar-open");

      sidebarToggle.setAttribute("aria-expanded", String(expanded));
    }

    function closeMobileSidebar() {
      body.classList.remove("sidebar-open");
      setToggleExpanded();
    }

    function toggleSidebar() {
      if (isDesktop()) {
        body.classList.toggle("sidebar-mini");
        saveMiniState(storageAvailable, body.classList.contains("sidebar-mini"));
      } else {
        body.classList.toggle("sidebar-open");
      }

      setToggleExpanded();
    }

    function addCloseHandlers(items) {
      Array.prototype.forEach.call(items, function (item) {
        item.addEventListener("click", function () {
          if (!isDesktop()) {
            closeMobileSidebar();
          }
        });
      });
    }

    if (getSavedMiniState(storageAvailable) && isDesktop()) {
      body.classList.add("sidebar-mini");
    }

    sidebarToggle.addEventListener("click", toggleSidebar);
    addCloseHandlers(closeButtons);
    addCloseHandlers(sidebarLinks);
    setToggleExpanded();

    function handleBreakpointChange() {
      if (isDesktop()) {
        body.classList.remove("sidebar-open");
        setClass(body, "sidebar-mini", getSavedMiniState(storageAvailable));
      } else {
        body.classList.remove("sidebar-mini");
      }

      setToggleExpanded();
    }

    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener("change", handleBreakpointChange);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleBreakpointChange);
    }
  });
})();
