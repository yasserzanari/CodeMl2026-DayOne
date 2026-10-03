# DayOne : analyse des données, règles et plan de réalisation

Date : 3 octobre 2026. Travail demandé : analyser le défi et les données, préparer une stratégie de réalisation et d'évaluation. Ce document ne constitue pas une application réalisée ni un score obtenu.

## 1. Sources et niveau de certitude

- Source principale : `dayone-participants.zip`, SHA-256 `c419cbdb901e43e25e7a68d9b0e885cbc31693aeead87e034efd93579d46a5f9`.
- Consignes officielles : `consignes-fr-en.pdf`, 8 pages ; français p. 1-4, anglais p. 5-8. Barème p. 4 et p. 7-8. Copie de lecture : `../../data/dayone/reference/consignes-fr-en.pdf`.
- Données : 129 images, PDF de 80 pages, CSV de 200 lignes, manifeste. Tous les 132 fichiers listés dans le manifeste concordent en taille et SHA-256.
- Diapositives fournies dans la conversation : contexte et contraintes, complétés ici par le PDF.
- Fiche locale HxBuddy : synthèse secondaire, mise à jour avec le barème du PDF. La consultation web de HxBuddy n'a pas permis de relire les onglets dynamiques. Les règles administratives de remise doivent être confirmées sur la page de l'équipe.
- Audit exécuté : `audit_dataset.py`, résultats dans `../../data/dayone/audit/`. Sources intactes ; sorties dérivées séparées. Aucun entraînement, extraction IA, appel payant ou envoi de données à un tiers effectué.

Les formulations « obligatoire » ci-dessous proviennent du PDF. Les choix d'architecture, métriques locales, objectifs de qualité et planning sont des recommandations, pas des règles ajoutées au défi.

## 2. Ce que le projet doit produire

Transformer les photographies d'un registre maternel multipage en dossier structuré, révisé par une sage-femme, avec continuité entre visites. Le registre papier reste la référence. L'interface doit être conversationnelle, de type WhatsApp, simulée ou réelle.

Le contrat de données porte sur une observation documentaire : quelle valeur est effectivement inscrite, à quel endroit, pour quelle visite, avec quel statut de lisibilité et quelle validation humaine. Une patiente, un épisode de grossesse, un registre, une page et une visite sont des objets différents.

Le produit doit capturer et stocker sans internet, attendre le traitement IA si nécessaire, permettre la saisie manuelle, puis synchroniser sans perte. Le PDF n'exige pas un modèle IA local fonctionnant hors ligne : il prévoit explicitement une file « En attente de traitement IA ».

Prédiction du risque maternel, triage vert/jaune/rouge, diagnostic, aide à la décision clinique et recommandations de traitement sont explicitement hors périmètre. Transcrire un traitement déjà inscrit est une extraction documentaire ; en recommander un nouveau dépasse le mandat.

## 3. État du projet local

Le dépôt contient un environnement Python, des compétences d'analyse, un notebook générique de classification/régression, les fiches des défis et des recherches sur les hackathons. Il contient aussi un dataset EquiAlgo dans `data/equialgo/`, distinct de DayOne.

Aucune application DayOne, pipeline d'extraction, interface conversationnelle, file persistante chiffrée ou fonction de liaison patiente n'a été trouvée dans l'inventaire. Le notebook générique n'est pas une baseline adaptée à ce défi : il ne faut pas choisir `preterm birth`, `gestational dm` ou `referral to higher care` comme cible à prédire.

Le `.gitignore` exclut déjà `data/**`, les CSV, ZIP et plusieurs formats de modèles. Pour la future application, exclure aussi secrets, bases locales, clés, images de capture, journaux contenant des valeurs de dossier et sauvegardes. Ne pas publier les références fournies sans vérifier les autorisations de partage.

## 4. Audit du dataset

### 4.1 Images et PDF

