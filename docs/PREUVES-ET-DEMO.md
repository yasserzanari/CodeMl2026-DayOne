# Vérification locale, écarts et démonstration

Date : 3 octobre 2026. Périmètre : prototype sur Windows, Python 3.11.8,
données entièrement fictives. Ce rapport complète l'analyse initiale, qui décrit
l'état antérieur à l'application. Il ne constitue ni certification de sécurité,
ni mesure de précision manuscrite, ni note prédite du jury.

## Écarts corrigés

- Une lettre accentuée dans le mot de passe provoquait une erreur serveur :
  échec reproduit par test, comparaison désormais sur octets UTF-8.
- Le résultat OCR et l'accusé `DONE` pouvaient être enregistrés séparément :
  ils partagent maintenant une transaction. Un déclencheur SQLite de test force
  l'échec de l'accusé ; les suggestions et le journal sont alors annulés ensemble.
- Prise de travail et insertion de clé d'idempotence sérialisées avec
  `BEGIN IMMEDIATE`. Le scénario rejoue une demande après perte de réponse.
- Les erreurs de validation Pydantic pouvaient inclure l'entrée rejetée :
  réponse 422 générique, sans contenu soumis. Réponses marquées `no-store`.
- Un bouton d'action restait désactivé quand la vue n'était pas recréée :
  réactivation dans `finally`.
- L'aperçu du masque sur une page verticale pouvait subir un redimensionnement
  discordant : hauteur automatique du canevas. Import vertical vérifié dans le navigateur.

## Preuves et portée

| Fait | Preuve reproductible | Limite |
|---|---|---|
| Import multipage, dédoublonnage et masquage | Tests HTTP ; comparaison des pixels expurgés ; deux pages dans la WebUI | Masquage manuel, aucune garantie que l'opérateur a masqué tous les identifiants |
| Correction protégée | Test de résultat OCR tardif après correction humaine et test de redémarrage | Conflit de version relancé ; pas de fusion automatique |
| Panne réelle et reprise | `test_process_restart.py` tue le processus au point d'arrêt OCR, redémarre, reprend la file et rejoue la même clé | Vérifie une panne avant inférence et un échec transactionnel séparément, pas toutes les instructions machine |
| Persistance | Deux redémarrages, pages, correction et deux visites retrouvées | Une seule machine et une seule instance serveur |
| OCR sans sortie réseau Python | Serveur de test bloque les connexions/DNS non loopback ; compteur cumulé nul ; vraies inférences EasyOCR | Pas de pare-feu système ; pas d'observation exhaustive des bibliothèques natives ou du navigateur |
| Confidentialité des réponses et logs | Entrée rejetée non renvoyée ; sentinelle absente de SQLite en clair ; logs du scénario sans texte/image soumis ; rapport du bot limité aux compteurs | Contrôles ciblés, pas une preuve universelle d'absence de fuite |
| Authentification et rôles | Refus sans session, session forgée, mutation sans CSRF, configuration réservée admin, image refusée après déconnexion | Deux rôles partagés, aucune identité individuelle ni restriction par centre |
| Chiffrement authentifié | Valeurs chiffrées différemment à chaque écriture ; altération et mauvaise clé rejetées ; images chiffrées | Métadonnées, codes, statuts et horodatages restent en clair |

Les tests HTTP/processus sont automatisés. La vérification navigateur est un
parcours manuel outillé ; elle n'est pas présentée comme une suite navigateur
automatisée. Le scénario HTTP couvre la panne/reprise ; le parcours navigateur
couvre import vertical, masquage, OCR, correction et création de visite.

## Reproductibilité

Code de référence vérifié : commit `7f3e14d`, branche `codex/dayone-local-console`.
Un clone local neuf de ce commit a été créé sous `.verification/clean-checkout`.
Un nouvel environnement `.verification/clean-venv` a été installé sans paquets
système (`include-system-site-packages=false`). L'installation initiale depuis
`requirements-dev.txt` a réussi ; ses versions exactes figurent dans
`requirements-verified-windows.txt`, également réinstallé depuis le clone.
Les deux poids existants ont été copiés localement dans le clone avant les tests.
Aucun registre du défi ni base applicative n'a été copié.

Résultat sur ce clone : **12 tests réussis, 10 avertissements, 29,64 secondes**.
Commandes réellement utilisées depuis le dépôt de travail :

```powershell
git clone --local --branch codex/dayone-local-console --single-branch . .verification/clean-checkout
.verification/clean-venv/Scripts/python.exe -m pip install -r .verification/clean-checkout/requirements-verified-windows.txt
.verification/clean-venv/Scripts/python.exe -m pytest .verification/clean-checkout/admin/tests -q
git -C .verification/clean-checkout status --short
```

