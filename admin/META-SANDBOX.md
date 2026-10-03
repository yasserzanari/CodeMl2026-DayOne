# Sandbox WhatsApp Business — option désactivée

Le défi accepte un prototype conversationnel **simulé ou réel**. La console livrée utilise le bot local et n'ouvre aucun webhook Meta. Un vrai canal WhatsApp n'est pas compatible avec l'exigence « aucune donnée réelle de patiente vers un tiers » : les messages et médias traverseraient l'infrastructure de Meta. Utiliser exclusivement des contenus synthétiques dans un éventuel sandbox.

## Pré-requis absents

- Compte Meta Developer et application WhatsApp Business Platform en mode test.
- Numéro de test, identifiant de numéro et identifiant du compte WhatsApp Business.
- Jeton d'accès de test, secret d'application, jeton de vérification de webhook.
- URL HTTPS publique de test et autorisation de recevoir les événements webhook.

Ces éléments ne sont pas fournis dans le projet. Aucun token, numéro, secret ou bouton « connecté » n'est inventé. Le sandbox **n'a pas été activé ni testé**.

## Adaptateur à ajouter uniquement pour une démonstration synthétique

1. Mettre tous les secrets dans des variables d'environnement locales exclues de Git. Garder l'adaptateur désactivé sans un indicateur explicite de mode sandbox et un avertissement dans l'interface.
2. Vérifier la requête de challenge du webhook et la signature `X-Hub-Signature-256` sur le corps brut avec le secret d'application. Rejeter tout événement non signé ou mal signé avant lecture des messages.
3. Dédupliquer par identifiant de message Meta persistant. Acquitter rapidement puis traiter dans une file durable ; appliquer des reprises bornées sans renvoyer deux fois le même rapport.
4. N'accepter que des identifiants de test et des scénarios synthétiques explicitement préparés. Interdire les images, textes cliniques, OCR, identifiants et rapports de patientes réelles dans les deux sens. Aucun pont automatique de la base locale vers Meta.
5. Utiliser les mêmes règles de suggestion et relecture que le mode local ; le sandbox ne doit pas confirmer une valeur ni émettre un conseil clinique.
6. Vérifier la conformité et la rétention des messages côté Meta avant toute démonstration. Documenter séparément le protocole testé, les événements réellement reçus, les erreurs et les doublons.

L'obtention de ces accès et le test de bout en bout sont des prérequis extérieurs. Le parcours du jury reste entièrement réalisable dans le bot local sans eux.
