# DayOne — console locale de suivi des registres

Prototype du défi DayOne pour convertir des registres maternels **fictifs** en dossiers structurés à relire. Le mode par défaut fonctionne sur une seule machine sans Internet après installation des dépendances et des poids OCR. Il ne donne ni diagnostic ni conseil médical.

## Ce que fait le prototype

- Tableau de bord agrégé et anonymisé ; connexion administrateur, rôle relecteur facultatif.
- Chat local de type WhatsApp : suggestions, confirmation/correction explicite par l'administrateur connecté et rapport de démonstration. **Aucune connexion à Meta**.
- Import de plusieurs pages PNG/JPEG, masquage manuel des zones identifiantes en mémoire avant stockage, contrôle qualité indicatif, images et messages chiffrés au repos.
- EasyOCR français/anglais pré-entraîné avec poids locaux et téléchargement désactivé pendant l'inférence ; suggestions par champ avec page et confiance brute, jamais validées automatiquement.
- Relecture avec statuts explicites, contrôle de version, protection des corrections humaines, file OCR SQLite persistante et reprise idempotente.
- Visites liées par code aléatoire exact après décision humaine. Pas de rapprochement probabiliste ni de synchronisation entre appareils.

## Démarrage Windows

Depuis la racine du dépôt :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r admin/requirements.txt
.\.venv\Scripts\python.exe admin/setup_models.py
$env:DAYONE_ADMIN_PASSWORD = "une-longue-phrase-secrete-a-conserver"
.\.venv\Scripts\python.exe admin/run.py
```

Ouvrir `http://127.0.0.1:8765`. Les trois dossiers de départ sont fictifs. Les poids ne contiennent aucune donnée patiente ; leur téléchargement initial demande Internet, puis le traitement est local. Le mot de passe dérive la clé de chiffrement : conserver le même mot de passe pour retrouver la base. Voir [les commandes, rôles, flux de démonstration et limites](admin/README.md).

## Vérifications

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest admin/tests/test_local_flow.py -q
$env:DAYONE_SYNTHETIC_CSV = "C:\chemin\vers\maternal_registry_synthetic.csv"
.\.venv\Scripts\python.exe admin/benchmark_ocr.py
```

Le [rapport OCR agrégé](admin/benchmark-results.json) mesure 48 champs sur des **cartes imprimées artificielles** rendues depuis huit lignes du CSV synthétique : 48/48 corrects, avec réseau bloqué durant le chargement et l'inférence. Ce résultat ne mesure pas les photos manuscrites du défi : aucun mapping photo–ligne CSV ou vérité terrain par cellule n'est fourni. Ne pas présenter ce chiffre comme un score du jury.

## Confidentialité et sources

Les PDFs, photographies, CSV, archives, poids, bases, journaux et secrets restent hors de Git via [.gitignore](.gitignore). Les données du défi doivent être obtenues séparément par les canaux autorisés et conservées localement. La console n'est pas homologuée pour des données réelles. Le bot WhatsApp réel exigerait Meta et ferait sortir les messages de la machine : seul un [sandbox avec scénarios synthétiques](admin/META-SANDBOX.md) pourrait être envisagé, après obtention des accès nécessaires ; aucun adaptateur Meta n'est activé ou testé ici.

## Règles, barème et limites

Les [consignes analysées](docs/ANALYSE-ET-PLAN.md) et les [décisions complémentaires](docs/VERIFICATIONS-COMPLEMENTAIRES.md) détaillent le barème de 100 points, les statuts, la mesure et les cas de conflit. Trois points demandent encore une clarification officielle : conserver une image expurgée face à la règle sur l'original intact ; mapping image/CSV pour la notation ; distinction hépatite C versus `Ag HBs`. Le prototype garde HCV et HBs séparés et ne stocke pas d'image non expurgée.