Le dernier état Git du clone était vide ; les poids copiés sont ignorés.
Le garde réseau du parcours navigateur a également compté zéro tentative
externe. La preuve visuelle locale est `.verification/dashboard-proof.jpg` ;
elle n'est pas versionnée.

Pour reproduire depuis un clone autorisé de la branche :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-verified-windows.txt
.\.venv\Scripts\python.exe admin/setup_models.py
$env:DAYONE_ADMIN_PASSWORD = "une-phrase-locale-longue-a-conserver"
.\.venv\Scripts\python.exe admin/run.py
```

Installation des dépendances et préparation des poids nécessitent Internet si
les fichiers ne sont pas déjà disponibles. L'inférence utilise exclusivement
`download_enabled=False`. Les poids requis pour `fr,en` sont :

| Fichier dans `admin/.models/` | Taille observée |
|---|---:|
| `craft_mlt_25k.pth` | 83 152 330 octets |
| `latin_g2.pth` | 15 406 141 octets |

Ils sont ignorés par Git. Les tailles aident au diagnostic, sans remplacer une
vérification d'intégrité. Le fichier de versions fixe les paquets de l'environnement
Windows observé ; il ne verrouille pas les hachages des distributions et ne prouve
pas la compatibilité d'un autre OS.

```powershell
.\.venv\Scripts\python.exe -m pytest admin/tests -q
```

Cette commande inclut le scénario à processus réel et l'OCR réel, avec poids
présents. Les bases et documents du test sont temporaires et synthétiques.
Le garde réseau est installé avant le chargement du serveur dans ce scénario.
Les avertissements des dépendances (quantification Torch, mémoire épinglée CPU,
API de test Starlette et lecture des pixels Pillow) ne sont pas des échecs.

## Authentification, clé et récupération

- La clé Fernet est dérivée du mot de passe admin par PBKDF2-HMAC-SHA256,
  600 000 itérations, sel aléatoire de 16 octets. Elle reste en mémoire ; elle
  n'est pas enregistrée dans le dépôt ou un fichier de clé.
- Le mot de passe arrive par variable d'environnement. Un utilisateur local
  capable d'inspecter le processus peut accéder à ses secrets et à sa mémoire.
- Le sel est conservé dans `DAYONE_RUNTIME_DIR/salt.bin`, à côté de la base.
  Le sel n'est pas secret. `chmod(0600)` ne prouve pas une ACL Windows restrictive.
- Une récupération demande **base + sel + même mot de passe**, depuis une
  sauvegarde cohérente réalisée serveur arrêté. Aucun mécanisme de récupération
  du mot de passe n'existe. Aucune rotation de clé avec migration n'est implémentée.
  Modifier le mot de passe de démarrage d'une base existante rend son contenu
  illisible ; le serveur le détecte et refuse le démarrage.
- La session signée expire au bout de huit heures et devient invalide après
  redémarrage (secret aléatoire en mémoire). Cookie HttpOnly/SameSite Strict ;
  HTTP loopback, sans TLS, donc pas un service à exposer au LAN ou à Internet.
- La déconnexion supprime le cookie du navigateur. Pas de révocation serveur
  individuelle d'un cookie volé avant son expiration ; pas de limitation des
  tentatives de connexion ni MFA. Ces lacunes restent à traiter avant un autre
  contexte d'utilisation.
- Les deux rôles peuvent lire les dossiers et images ; seuls les administrateurs
  changent la configuration et reprennent la file globale. Le journal n'identifie
  pas un professionnel individuellement et n'est pas inviolable.
- Images, valeurs et messages sont chiffrés ; métadonnées SQLite, états, codes,
  comptes et dates ne le sont pas. Le prototype ne chiffre pas le disque entier.
- Les messages libres peuvent contenir des identifiants malgré l'avertissement.
  Le chiffrement n'équivaut pas à leur suppression : la règle « aucun identifiant
  direct stocké » ne peut donc pas être garantie pour une saisie arbitraire.
  Continuer exclusivement avec des documents et messages fictifs contrôlés.

## Trois questions officielles encore ouvertes

Relecture de `consignes-fr-en.pdf` fourni, pages françaises 2–4 et anglaises 6–8 :

1. **Original/expurgation** : p. 2 interdit le stockage d'identifiants directs et
   la modification des sources ; p. 3 demande l'image d'origine liée au dossier.
   Garder les sources de référence intactes hors application et ne stocker dans
   l'application qu'une copie expurgée. Faire confirmer que cela satisfait
   l'exigence d'image d'origine. Aucune réponse officielle obtenue.
2. **Vérité terrain** : p. 2 annonce des valeurs de référence par page. L'archive
   auditée n'a pas de mapping explicite cellule/page/visite vers le CSV ; l'ordre
   des lignes n'a pas été validé. Obtenir le mapping ou annoter un sous-ensemble
   avec double relecture avant de calculer une précision manuscrite.
3. **Examens** : les consignes mentionnent hépatite C et des registres contiennent
   Ag HBs. Garder deux champs, sans conversion ni remplacement silencieux ;
   demander la cible attendue pour la notation.

Les consignes n'imposent aucune technologie et interdisent l'envoi de données
réelles à un tiers. La demande utilisateur impose en plus le traitement local.
WhatsApp réel reste désactivé ; un éventuel sandbox ne peut utiliser que du fictif.

## Démonstration de cinq minutes

Préparer les poids avant la session. Lancer avec un runtime de démonstration
isolé et un mot de passe fictif (ne jamais employer une base réelle) :

```powershell
$env:DAYONE_ADMIN_PASSWORD = "synthetic-ui-verification-2026"
.\.venv\Scripts\python.exe admin/tests/demo_server.py --port 8876
```

Ouvrir `http://127.0.0.1:8876`. Les deux images générées sont dans
`.verification/ui-demo/synthetic-page-1.png` et `synthetic-page-2.png`.