| Élément | Constat mesuré | Conséquence |
|---|---|---|
| Fichiers image | 129 | Le nombre de fichiers ne mesure pas le nombre d'exemples indépendants. |
| Images distinctes par SHA-256 | 85 | Construire l'inventaire dédupliqué avant toute séparation. |
| Groupes de copies exactes | 44 paires, donc 44 copies supplémentaires | Même image interdite dans développement et test sous deux noms différents. |
| PNG de spécimens | 124 fichiers, 80 distincts, 1654 × 2339, mode palette | Dix dossiers de huit pages ; forte dépendance entre pages. |
| JPG `1-1` à `1-5` | 5 photos distinctes, 900 × 1600, RGB | Cas de prise de vue et manuscrit utiles comme groupe séparé. |
| PDF de spécimens | 80 pages, dix patientes fictives | Les pages PDF et PNG correspondantes doivent rester dans le même groupe. |

Le PDF présente huit sections par patiente : couverture ; identification et antécédents ; grossesse actuelle ; accouchement ; postpartum précoce mère ; postpartum précoce nouveau-né ; postpartum tardif mère ; postpartum tardif nouveau-né. Une page de grossesse contient plusieurs colonnes de visites. L'extraction doit garder l'association ligne/colonne/visite.

L'inspection visuelle des exemples montre des formulaires roses, tableaux denses, cases à cocher, valeurs manuscrites sur les JPG et valeurs à apparence manuscrite sur les spécimens. Les cinq JPG semblent appartenir à un même livret : les grouper conservativement jusqu'à vérification. La couverture complète des langues arabe/anglais et des dégradations annoncées n'est pas démontrée par cet audit. Ne pas annoncer de performance multilingue sans cas annotés.

### 4.2 CSV synthétique

200 lignes × 31 colonnes ; 200 `id` distincts ; aucun doublon de ligne, même en retirant `id`. 148 cellules manquantes dans neuf colonnes ; 111 lignes, soit 55,5 %, ont au moins un manque.

| Champ | Manquants | Pourcentage |
|---|---:|---:|
| Glycémie à jeun initiale | 35 | 17,5 % |
| Hémoglobine | 23 | 11,5 % |
| Périmètre crânien | 23 | 11,5 % |
| Niveau d'instruction | 18 | 9 % |
| IMC avant grossesse | 16 | 8 % |
| Nombre d'avortements | 11 | 5,5 % |
| Résultat VIH | 10 | 5 % |
| Résultat syphilis | 7 | 3,5 % |
| Résultat hépatite C | 5 | 2,5 % |

Le CSV agrège profil, antécédents, mesures, analyses, grossesse et naissance. Il n'a pas de nom de fichier, numéro de page, date de visite, statut de champ, score de confiance ou clé d'épisode. Il ne permet donc pas à lui seul de reconstituer un dossier longitudinal ni de mesurer l'extraction image par image.

Le premier spécimen du PDF indique un âge de 31 ans ; la ligne CSV `id=1` indique 24 ans. La correspondance par ordre ou identifiant numérique n'est donc pas une référence valide démontrée. Le PDF annonce des références par page, mais l'archive ne fournit pas une table explicite `image → champ → valeur → statut`. Obtenir cette correspondance des organisateurs ou créer des annotations manuelles contrôlées avant de publier un score d'extraction.

Les catégories sont déséquilibrées : VIH positif 3/190 résultats renseignés ; syphilis positive 9/193 ; hépatite C positive 2/195. Une réponse « négatif » systématique aurait une exactitude artificiellement élevée. Les cas positifs, négatifs, absents et illisibles doivent être évalués séparément.

37 poids de naissance valent exactement 4800 g et 91 périmètres crâniens valent exactement 40 cm. Ces concentrations aux maxima sont compatibles avec un plafonnement synthétique, sans preuve du générateur. 123 lignes ont parité égale à gestité ; la définition temporelle des comptes doit être documentée avant d'appliquer une règle métier. Aucune ligne ne dépasse la parité pour les enfants vivants ou la gestité pour parité + avortements renseignés. Ces contrôles descriptifs ne valident pas la cohérence médicale.

