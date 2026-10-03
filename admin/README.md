# DayOne Console — prototype local

Interface admin pour consulter des données synthétiques, relire des champs, lancer un OCR **local** et essayer un bot de type WhatsApp simulé. Aucun message, image ou champ n'est envoyé à Meta ou à une API de modèle. Le serveur n'écoute que `127.0.0.1`. Ce prototype n'est pas prêt pour des données réelles de patientes.

**Mode A — local, actif par défaut :** navigateur et serveur sur la même machine, plusieurs pages expurgées par dossier, OCR EasyOCR local, suggestions par champ, validation humaine, visites liées par code exact, file OCR SQLite persistante et reprise manuelle. Les valeurs et messages sont chiffrés au repos. L'absence d'Internet n'interrompt pas ce parcours après installation.

**Mode B — WhatsApp Business sandbox :** prérequis externes non fournis et adaptateur non activé. Le [guide de sandbox](META-SANDBOX.md) décrit la frontière à respecter. Le bouton Bot local ne prétend pas être connecté à Meta.

## Démarrage Windows

Depuis le dossier racine du dépôt :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r admin/requirements.txt
$env:DAYONE_ADMIN_PASSWORD = "choisir-une-longue-phrase-secrete"
.\.venv\Scripts\python.exe admin/run.py
```

Ouvrir `http://127.0.0.1:8765` et se connecter. Si ce port est occupé, définir par exemple `$env:DAYONE_BIND_PORT = "8875"` avant le lancement. Un second rôle de relecteur peut être activé avec `$env:DAYONE_REVIEWER_PASSWORD = "une-autre-longue-phrase-secrete"` ; ce rôle ne peut pas modifier la configuration ou relancer toute la file. Les trois dossiers de départ sont entièrement fictifs et servent à explorer l'interface ; ils ne sont pas une sortie OCR. La base se trouve dans `admin/.runtime/local/` par défaut et les poids dans `admin/.models/`. Ces répertoires sont exclus de Git. Garder le même mot de passe administrateur : il dérive la clé de chiffrement et sa perte rend la base irrécupérable.

Pour installer les poids EasyOCR une fois, sans utiliser d'image patiente :

```powershell
.\.venv\Scripts\python.exe admin/setup_models.py
```

Cette étape télécharge des **poids de modèle uniquement**. Ensuite, `run.py` lance EasyOCR avec `download_enabled=False`, et l'OCR n'émet aucune requête réseau. Les langues du profil initial sont français et anglais ; l'arabe demande un modèle compatible distinct et une évaluation dédiée. Une déconnexion réseau après installation n'empêche pas l'OCR local. La qualité sur l'écriture manuscrite et les tableaux reste à mesurer.

## Parcours

1. Ouvrir **Bot local**, créer une conversation fictive, envoyer « âge 28 », puis « confirmer âge 28 » ou « corriger âge 29 », et enfin « rapport ». Une valeur libre reste une suggestion ; seule la commande explicite de l'administrateur connecté confirme le champ. Le rapport de démonstration est agrégé et le bot ne fournit aucun conseil médical.
2. Ouvrir **Relecture**, corriger ou confirmer chaque champ. Les statuts `NON_FOURNI`, `ILLISIBLE`, `INCONNU` et `NON_APPLICABLE` restent explicites. Le statut `À_RÉVISER` bloque la validation. Une réponse OCR ou du bot ne remplace jamais un champ déjà confirmé.
3. Pour l'OCR, joindre une ou plusieurs images synthétiques, masquer visuellement chaque zone identifiante avant sauvegarde et confirmer le contrôle. Le serveur applique les masques en mémoire avant stockage chiffré. Il calcule une luminosité, un contraste et un indicateur de netteté heuristiques. L'OCR propose des valeurs avec page et confiance brute non calibrée. La file persiste et la clé d'idempotence évite de répéter une opération après perte de réponse.
4. Créer une **visite liée** depuis un dossier ou vérifier le code exact d'un autre dossier avant liaison manuelle. Le code est aléatoire ; aucun rapprochement probabiliste de patientes n'est effectué.
5. Ouvrir **Configuration** pour les langues OCR, l'ordre de relecture et la reprise de la file. Le mot de passe reste dans une variable d'environnement.

Le mot « WhatsApp » décrit ici le style du dialogue. Une intégration réelle avec WhatsApp ferait nécessairement transiter les messages et médias par Meta et sortirait de la contrainte « tout local ».

## Portée actuelle et score du défi

Cette console matérialise la capture expurgée, la relecture humaine, les statuts par champ, un OCR EasyOCR local et un bot déterministe local. Les valeurs des trois dossiers initiaux sont des exemples saisis pour la démonstration, pas des résultats de modèle.

