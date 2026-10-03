# Contrat UX — console DayOne

Sources métier : `../ANALYSE-ET-PLAN.md`, `../VERIFICATIONS-COMPLEMENTAIRES.md` et PDF des consignes dans l'archive. Ce contrat décrit le prototype admin local ; il ne certifie pas un déploiement clinique.

- Audience : administrateur local, relecteur autorisé, données synthétiques uniquement.
- Locale : français ; dates absolues en ISO dans la base, affichage français dans l'interface.
- Accessibilité visée : WCAG 2.2 AA. Contrôles natifs, labels, focus visible et régions de statut.
- Navigation : Tableau de bord, Relecture, Bot local, Configuration. L'URL conserve la section et le dossier ouvert.
- Liste de dossiers : pagination serveur, 20 par page ; recherche par code et filtre de statut ; aucune donnée personnelle directe.
- Relecture : un changement de champ reste dans le dossier ; le serveur valide la version attendue ; après conflit, l'interface recharge la version et préserve la valeur saisie dans le formulaire jusqu'à décision de l'utilisateur.
- Confirmation : validation du dossier après relecture explicite de chaque champ ; une valeur inconnue peut être confirmée comme inconnue.
- Notifications : bannière persistante pour OCR non prêt ou erreur de chargement, message de statut accessible pour succès, erreur à côté de l'action pour récupération.
- Opérations externes : aucune. Le bot est simulé localement ; aucune connexion réelle Meta ni API de modèle n'est offerte dans cette version.
- Sécurité : session locale HTTP-only, protection CSRF des mutations, serveur lié à `127.0.0.1`, valeurs et images chiffrées au repos ; le mot de passe reste dans l'environnement local.
- Primitive canonique : contrôles HTML natifs ; fonctions `api`, `notify` et `render` partagées dans `static/app.js` ; tokens visuels dans `static/styles.css`.