### 4.3 Pièges de sens

- Le registre contient `Ag HBs`, tandis que les consignes et CSV mentionnent l'hépatite C. Préserver deux champs distincts. Aucun remplacement silencieux.
- Les formulaires contiennent noms, CIN, téléphone, adresse et nom du conjoint, même sur les spécimens. Exclure ces zones et champs du produit.
- `id` du CSV et « Patiente fictive n°x/10 » sont des repères d'audit, jamais des mécanismes de liaison pour la démo ou le produit.
- Une case non cochée ne suffit pas toujours à conclure « non ». Définir les règles de chaque groupe de cases ; sans réponse explicite, préserver le manque.
- Une valeur CSV vide ne permet pas de décider si l'image était vide, illisible, inconnue ou non applicable.
- Moyenne de tension du CSV et mesure d'une visite ne sont pas le même champ.
- Une semaine gestationnelle décimale du CSV ne doit pas être interprétée comme « semaines.jours » : 16,3 semaines n'est pas automatiquement 16 SA + 3 jours.
- Préserver unités et brut : g/dL contre g/L ; mg/dL contre g/L ; poids maternel en kg contre poids de naissance en g ; tension possiblement notée selon des conventions différentes.
- Ne pas remplir une valeur absente par moyenne, valeur plausible, visite précédente ou résultat d'un autre test. Les contrôles de cohérence signalent une question, ils ne corrigent pas le document.

## 5. Règles et manière de les respecter

| Exigence officielle | Réalisation proposée | Preuve à préparer |
|---|---|---|
| Papier référence et zéro changement du flux | Capture après l'écriture habituelle ; questions ciblées, pas de ressaisie systématique. | Démo partant du registre, actions nécessaires comptées. |
| Schéma fondé sur les sections | Dictionnaire des champs, types, unités, répétitions et statuts. | Schéma versionné et exemples de chaque section. |
| Six statuts explicites | `CONNU`, `INCONNU`, `NON_FOURNI`, `ILLISIBLE`, `NON_APPLICABLE`, `À_RÉVISER`. | Cas annotés et sorties vérifiées. |
| Confiance par champ | Confiance documentée et confrontée aux erreurs ; séparée de la validation humaine. | Rapport fiabilité/confiance et exemples de doute. |
| Confirmer, corriger, reprendre | Actions réelles avec sauvegarde et provenance de correction. | Une correction visible dans le dossier et le journal. |
| Saisie manuelle complète si IA indisponible | Formulaire guidé couvrant tous les champs, sans requête réseau nécessaire. | Capture et dossier saisi IA désactivée. |
| Capture et stockage sans internet | Persistance chiffrée, file durable, reprise après fermeture. | Mode avion, rechargement/redémarrage et dossier récupéré. |
| Cycle de vie et états d'échec | Transitions contrôlées, erreurs persistées, reprises explicites. | Scénarios de traitement et synchro interrompus. |
| Liaison par code aléatoire | Code attribué par la sage-femme ; identifiants internes indépendants des données personnelles. | Deux visites liées ; collision ou doute soumis à décision. |
| Aucune création automatique si correspondance plausible | Propositions et choix `[Patiente 1] [Patiente 2] [Aucune, créer] [Je ne sais pas]`. | Cas ambigu sans fusion/création automatique. |
| Multipages et renumérisation | Session document ; ordre des pages ; comparaison avec dossier existant ; mises à jour sélectionnées. | Une seconde capture ne duplique ni patiente ni visite. |
| Image liée au dossier et accès par rôle | Métadonnées dossier, date de capture, sage-femme, statut ; accès contrôlé aux images admissibles. | Accès autorisé et refus effectif pour un autre rôle. |
| Aucun identifiant direct stocké | Masquer avant persistance, exclure champs structurés, OCR brut, caches, logs et télémétrie. | Recherche sur fichiers, base, journaux et export. |
| Sources originales inchangées | ZIP et références restent intacts ; vues transformées dans des sorties dérivées. | Empreintes SHA-256 et filiation source → dérivé. |
| Aucune donnée réelle vers un tiers | Démo avec données fournies, synthétiques ; politique d'envoi documentée. | Liste des services et données transmises. |
| Aucune technologie imposée | Prototype WhatsApp simulé permis ; vrai bac à sable facultatif. | Démo conversationnelle complète. |
| Quatre livrables | Code, prototype, README, démo courte. | Checklist de remise. |