| Temps | Geste et résultat attendu |
|---|---|
| 0:00–0:40 | Connexion, dashboard ; montrer « aucun service tiers connecté » et les dossiers fictifs |
| 0:40–1:40 | Bot local, nouvelle conversation, relecture ; importer les deux pages, masquer le bandeau fictif, cocher la confirmation et enregistrer chacune |
| 1:40–2:30 | Lancer OCR ; montrer les quatre suggestions, la page de provenance et la confiance explicitement non calibrée |
| 2:30–3:20 | Corriger l'âge à 29, statut CONNU, enregistrer ; distinguer valeur absente et illisible ; montrer qu'un dossier incomplet ne se valide pas |
| 3:20–4:10 | Créer une visite liée ; montrer deux dossiers sous le même code, puis la recherche par code et confirmation humaine pour une liaison existante |
| 4:10–5:00 | Montrer la preuve automatisée de panne/reprise, le rapport local agrégé et les limites manuscrit/synchronisation ; revenir au dashboard |

Pour une démonstration de panne en direct, démarrer avec `--hold-ocr`, lancer
l'OCR puis arrêter uniquement ce serveur après apparition de `ocr-started` dans
le runtime. Redémarrer sans ce drapeau avec le même mot de passe, se reconnecter
et reprendre la file dans Configuration. Utiliser un nouveau runtime isolé
pour chaque répétition ; ne pas effacer une base contenant du travail à conserver.

## Checklist par critère du jury

| Critère | Poids | État démontré | Travail restant prioritaire |
|---|---:|---|---|
| Extraction | 30 | OCR local, neuf champs possibles, provenance par page ; benchmark antérieur 48/48 sur 48 champs de cartes imprimées artificielles | Schéma complet périnatal, colonnes/visites, annotations fiables, manuscrit et langues FR/AR/EN ; aucune note déduite du 48/48 |
| Incertitude | 20 | Six statuts, validation humaine séparée, confiance marquée brute/non calibrée | Mesurer calibration et erreurs sur données annotées ; conserver une zone de preuve par cellule |
| Conversation | 20 | Proposer/confirmer/corriger, saisie manuelle des neuf champs, multipages | Couverture de toutes les sections, questions ciblées, parcours complet de reprise photo |
| Hors ligne | 15 | Capture et OCR sur machine locale, file durable, interruption/reprise idempotente | Capture téléphone autonome quand le serveur est inaccessible, synchronisation entre appareils et cycle de vie complet |
| Liaison/confidentialité | 10 | Code exact, décision humaine, chiffrement des contenus, accès authentifié | Correspondances ambiguës, attribution du code terrain, politique d'image officielle, gestion des identifiants libres et des clés |
| Code/documentation | 5 | Versions figées, tests et scénario reproductible | Tests sur autres machines, architecture moins monolithique, exploitation et sauvegarde/rotation |

Les poids sont officiels ; les états sont une autoévaluation de couverture,
pas un score accordé. Le prochain blocage pour une mesure d'extraction défendable
est la vérité terrain par page/cellule/visite. La couverture du schéma et le
fonctionnement autonome sur téléphone restent des travaux techniques possibles
sans attendre cette réponse.
