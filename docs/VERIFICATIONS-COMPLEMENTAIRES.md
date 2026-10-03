# DayOne — décisions complémentaires et points à vérifier

> **Décision de mise en œuvre du 3 octobre 2026.** À la demande du porteur du projet, le prototype actuel exécute l'OCR, la relecture et le stockage exclusivement sur la machine locale. Le bot WhatsApp est simulé localement, sans connexion à Meta ni à une API de modèle. L'architecture PWA avec traitement et synchronisation distants décrite plus bas reste une étude antérieure et n'est pas l'architecture du prototype livré. Voir [admin/README.md](../admin/README.md).

Ce document complète [l'analyse principale](ANALYSE-ET-PLAN.md). Il fixe une interprétation de travail pour construire un prototype vérifiable. Il ne transforme pas les ambiguïtés des consignes en autorisations officielles. Référence principale : `consignes-fr-en.pdf` dans `dayone-participants.zip`, version française p. 1–4 et version anglaise p. 5–8. Les sources originales restent inchangées.

## 1. Contradictions et limites du mandat

| Sujet | Formulations vérifiées | État et décision de travail |
|---|---|---|
| Image d'origine et identifiants | P. 2 : « Tout identifiant direct visible sur le papier (...) doit être ignoré ou masqué, jamais stocké » ; p. 2–3 : « Conserver l'image d'origine liée au dossier » et « Les images d'origine (...) ne doivent pas être modifiées ». L'anglais p. 6–7 reprend les deux exigences. | **Question organisateur.** Dans le produit, créer en mémoire une image expurgée avant toute persistance/transmission, garder un lien de provenance et préserver les fichiers fournis intacts hors application. Une copie expurgée n'est pas littéralement l'image intacte : demander si elle satisfait le critère. En attendant, ne jamais enregistrer un original comportant un identifiant visible. |
| Hépatite B et C | P. 1–2 : schéma demandé comprenant « hépatite C » ; CSV : `hepatitis c test result`. Le formulaire PDF des dix dossiers affiche `Ag HBs`, qui désigne l'antigène de l'hépatite B ; la version anglaise p. 5–6 demande aussi « hepatitis C ». | **Résolu pour l'implémentation, question pour la note.** Définir deux champs indépendants `hepatitis_b_surface_antigen` et `hepatitis_c_test`. Une inscription HBs ne remplit jamais HCV. Demander quelle source le jury utilise pour noter ces champs. |
| Langues | P. 2 : données annoncées en français, arabe et anglais ; p. 4 : exactitude d'extraction sur ces langues pour 30 points ; même p. 4 : « Robustesse sur l'écriture arabe et les pages multilingues » listée comme bonus. | **Choix provisoire.** La qualité de base est à mesurer sur toutes les langues effectivement présentes et annotées. Le bonus semble viser une robustesse supérieure, sans définition ni points. Ne pas annoncer une couverture arabe générale sur le petit corpus. |
| Référence par page et CSV | P. 2 : « valeurs de référence de chaque page » et CSV synthétique de 200 lignes. L'archive ne contient pas de table explicite reliant les 80 pages, 10 dossiers et 200 lignes. | **Question organisateur.** Annoter un sous-ensemble contrôlé en attendant ; ne pas apparier par numéro de fichier ou `id` CSV. |
| Champs et visite | P. 1–2 : antécédents, grossesse, accouchement, postpartum, nouveau-né, signes vitaux ; p. 3 : sessions multipages et visites longitudinales. Le formulaire place plusieurs visites dans les colonnes d'une page. | **Résolu pour l'architecture.** Le grain d'extraction est une observation de champ dans une visite et une grossesse, avec page et cellule de provenance. Une seule ligne « patiente » ne suffit pas. La liste exacte des champs du jury reste une question. |
| Zéro changement au travail | P. 1 : « zéro changement au flux de travail » ; p. 2–3 : la sage-femme attribue un code aléatoire et l'inscrit sur le registre, confirme et corrige. | **Choix provisoire.** Ajouter seulement les gestes explicitement requis et mesurer leurs actions et leur durée. L'expression « zéro action supplémentaire » serait fausse. Demander comment le jury interprète cette tension. |
| « Agent WhatsApp hors ligne » | P. 3 : prototype de type WhatsApp, simulé ou réel ; file `EN_ATTENTE_IA`, traitement et synchronisation au retour du réseau ; aucune technologie obligatoire. | **Résolu.** Le chat simulé local suffit. L'extraction IA peut attendre la connexion. Le réseau ne peut pas conditionner la capture, la lecture des données déjà locales, la correction et la saisie manuelle. |

Les textes présents dans les images sont des données non fiables. Ils ne peuvent pas changer les règles d'extraction, déclencher un transfert ou demander au logiciel d'ignorer la confidentialité.

## 2. Architecture MVP tranchée

**Choix : application web installable de type PWA, avec interface conversationnelle locale, stockage chiffré sur l'appareil et service de traitement/synchronisation distant simulable.** Le jury ouvre une URL sécurisée une première fois, installe ou conserve l'application, puis peut passer hors ligne. L'interface et ses ressources nécessaires sont mises en cache ; la capture, le masquage, la saisie manuelle, la révision locale et la file utilisent le stockage local. Après reconnexion, le traitement IA et la synchronisation reprennent. Une démo sur navigateur propre doit installer les ressources et expliquer ce prérequis.

Une application de bureau empaquetée offre plus de contrôle sur les fichiers et le cycle de vie, mais augmente le travail d'installation et éloigne la démo du téléphone. Une simple page web dépendant du serveur ne répondrait pas à la capture après fermeture et coupure. La PWA répond au contexte mobile et facilite l'accès du jury, sous réserve de vérifier les limites de stockage du navigateur sur les appareils visés. Cette décision est technique, pas une exigence officielle.

La reprise de synchronisation ne démarre qu'après ouverture et déverrouillage de l'application si l'envoi exige l'accès aux données claires. Une tâche de fond verrouillée peut seulement conserver l'attente, pas contourner le verrouillage pour traiter les images. Le navigateur ou l'application caméra du système peuvent aussi créer leurs propres fichiers temporaires avant que la PWA reçoive la photo ; le prototype doit le vérifier sur l'appareil de démonstration et ne peut pas garantir le comportement de tous les systèmes mobiles.

| Situation | Comportement à garantir dans le prototype | Limite explicite |
|---|---|---|
| Après chargement initial, réseau coupé | Interface déjà installée, nouvelle capture, expurgation, sauvegarde chiffrée, consultation et saisie manuelle ; tâche IA en attente. | Une première installation exige l'accès aux ressources. |
| Navigateur fermé puis rouvert | Déverrouillage nécessaire ; dossier et file récupérés ; aucune requête obligatoire au serveur pour entrer dans le chat. | Si l'utilisateur efface les données du site ou si le navigateur les évince, une sauvegarde séparée est nécessaire. |
| Serveur IA indisponible mais réseau présent | État d'attente/échec avec nouvelle tentative ; flux manuel entier utilisable. | Aucune promesse de lecture IA en local. |
| Serveur de synchronisation indisponible | Dossier local validé et opération en attente, sans fausse mention « synchronisé ». | La continuité entre plusieurs appareils attend la réception serveur. |

Les capacités de stockage hors ligne et les règles d'éviction des navigateurs doivent être vérifiées sur l'appareil cible. L'API de persistance peut réduire le risque d'éviction, mais ne remplace pas une sauvegarde : voir [IndexedDB, W3C](https://www.w3.org/TR/IndexedDB-2/) et [quotas et éviction, MDN](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria). Les primitives cryptographiques du navigateur sont décrites par [Web Cryptography, W3C](https://www.w3.org/TR/webcrypto/). Il faudra choisir et documenter les versions, licences et compatibilités réelles avant de coder.

## 3. Confidentialité, chiffrement et clés

**Périmètre :** chiffrer par chiffrement authentifié toutes les images expurgées, observations, dossiers, journaux métier et opérations en attente avant écriture dans le stockage local. Le chiffrement en transit protège les échanges quand le réseau revient. Garder les données claires uniquement en mémoire pendant une session déverrouillée et pendant le traitement autorisé. Les métadonnées non chiffrées doivent être réduites à ce qui permet de retrouver et synchroniser des objets sans révéler le dossier.

**Clé :** générer aléatoirement une clé de données locale lors de l'installation ; l'envelopper par une clé dérivée d'une phrase secrète de la sage-femme avec sel unique et paramètres documentés. Ne persister que la clé enveloppée, jamais la phrase secrète ni la clé claire. Au démarrage, l'utilisateur déverrouille ; la clé déchiffrée ne reste qu'en mémoire. Verrouiller après inactivité et à la fermeture ou au changement d'utilisateur. Cette conception doit faire l'objet d'une revue cryptographique avant tout usage avec des données réelles. Une clé enregistrée directement et utilisable par toute page du même navigateur ne protège pas contre l'accès à une session ouverte ou à un script malveillant.

Pour l'extraction distante autorisée sur les seules données synthétiques de démonstration, préparer les données en mémoire après déverrouillage et les transmettre uniquement quand l'utilisateur déclenche ou reprend le traitement. Le chiffrement local ne protège plus l'image pendant ce traitement côté service ; définir la durée de rétention, les journaux et les droits d'accès du service. Un chiffrement de bout en bout incompatible avec la lecture par ce service ne doit pas être promis.

**Sauvegarde et perte :** permettre l'export d'une sauvegarde chiffrée explicitement déclenchée et vérifiée par restauration sur appareil de test. Sur appareil partagé, un compte et une phrase secrète propres à chaque sage-femme évitent le partage involontaire des dossiers. Si phrase secrète, clé enveloppée et sauvegarde sont perdues, les données chiffrées peuvent devenir irrécupérables ; l'application doit l'indiquer avant l'usage. Ne promettre « aucune perte » qu'au regard des scénarios testés, avec limites d'appareil et de sauvegarde écrites.

**Masquage avant persistance :** analyser l'image en mémoire, appliquer les zones connues et détectées d'identifiants directs, puis demander une confirmation visuelle de l'expurgation. Si un identifiant est visible ou si la détection est incertaine, bloquer la sauvegarde et la transmission de l'image concernée ; proposer masquage manuel ou reprise. La copie expurgée peut préserver les coordonnées des zones et un identifiant de capture, sans stocker leur contenu. Ne pas créer une miniature ou un brouillon persistant avant ce contrôle.

**Revue des surfaces de fuite :** inspection du stockage local, miniatures et aperçus, blobs d'upload temporaires, texte OCR brut, cache du navigateur, cache du service worker, traces de requête, erreurs, télémétrie, exports, captures de démonstration, journaux serveur et sauvegardes. Les ressources statiques du service worker peuvent être mises en cache ; les images et réponses contenant des valeurs ne doivent pas y être cachées en clair. Refuser l'envoi vers un service tiers de toute donnée réelle, comme l'exige la p. 3. Même avec des données synthétiques, obtenir confirmation des droits de partage et de la licence avant API externe ou publication.

**Accès :** contrôle d'autorisation appliqué par le service à chaque demande d'image, de dossier et de version ; vérifier le rôle et le rattachement autorisé, avec refus effectif d'un lien copié. L'interface seule ne constitue pas un contrôle d'accès. La session ouverte reste exposée à une personne qui tient l'appareil ; chiffrement au repos et verrouillage réduisent deux risques différents. Le prototype ne garantit pas la sécurité clinique ni la conformité réglementaire d'un déploiement réel.

## 4. Cycle de vie, versions et concurrence

Au lieu d'un seul statut qui combine plusieurs dimensions, garder quatre états indépendants, plus l'identité de la version :

| Dimension | États principaux | Sens |
|---|---|---|
| Capture/document | `CAPTURÉ`, `MASQUAGE_À_VÉRIFIER`, `PRÊT`, `RENUMÉRISATION_SUSPECTÉE` | Pages locales et provenance. |
| Tâche IA | `EN_ATTENTE_IA`, `EN_COURS`, `TRAITÉ_IA`, `ÉCHEC_IA`, `SAISIE_MANUELLE` | Traitement distinct de la validation. |
| Révision et liaison | `À_RÉVISER`, `VALIDÉ`, `LIAISON_À_DÉCIDER`, `PATIENTE_LIÉE`, `DOUBLON_SUSPECTÉ` | Décisions humaines. |
| Synchronisation | `LOCAL`, `EN_ATTENTE`, `EN_COURS`, `ÉCHEC_SYNC`, `SYNCHRONISÉ`, `CONFLIT` | Confirmation de réception d'une version donnée. |

Le flux linéaire de la p. 3 (`CAPTURÉ` à `SYNCHRONISÉ`) demeure visible à l'utilisateur, mais les dimensions internes évitent qu'une correction après synchronisation rende le dossier simultanément « validé et synchronisé » à tort. Chaque observation et dossier porte une version monotone et un journal d'événements non destructif. Une nouvelle correction crée une nouvelle version locale en attente, sans modifier rétroactivement la preuve reçue.

**Invariants à respecter :**

1. Une extraction IA ne remplace jamais une valeur confirmée ou corrigée par une personne. Une réponse IA tardive est conservée comme suggestion de sa version source ou ignorée avec motif.
2. Une réponse de synchronisation confirme uniquement la version dont elle porte l'identifiant. Si une correction est intervenue, la version nouvelle reste en attente.
3. Le serveur accepte une écriture uniquement si la version attendue correspond ; sinon il renvoie un conflit et les deux versions pour décision explicite. Aucune résolution silencieuse « dernier arrivé gagne ».
4. Chaque opération d'envoi possède une clé d'idempotence stable, réutilisée à chaque tentative. La transaction serveur enregistre ensemble le résultat métier et cette clé ; un rejouement renvoie le résultat existant.
5. Une opération n'est retirée de la file qu'après accusé de réception durable de la même version. Si l'accusé est perdu, la tentative suivante réutilise la clé.
6. Deux onglets locaux ne modifient pas aveuglément la même version : un verrou local ou un contrôle de version refuse le deuxième enregistrement et propose de recharger/fusionner.
7. Une demande de suppression, de renumérisation ou de changement de liaison conserve un historique de versions et exige une confirmation humaine.

**Cas concrets :** réponse IA après correction → suggestion sans effet sur la correction ; correction pendant synchro → nouvelle version non synchronisée ; deux appareils corrigent le même champ → conflit explicite avec provenance ; panne après écriture serveur → renvoi idempotent ; accusé perdu → opération conservée puis reconnue ; deux onglets → conflit local ; réseau intermittent → reprises avec délais et état visible. Ces comportements sont des spécifications à implémenter, pas des tests déjà réussis.

## 5. Identité et liaison des visites

Le modèle distingue `Patiente` (identifiant interne aléatoire), `Grossesse` (épisode), `Visite` (date/ordre et type), `Registre` (document multipage) et `Capture` (photo/version d'une page). Deux grossesses de la même femme partagent une patiente, mais ne fusionnent pas les visites. Les références de fichiers et le `id` du CSV ne sont pas des identifiants de production.

Le code inscrit sur le papier est généré aléatoirement, assez long pour réduire les collisions, avec contrôle des caractères confus et vérification d'unicité **dans le périmètre connu**. La sage-femme le confirme avant de l'écrire. L'ID interne est généré séparément et ne dérive pas de l'âge, village, nom, téléphone ou autre donnée personnelle. Hors ligne, l'unicité globale n'est pas garantie : détecter et faire résoudre une collision à la synchronisation.

Un code correct propose la patiente et son historique ; une nouvelle grossesse crée un nouvel épisode après choix humain. Un code oublié, mal lu, dupliqué ou absent conduit à « Je ne sais pas » ou à des correspondances possibles, jamais à une fusion automatique. Les indices admissibles pour proposer, sans identifier à eux seuls, sont le code partiel, l'établissement, la chronologie, l'épisode et les sections de registre non identifiantes déjà autorisées. Âge/village ou état de santé peuvent être communs à plusieurs personnes et sensibles : les montrer au minimum, avec accès restreint, sans les transformer en empreinte stable. Nom et téléphone ne servent pas au rattrapage.

Si une liaison était mauvaise, l'utilisateur autorisé peut l'annuler avec motif ; les versions et références aux visites sont corrigées par transaction, puis les vues agrégées sont recalculées. Une renumérisation compare le document proposé aux captures existantes, présente les différences et laisse choisir quelles observations remplacer. La similarité d'image sert à signaler un doublon, sans décider seule qu'il s'agit de la même visite.

## 6. Contrat d'extraction et d'incertitude

Valider chaque sortie IA contre un contrat JSON versionné et une liste fermée de champs. Une observation comprend au minimum : `field_path`, `episode_id`, `visit_id` ou `visit_slot`, `source_page_id`, `source_region`, `raw_value` expurgée, `normalized_value`, `unit`, `status`, `uncertainty_reason`, `ai_confidence` si justifiée, `extractor_version`, puis `review_state`, `reviewer_id` et `review_event_id` séparés. Une sortie invalide passe en échec ou révision ; elle n'est pas intégrée en silence. Les coordonnées de preuve doivent pointer vers la copie expurgée consultable.

Les six statuts exigés restent `CONNU`, `INCONNU`, `NON_FOURNI`, `ILLISIBLE`, `NON_APPLICABLE`, `À_RÉVISER`. Distinguer « page attendue absente » comme motif documentaire ; ne pas transformer automatiquement en `NON_FOURNI` la valeur d'une page qui n'a jamais été photographiée. Une case non cochée n'est une réponse négative que si la logique du formulaire le garantit. Deux valeurs contradictoires sur des pages différentes demeurent deux observations avec leur visite et une question de révision. Date ambiguë, colonne incertaine et unité absente restent `À_RÉVISER` ou `ILLISIBLE` selon la preuve.

La confiance est **par champ**, séparée de la validation humaine. Un nombre sorti par le modèle ne doit pas être présenté comme une probabilité calibrée sans comparaison aux erreurs sur validation. Avec peu d'exemples indépendants, préférer des catégories expliquées (« lecture claire », « doute sur caractère », « doute sur colonne », « impossible ») et un ordre de questions. Si une calibration numérique devient possible, elle doit utiliser des dossiers séparés et rapporter les effectifs et erreurs par tranche.

Les règles de cohérence vérifient que la transcription est plausible et bien située ; elles n'émettent ni alerte de risque clinique, ni conduite à tenir. Un résultat VIH ou une mesure de tension ne déclenche jamais une recommandation médicale dans ce défi.

## 7. Évaluation honnête sur le corpus limité

Le découpage proposé de 6/2/2 dossiers dans l'analyse principale est **un point de départ fragile**, car le PDF n'offre que dix dossiers, avec sections répétées et apparence très semblable. Le test final doit rester séparé dès avant le réglage, mais son intervalle d'incertitude sera large. Prévoir aussi une validation croisée par groupe uniquement sur les dossiers de développement pour estimer la variabilité. Les cinq photos de terrain synthétique constituent un jeu de robustesse descriptif si leurs champs sont annotables ; ne pas les assimiler à des patientes réelles ou à toutes les langues annoncées.

L'annotation locale requiert pour chaque cellule : dossier, épisode, section, page, visite/colonne, champ, valeur visible brute, valeur normalisée, statut, zone de preuve et commentaire. Une deuxième personne vérifie un échantillon ciblé ainsi que tous les désaccords ou champs sensibles ; arbitrer les écarts avant de figer les références. Marquer « non annotable » avec motif, et publier ce nombre hors du dénominateur principal. Toute correction des références après consultation du test doit être tracée.

Dédupliquer par hash et inspection visuelle : les fichiers PDF et PNG d'une même page peuvent ne pas partager les mêmes octets ; les variantes redressées, floutées, recadrées et les colonnes d'un même dossier doivent rester dans le même groupe. Chercher aussi les doublons visuels et quasi-doublons entre groupes. Il est interdit d'utiliser le texte embarqué du PDF ou le CSV comme réponse pendant une évaluation de photos si le produit ne disposerait pas de cette information sur le terrain.

Rapporter les résultats **par dossier et type de champ**, avec effectifs, puis agrégés : exactitude stricte, exactitude normalisée selon règles figées, statut correct, couverture/abstention, faux positifs sur champs absents, erreurs à forte confiance, attribution à la bonne visite. Donner les résultats IA seule, après révision humaine et le temps/actions de cette révision. Pour les cas rares, montrer les comptes bruts. Les dégradations artificielles évaluent la résistance à ces transformations, pas la performance en milieu réel ; le corpus ne prouve pas une généralisation multilingue.

Le score du jury ne peut pas être calculé à partir de ces métriques locales, car la formule et le test caché ne sont pas fournis. Ne publier aucun pourcentage avant une exécution sur références établies.

## 8. Interaction et charge de travail

L'interface affiche un résumé par visite avec provenance accessible en un geste. Les champs lisibles et cohérents peuvent être **confirmés par groupe** après une vue récapitulative ; les champs à doute, dates, unités, correspondances et conflits sont présentés individuellement. Une correction ouvre immédiatement la zone de preuve expurgée, propose la valeur candidate et permet l'édition. « Reprendre la photo » remplace la capture de travail par une nouvelle version, sans effacer l'historique. La conversation et sa position reprennent après fermeture. Le mode manuel couvre tous les champs, section par section, avec sauvegarde progressive.

Mesurer sur scénarios : nombre de questions, actions, reprises de photo, corrections, temps total et taux d'erreurs restantes après validation. Cette mesure permet de juger si le prototype respecte l'intention « sans modifier les pratiques » au mieux, sans affirmer qu'il n'ajoute aucun geste.

## 9. Matrice d'acceptation à exécuter pendant l'implémentation

Les lignes ci-dessous définissent des vérifications futures. Aucun de ces scénarios n'a été exécuté sur un produit DayOne dans ce dépôt.

| Précondition | Action | Résultat attendu | Preuve à conserver |
|---|---|---|---|
| Application chargée, réseau coupé | Capturer, expurger, enregistrer, fermer et rouvrir | Dossier et file récupérés après déverrouillage ; aucune image claire persistée | Capture d'état, inspection stockage, journal d'événements expurgé |
| IA indisponible | Remplir manuellement toutes les sections | Validation et liaison possibles sans IA | Parcours complet enregistré |
| Réponse IA retardée, champ humain corrigé | Faire arriver la réponse | Correction conservée ; IA visible comme suggestion ancienne | Versions avant/après et événement |
| Correction en cours de synchronisation | Recevoir l'accusé de l'ancienne version | Ancienne version confirmée, nouvelle toujours en attente | Identifiants des deux versions |
| Serveur a écrit, accusé perdu | Rejouer la même opération | Un seul dossier/événement serveur | Clé idempotente et comptage serveur |
| Deux onglets avec même version | Corriger dans les deux | Deuxième enregistrement refusé ou conflit explicite | Versions et message de conflit |
| Deux appareils modifient même champ | Synchroniser le second | Conflit visible ; aucune valeur effacée silencieusement | Deux valeurs, auteurs, versions |
| Deux correspondances plausibles | Ajouter une visite | Choix humain ou « Je ne sais pas », aucune création automatique | Historique de décision |
| Code collisionné ou erroné | Tenter la liaison | Aucune fusion automatique ; résolution proposée | Deux profils conservés |
| Registre déjà capturé | Photographier à nouveau | Dossier existant et différences montrés ; mises à jour choisies | Versions et sélection |
| Photo avec nom et téléphone | Capturer et tenter d'enregistrer | Masquage confirmé ou sauvegarde bloquée ; aucune valeur dans stockage/requête/log | Recherche de chaînes sentinelles dans toutes les surfaces |
| Rôle non autorisé | Ouvrir URL/image copiée | Refus côté service | Réponse serveur et journal d'accès expurgé |
| Dossier jamais utilisé pour réglage | Lancer l'extraction réelle | Métriques et erreurs calculées sur la sortie, sans réponse préremplie | Trace du pipeline, paramètres, référence figée |

Pour la démo, garder une extraction réelle reproductible. Une vidéo de secours ou une sortie mise en cache doit être annoncée clairement. Les données préremplies ne doivent pas être présentées comme une extraction exécutée en direct.

## 10. Priorités pour viser le barème

| Priorité | Portée MVP | Critère servi | Effort indicatif sur 24 h disponibles |
|---|---|---|---:|
| 1 | Schéma, annotations, extraction réelle minimale et attribution aux visites | Extraction 30 ; incertitude 20 | 5–7 h |
| 2 | Chat de révision, preuve, correction, reprise, manuel, multipages | Conversation 20 | 4–5 h |
| 3 | Capture expurgée, chiffrement, file durable et synchronisation idempotente | Hors ligne 15 ; confidentialité 10 | 5–7 h |
| 4 | Code, choix de liaison, renumérisation versionnée | Liaison/confidentialité 10 | 2–3 h |
| 5 | Évaluation, README, packaging, démo et marge d'intégration | Code 5 ; crédibilité de tous les critères | 4–6 h |

Ces budgets dépassent possiblement 24 h selon la taille et l'expérience de l'équipe ; intégrer les tâches en parallèle si l'équipe le permet et geler tôt une démo stable. Les tâches difficiles à simuler honnêtement sont le chiffrement, la reprise après fermeture, les conflits et la qualité d'extraction. Elles demandent une preuve de fonctionnement et ne doivent pas rester des écrans statiques.

À différer tant que les six critères de base ne fonctionnent pas : bac à sable WhatsApp réel, tableau de bord d'agrégats, interface bilingue complète, entraînement d'un modèle spécialisé, infrastructure distribuée. Contrôle de qualité photo peut être ajouté rapidement s'il réduit des échecs observés. L'arabe mérite des essais sur exemples réellement présents/annotés, sans promesse générale.

La matrice critère → preuve finale est : extraction → tableau des valeurs correctes et erreurs sur dossier réservé ; incertitude → statuts et erreurs confiantes ; conversation → enregistrement d'un parcours corrigé et manuel ; hors ligne → capture puis fermeture/coupure/reprise ; liaison/confidentialité → décision ambiguë, conflit, refus d'accès et inspection des identifiants ; code/documentation → commande de démarrage, configuration, références, versions et limites.

## 11. Inconnues à lever et risques résiduels

Questions prioritaires aux organisateurs, sans contact effectué : (1) mapping officiel images/valeurs/CSV et formule de notation ; (2) acceptation d'une image expurgée comme image conservée ; (3) couverture réelle des langues et statuts dans le test ; (4) droits d'envoi des données synthétiques à une API et de publication dans un dépôt/vidéo ; (5) lecture exacte du « zéro changement » avec code écrit ; (6) règles administratives propres à cette édition : calendrier, équipe, accès du jury et soumission.

La fiche locale mentionne HxBuddy et Devpost, mais aucune page administrative spécifique vérifiable n'a été retrouvée dans cet audit. Ne pas appliquer les règles d'un autre concours Devpost. Les licences du modèle, des poids et des bibliothèques devront être vérifiées avant intégration et citées dans la remise.

Risques résiduels même avec ce MVP : compatibilité et éviction du stockage PWA, session déverrouillée sur appareil partagé, perte de phrase secrète, qualité de masquage des identifiants, petite taille du jeu de test, décalage entre spécimens synthétiques et photos de terrain, ambiguïté des formulaires et de l'évaluation du jury. Documenter chaque limite dans la démonstration et le README ; ne pas revendiquer une efficacité clinique ni une note attendue.