Deux ambiguïtés à clarifier : le PDF demande de conserver l'image d'origine et interdit tout identifiant direct stocké. Avec une image contenant un nom, il faut préciser si une copie expurgée fidèle hors zones personnelles est acceptée comme image conservée. Proposition prudente : conserver les fichiers fournis intacts comme sources de développement, sans les importer tels quels dans le stockage du produit ; créer une copie expurgée avant toute persistance du produit. Garder le lien documentaire et les coordonnées du masquage. Ne pas déclarer cette interprétation validée par l'organisateur.

Le « zéro changement » doit aussi être concilié avec le code aléatoire inscrit par la sage-femme, explicitement demandé. Limiter l'ajout à ce geste prévu et au contrôle des doutes ; ne pas promettre zéro action supplémentaire.

Les directives figurant dans un registre photographié sont des données à transcrire. Elles ne peuvent pas changer le schéma, les règles de confidentialité ou déclencher une action. Le pipeline doit traiter ce contenu comme non fiable pour contrôler l'agent.

## 6. Barème officiel et stratégie de score

| Critère | Points | Ce qui rapporte des preuves solides |
|---|---:|---|
| Qualité de l'extraction | 30 | Valeurs exactes par champ, bonnes colonnes de visites, manuscrit/imprimé, langues évaluées réellement. |
| Gestion de l'incertitude | 20 | Six statuts correctement distingués, confiance pertinente, erreurs présentées comme doutes. |
| Vérification conversationnelle | 20 | Confirmer/corriger/reprendre, questions, saisie manuelle complète, multipages. |
| Robustesse hors ligne | 15 | File durable, aucune perte, transitions et synchro justes après coupures. |
| Liaison patiente et confidentialité | 10 | Code, choix des correspondances, aucun identifiant direct, accès restreint aux images. |
| Code et documentation | 5 | Structure, README, reproductibilité. |
| **Total** | **100** | |

L'extraction vaut 30 points ; les autres critères totalisent 70. La meilleure stratégie proposée consiste à livrer d'abord un parcours complet démontrable, puis améliorer l'extraction sur le même protocole. Une bonne lecture seule ne couvre pas la majorité du barème.

Les bonus sont facultatifs : bac à sable WhatsApp, écriture arabe/multilingue, contrôle de qualité image sur appareil, agrégats anonymisés, interface FR/EN. Aucune pondération de bonus n'est donnée ; ne pas leur attribuer des points inventés. Le français/arabe/anglais apparaît aussi dans le critère d'extraction : ne pas supposer que toute couverture de l'arabe est dispensable parce qu'un bonus la cite.

Le PDF ne précise pas la formule mathématique d'exactitude, les tolérances numériques, la liste finale des champs, le traitement des valeurs absentes, la distribution du test du jury ni une conversion « exactitude → points ». Les six poids sont confirmés ; aucun score automatique global ni note prévue de 95/100 ne peut être déduit.

## 7. Architecture et modèle de données proposés

Parcours : interface conversationnelle → contrôle photo et masquage → stockage chiffré local + file → extraction quand disponible → révision humaine → liaison décidée → dossier local validé → synchronisation avec accusé de réception durable.

