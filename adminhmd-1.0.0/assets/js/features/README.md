# Frontend features

Chaque dossier contient le point d'entree JavaScript d'un domaine metier Nexora.

- `dashboard/`: indicateurs de pilotage
- `products/`: catalogue produits
- `customers/`: clients
- `suppliers/`: fournisseurs
- `inventory/`: stock et emplacements
- `transfers/`: transferts entre emplacements
- `sales/`: caisse et ventes
- `payments/`: paiements
- `notifications/`: notifications
- `reports/`: rapports
- `users/`: utilisateurs et roles
- `expenses/`: dépenses
- `purchases/`: commandes fournisseurs
- `receipts/`: réceptions de marchandises
- `invoices/`: factures

`loader.js` charge les modules sur les pages HTML adaptees. Les appels HTTP restent centralises dans `../api.js`.

Les pages HTML sont classees dans `../../html/` par domaine :

- `dashboard/index.html`
- `catalog/products.html`
- `sales/checkout.html`
- `inventory/index.html`
- `suppliers/index.html`
- `users/index.html`
- `reports/index.html`
- `finance/expenses.html`
- `billing/invoices.html`
- `notifications/index.html`
- `profile/index.html`
- `auth/` pour la connexion et l'inscription
- `admin/` pour l'administration des utilisateurs
