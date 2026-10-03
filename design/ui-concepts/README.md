# Direction proposée pour la console DayOne

Maquettes générées avec l'outil intégré imagegen, après lecture de
`admin/static/app.js`. Aucun document patient ni image source fourni au modèle.
Les exemples et les registres représentés sont entièrement inventés.
Ces images ne sont pas des captures de fonctionnalités implémentées.

## Ce que le code justifie d'afficher

- Vue d'ensemble : nombres de dossiers et champs à confirmer, dossiers récents,
  état de disponibilité des poids OCR ; file de travaux via `/api/jobs`.
- Relecture : code, champs et unités, statut documentaire distinct de la
  confirmation humaine, provenance OCR par page, images expurgées, visites,
  historique. Présenter l'image à côté des valeurs plutôt qu'en dessous.
- Bot : conversations par code, historique des messages, propositions et
  commandes de confirmation/correction, accès au dossier associé. Le bot
  est déterministe et local, sans connexion WhatsApp.
- Configuration : langues FR/EN, ordre de relecture, poids présents/absents,
  traitements en attente et reprise, restriction au rôle administrateur.

## Corrections de conception

Réduire les cartes de compteurs et les bandeaux répétés. Mettre les dossiers
et les actions au premier plan. Employer une couleur d'accent sobre et une
couleur de doute documentaire ; ne pas coder un risque clinique par couleur.
Afficher les libellés lisibles (« À réviser ») plutôt que les constantes API.

Les maquettes sont illustratives : textes, dates, nombres et détails du faux
registre peuvent varier entre images. Pour l'implémentation :

- « Poids présents » ne prouve pas que le moteur est opérationnel ; conserver
  cette distinction dans le statut.
- Un champ vide peut être confirmé comme « Non fourni » ; le bouton ne doit
  pas être désactivé pour ce seul motif.
- La confiance OCR est brute et non calibrée, jamais un score médical.
- Le zoom, les onglets, les commandes rapides et la disposition comparative
  sont des propositions d'interface à implémenter, pas des fonctions vérifiées.
- Ne pas ajouter de téléchargement d'image, d'export, de rotation de clé,
  d'API externe ou de connexion WhatsApp à partir d'un pictogramme généré.
- La table d'activité doit refléter les événements réels sans inventer de champ
  ou d'information absente du schéma courant.

Le code de l'application n'est pas modifié par cette exploration visuelle.