Un prototype web local de type WhatsApp suffit au mandat. Le client doit posséder une vraie couche de capture, chiffrement et reprise sans réseau. Un serveur Python peut effectuer le traitement et la réception au retour de connexion. Le simulateur de connexion pilote des pannes reproductibles ; une coupure réelle vérifie que le client ne dépend pas d'une réponse du serveur. Choisir les bibliothèques selon les compétences de l'équipe et vérifier leurs licences ; aucune marque de modèle n'est exigée.

Entités recommandées : `PatientProfile`, `PregnancyEpisode`, `RegistryDocument`, `PageCapture`, `Visit`, `FieldObservation`, `ReviewEvent`, `SyncOperation`. Une patiente peut avoir plusieurs grossesses, chacune plusieurs visites et documents.

Chaque observation conserve : chemin du champ ; valeur brute non identifiante ; valeur normalisée ; unité ; statut documentaire ; confiance IA ; page et zone de preuve ; visite concernée ; auteur/origine ; décision de révision ; version du schéma et de l'extracteur. La confirmation humaine est un état séparé du statut documentaire. Une valeur confirmée inconnue reste `INCONNU` ; la confirmation ne transforme pas artificiellement la confiance IA en 100 %.

Définition de travail à vérifier sur annotations :

| Statut | Interprétation proposée |
|---|---|
| CONNU | Valeur explicitement lisible et attribuable au bon champ. |
| INCONNU | Le document ou la sage-femme indique explicitement ne pas connaître la valeur. |
| NON_FOURNI | Champ présent sans donnée ; page attendue non reçue distinguée par un motif séparé. |
| ILLISIBLE | Une inscription existe, mais ne peut pas être transcrite fidèlement. |
| NON_APPLICABLE | Inapplicabilité explicitement établie par document ou confirmation humaine. |
| À_RÉVISER | Lecture candidate ambiguë, attribution incertaine ou incohérence à faire vérifier. |

Machine à états proposée : `CAPTURÉ → EN_ATTENTE_IA → TRAITÉ_IA → À_RÉVISER → VALIDÉ → PATIENTE_LIÉE → ENREGISTRÉ → SYNCHRONISÉ`. Prévoir branches d'échec traitement, échec synchro, doublon suspecté et révision manuelle requise. La saisie manuelle permet d'atteindre la validation sans IA ; une correction d'un dossier synchronisé crée une nouvelle version en attente de synchro.

La file utilise une clé d'opération stable et une réception idempotente : rejouer un envoi crée le même enregistrement, pas un second. Ne supprimer de la file qu'après accusé de réception durable. Après un accusé perdu, vérifier l'opération avant de renvoyer/créer. Une image identique n'est pas forcément une nouvelle visite ; une image différente n'est pas forcément un nouveau document.

Chiffrement authentifié au repos pour images, données et file ; chiffrement en transit ; clés séparées des données et du dépôt ; déverrouillage explicite. Des chaînes encodées en Base64 ne sont pas du chiffrement. Un token de rôle dans l'interface ne suffit pas : l'accès serveur aux images doit appliquer le rôle. Définir sauvegarde, récupération et limites du prototype.

## 8. Pipeline d'extraction proposé

1. Détecter la page et sa section ; rejeter ou signaler capture tronquée, floue ou trop sombre.
2. Masquer les zones identifiantes avant stockage du produit et avant appel IA ; si la zone est incertaine, demander une reprise ou une confirmation du masquage.
3. Produire une vue dérivée redressée, sans écraser la source ; garder transformations et coordonnées.
4. Extraire selon le schéma : tableaux par ligne et colonne, visites répétées, cases et texte libre. Une page dense peut être découpée en sections avec rattachement explicite.
5. Imposer une sortie structurée et des champs autorisés ; aucune valeur inventée ; `null` avec statut et motif lorsque nécessaire.
6. Normaliser dates, unités et catégories tout en gardant le brut non identifiant. Ne pas convertir HBs en HCV ou une moyenne en visite.
7. Déterminer l'incertitude à partir des preuves, du manque, de la qualité et des ambiguïtés. Une confiance déclarée par un modèle n'est pas automatiquement une probabilité calibrée.
8. Poser une question ciblée avec extrait expurgé : confirmer, corriger, reprendre ou indiquer inconnu/non fourni/non applicable.
9. Valider, rattacher au dossier sur décision humaine et synchroniser la version.