Le [benchmark local](benchmark-results.json) rend huit lignes du CSV synthétique fourni en cartes imprimées artificielles, propres et à faible contraste : **48 valeurs correctes sur 48** pour âge, gestité et parité ; **0 faux positif HCV sur 16 cartes sans ce champ**. Le chargement des poids et l'inférence ont été exécutés avec les connexions réseau bloquées. Ces chiffres ne représentent **pas** la précision sur les photos manuscrites du défi : il manque une correspondance fiable entre les photos et les lignes CSV ainsi qu'une vérité terrain annotée par cellule. La confiance d'EasyOCR affichée dans l'interface n'est pas calibrée.

Le barème officiel totalise 100 points : extraction 30, incertitude 20, vérification conversationnelle 20, robustesse hors ligne 15, liaison patiente et confidentialité 10, code et documentation 5. Pour progresser, les priorités sont :

1. Établir un jeu de vérité terrain par dossier, visite, champ et cellule, puis mesurer exactitude, abstention, faux positifs et temps de relecture sur des dossiers tenus à l'écart du réglage.
2. Ajouter une localisation des cellules et une extraction par colonne/visite, avec confiance réellement calibrée et preuve visuelle, plutôt que les seules expressions régulières actuelles.
3. Étendre le bot local aux questions de confirmation et aux corrections guidées champ par champ. Ne jamais transformer une suggestion en valeur confirmée sans action explicite.
4. Ajouter une synchronisation chiffrée entre appareils, avec accusés persistants et résolution humaine des conflits. Le prototype garde une file OCR locale et un historique de versions, mais ne synchronise pas plusieurs appareils.
5. Documenter des démonstrations hors réseau avec images synthétiques, toutes les limites observées, les licences des poids et les règles de confidentialité. Aucun diagnostic ni score de risque clinique.

La [méthode de mesure et le plan détaillé](../docs/VERIFICATIONS-COMPLEMENTAIRES.md) restent le guide de référence pour ces étapes ; la décision « tout local » en tête de ce document prévaut sur l'ancienne architecture distante.

## Vérifications reproductibles

```powershell
.\.venv\Scripts\python.exe -m pytest admin/tests/test_local_flow.py -q
$env:DAYONE_SYNTHETIC_CSV = "C:\chemin\vers\maternal_registry_synthetic.csv"
.\.venv\Scripts\python.exe admin/benchmark_ocr.py
```

Le 3 octobre 2026, les tests couvrent : authentification/rôles/CSRF ; confirmation conversationnelle explicite ; deux pages et OCR avec réseau bloqué, chiffrement des images, préservation d'une correction humaine, clé d'idempotence et visite liée ; statuts illisibles et validation bloquée ; refus d'une liaison non confirmée, correction concurrente et récupération d'une opération interrompue. Le benchmark génère ses images en mémoire et n'écrit que des comptes agrégés. Versions observées : Python 3.11, FastAPI 0.142.2, Uvicorn 0.54.0, Pillow 12.3.0, EasyOCR 1.7.2, Torch 2.11.0, cryptography 46.0.7, pytest 9.1.1.

**Démo hors réseau :** installer les dépendances et poids une fois, puis couper Internet en laissant la machine allumée. Lancer le serveur et parcourir Bot local → Relecture → import de deux pages fictives expurgées → OCR → correction → visite liée. Une opération OCR en attente reste dans SQLite ; après redémarrage, utiliser Configuration → « Reprendre la file locale ». Aucun service distant ne se synchronise au retour d'Internet dans cette version.

## Sécurité et limites

Le chiffrement des données au repos utilise une clé dérivée du mot de passe admin. Perdre ce mot de passe rend la base irrécupérable. La session déverrouillée et le navigateur restent exposés à une personne ayant accès à l'ordinateur. Le masquage manuel doit être vérifié par un humain : le prototype ne peut pas garantir qu'un identifiant hors des rectangles a été retiré. Les fichiers transmis par le navigateur peuvent exister dans des caches du système hors du contrôle de l'application. Utiliser **uniquement les spécimens fictifs**.

Les sources `dayone-participants.zip` et `data/` ne sont pas modifiées. Les trois questions encore ouvertes sont : conservation d'une image expurgée face à l'exigence d'« original » intact, mapping officiel photo/CSV pour mesurer le score et distinction du champ hépatite C face à `Ag HBs` sur le formulaire. Le paquet [EasyOCR 1.7.2](https://github.com/JaidedAI/EasyOCR) installé indique la licence Apache 2.0 ; les conditions propres aux poids téléchargés doivent aussi être vérifiées avant la remise. Documenter les résultats réellement obtenus et confirmer les règles de partage des images synthétiques. Ne pas ajouter les PDFs/photos sources ou `.runtime/` au dépôt.