Comparer une baseline transparente (lecture structurée simple par section) à une amélioration (meilleur découpage ou contrôles de mise en page), sur les mêmes documents et annotations. Choisir le modèle sur exactitude, comportement sur manques, latence, coût et compatibilité de licence. Le volume indépendant est faible : commencer avec un modèle préentraîné évalué localement ; un entraînement lourd n'est pas justifié par ce seul corpus.

## 9. Protocole local d'évaluation

### Références et séparation

Établir `page → patiente/épisode → section → visite → champ → brut → normalisé → statut → zone de preuve`. Demander le mapping officiel ; à défaut, faire une transcription manuelle et une deuxième vérification indépendante. Utiliser le texte PDF comme aide d'annotation uniquement, sans le fournir au pipeline évalué sur photos. Les noms et numéros de fichier ne doivent pas servir à récupérer des réponses déjà connues.

Dédupliquer par hash ; grouper PDF, PNG, copies, variantes et augmentations du même dossier. Une proposition reproductible sur dix dossiers : six dossiers développement, deux validation pour les seuils/questions, deux test final. Tirage groupé fixé avant optimisation. Les cinq photos d'un autre livret forment un groupe de robustesse distinct, évalué sur les seuls champs annotables. Avec dix dossiers, annoncer les effectifs et éviter les conclusions de généralisation forte.

L'audit global des données a été effectué ; aucun modèle n'a été ajusté. Après fixation des groupes, ne plus inspecter les réponses du test final pour corriger prompts ou seuils. Les images synthétiquement floutées/inclinées restent dans le groupe de leur source et sont marquées « dégradation simulée ».

### Mesures proposées, distinctes de la notation officielle

- Exactitude des valeurs sur champs de référence renseignés, avec normalisation autorisée prédéfinie ; mauvais/absent/abstention sur un champ connu comptés comme échec dans cette mesure globale.
- Résultats sur champs réellement absents, inconnus, illisibles et non applicables séparés ; matrice de confusion et macro-F1 des six statuts.
- Exactitude macro par type de champ et par dossier, plus nombre de champs au dénominateur ; ne pas laisser des milliers de cases vides dominer la moyenne.
- Précision des valeurs proposées en `CONNU` et couverture de ces propositions ; courbe montrant leur compromis. Refuser toute lecture n'obtient pas une bonne couverture.
- Taux d'erreurs proposées avec confiance élevée ; fiabilité par tranches de confiance. Si une calibration est apprise, utiliser validation séparée et signaler les petits effectifs.
- Exactitude avant révision et après révision séparées ; temps de révision, nombre de corrections et de questions. Une correction humaine n'est pas un succès initial de l'IA.
- Résultats par section, source photo/spécimen, manuscrit/imprimé, langue réellement présente, qualité d'image, valeurs positives/négatives et statuts.
- Contrôles fonctionnels : captures retrouvées après redémarrage, absence de double création à la reprise, décisions de liaison explicites, refus d'accès, absence de fuite d'identifiants.

Pour les nombres, définir à l'avance les normalisations et tolérances permises. Donner aussi le résultat strict : une tolérance large ne doit pas rendre invisible une erreur de lecture. Aucune tolérance locale ne doit être présentée comme celle du jury.

Rapport des expériences : versions données/schéma/modèle/prompt ; groupes ; paramètres ; coût/latence ; métriques ; erreurs représentatives ; décisions. Ne publier de résultat que lorsqu'il a été réellement mesuré.

## 10. Plan de travail et critères de passage

Planning recommandé pour 24 heures de travail disponibles, à adapter à la durée réelle du hackathon. Aucun horaire officiel de remise n'a été vérifié.

| Phase | Budget indicatif | Travail | Passage à la suite |
|---|---:|---|---|
| A. Cadrage | 1 h | Fixer schéma, statuts, règles, questions au partenaire et partage des tâches. | Mandat et barème traduits en checklist. |
| B. Données et références | 2 h | Dédupliquer, grouper, annoter les champs, fixer développement/validation/test. | Références fiables et protocole écrit. |
| C. Parcours complet | 4 h | Chat simulé, capture, masquage, stockage chiffré, file, révision, liaison, réception. | Un dossier parcourt toute la chaîne ; IA temporaire clairement signalée si utilisée pendant le développement. |
| D. Extraction réelle | 5 h | Première lecture structurée, tableaux/visites, statuts, normalisation, preuve. | Baseline mesurée et erreurs enregistrées. |
| E. Robustesse fonctionnelle | 4 h | Coupures, redémarrage, reprise, échec IA, saisie manuelle complète, ambiguïtés et renumérisation. | Aucun échec silencieux sur scénarios prioritaires. |
| F. Amélioration mesurée | 3 h | Corriger les types d'erreurs dominants sur validation ; ajuster questions/seuils. | Gain démontré sans perte excessive de couverture. |
| G. Évaluation et remise | 3 h | Geler, évaluer test, README, commandes, screenshots expurgés, démo et dossier de soumission. | Un tiers peut lancer et examiner les preuves. |
| Réserve | 2 h | Intégration et incidents. | Priorité à la stabilité. |

Si le temps manque : couvrir les six catégories avec un parcours opérationnel et déclarer les sections d'extraction moins robustes. La saisie manuelle doit rester complète. Conserver toutes les sections dans le schéma et signaler toute couverture IA partielle. Réduire les bonus, l'intégration WhatsApp réelle et l'entraînement personnalisé avant de réduire le hors ligne ou la confidentialité.

Pour plusieurs membres : répartir travail données/extraction, interface/révision, persistance/synchro/liaison, intégration/évaluation/remise selon l'effectif réel. Fixer tôt le contrat JSON pour intégrer les parties. Ne multiplier les services que si leur utilité est démontrée.

## 11. Scénarios d'acceptation prioritaires

1. Capturer plusieurs pages sans réseau ; fermer/recharger ; les retrouver chiffrées avec file intacte.
2. Restaurer la connexion ; recevoir un traitement réel ; afficher statuts et preuves ; corriger un champ incertain.
3. Couper au milieu du traitement ; revenir ; reprise explicite sans perte ni faux statut de réussite.
4. Couper après réception serveur mais avant accusé client ; rejouer ; une seule opération enregistrée.
5. IA indisponible ; saisir et valider un dossier complet manuellement.
6. Nouvelle visite avec code connu ; vérifier historique et rattachement, sans fusion des grossesses.
7. Deux correspondances possibles ; choisir ou répondre « Je ne sais pas » ; aucune création/fusion silencieuse.
8. Rephotographier un registre ; présenter l'existant et les changements ; sélectionner les champs à mettre à jour, versionner.
9. Photo illisible, champ vide, inconnu explicite, case conditionnelle non applicable ; états distincts et pas de complétion inventée.
10. Photo contenant des identifiants ; ils n'apparaissent ni en données, images stockées, journaux, exports ou requêtes externes.
11. Rôle sans permission image ; refus effectif même via l'URL de l'image.
12. Valeur HBs, résultat positif rare, plusieurs dates/colonnes ; garder l'attribution exacte et demander confirmation si doute.

Ces scénarios sont à exécuter pendant l'implémentation ; ils n'ont pas été exécutés sur une application inexistante.

## 12. Démonstration et remise

Scénario recommandé d'environ trois minutes, durée proposée et non limite officielle : registre → deux pages capturées sans connexion → fermeture/reprise → connexion restaurée → traitement réel → doute illustré par sa preuve → correction sauvegardée → décision entre correspondances → historique et confirmation de synchro. Montrer brièvement la renumérisation et le mode manuel, ou les garder prêts pour les questions du jury.

Les résultats mis en cache pour une répétition doivent être identifiés comme tels. Préparer une vidéo de secours mais garder un chemin d'extraction réel et des chiffres reproductibles. Ne pas annoncer une amélioration de mortalité ou une efficacité clinique à partir de ce prototype.

Checklist : code des quatre modules attendus ; prototype conversationnel ; README installation et commandes ; schéma et statuts ; cycle de vie ; provenance des références ; protocole et résultats mesurés ; limites ; dépendances et versions ; modèles/outils/sources et licences ; configuration d'exemple sans secret ; démo courte ; distinction travail antérieur/nouveau ; accès du jury conforme à la plateforme.

La fiche locale rapporte une soumission Devpost, un projet/un prix pour ce défi et maintien des membres HxBuddy. Ces indications administratives sont secondaires et à confirmer sur HxBuddy/Devpost. Ne pas reprendre les règles trouvées pour un autre hackathon.

## 13. Questions précises à poser aux organisateurs

1. Où est la correspondance image/page/champ avec valeurs de référence ? Le CSV de 200 lignes est-il indépendant des dix spécimens ?
2. Quel schéma et quelles normalisations/tolérances le jury utilisera-t-il ? Comment note-t-il l'abstention et les statuts ?
3. Quel jeu de test est prévu, quelles langues et quelles formes de dégradation ? Les cas sont-ils inconnus des équipes ?
4. Une copie expurgée avant stockage satisfait-elle la conservation de l'image d'origine lorsque des identifiants y figurent ?
5. Comment concilier inscription du code aléatoire et zéro changement de pratique ? Quel format de code est attendu ?
6. Quels fichiers fournis peuvent être partagés avec le jury, publiés ou envoyés à une API sur données synthétiques ?
7. Quelles règles d'équipe, date/heure de remise, durée de démo, accès au dépôt et déclaration des ressources préexistantes s'appliquent à cette édition ?

L'absence de ces réponses n'empêche pas de développer le schéma, le parcours, le hors ligne, la révision et l'évaluation locale annotée. Elle limite la précision des affirmations de conformité et de score final.

## 14. Registre de conclusions

| Conclusion | État | Preuve / limite |
|---|---|---|
| Barème sur 100 et poids 30/20/20/15/10/5 | Confirmé | Consignes, p. 4 et p. 7-8, extraction et inspection visuelle. |
| 129 images mais 85 distinctes | Confirmé | SHA-256 calculés sur tous les fichiers image. |
| CSV 200 × 31, 148 manques, 111 lignes touchées | Confirmé | Audit pandas exécuté. |
| Mapping CSV → images non démontré | Confirmé pour l'archive inspectée | Absence de clé explicite ; âge différent pour premier repère. |
| Corpus représentatif du terrain et des trois langues | Non démontré | Corpus synthétique petit ; couverture complète non annotée. |
| Plan proposé maximisera réellement la note | Conditionnel | Alignement avec barème, sans résultat du jury ni performance implémentée. |
| Conformité finale des images expurgées | À confirmer | Ambiguïté conservation/confidentialité. |
| Précision du modèle, pertes à la synchro, qualité du produit | Non évalué | Aucun prototype DayOne implémenté. |

Reproduction : audit des images/CSV exécuté localement, script fourni. Lecture PDF effectuée avec le runtime documentaire de Codex. Refaire l'audit depuis la racine :

```powershell
.\.venv\Scripts\python.exe HxBuddy-Challenges/07-dayone-offline-midwife/audit_dataset.py
```

Sorties : `data/dayone/audit/audit_dataset.json`, `inventaire_images.csv`, `profil_champs.csv`. Les champs détaillés, dimensions et groupes de doublons sont consultables sans entraîner un modèle.
