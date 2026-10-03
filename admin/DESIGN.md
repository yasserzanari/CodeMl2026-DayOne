---
version: alpha
name: "DayOne Console"
description: "Poste de contrôle local pour relire des registres maternels synthétiques, inspiré d'une fiche de suivi plutôt que d'un logiciel médical."
colors:
  primary: "#196B65"
  primary-deep: "#124D49"
  ink: "#233A3A"
  muted: "#607674"
  canvas: "#F3F7F6"
  surface: "#FFFFFF"
  line: "#D9E5E2"
  lilac: "#786BA4"
  lilac-pale: "#F0ECF8"
  coral: "#B96152"
  coral-pale: "#FFF0EA"
typography:
  display:
    fontFamily: "Georgia, 'Times New Roman', serif"
  body:
    fontFamily: "'Segoe UI', Arial, sans-serif"
  mono:
    fontFamily: "Consolas, 'Courier New', monospace"
rounded:
  DEFAULT: "0.75rem"
  sm: "0.45rem"
  lg: "1.25rem"
spacing:
  section-gap: "2rem"
  page-max: "90rem"
components:
  button: {}
  card: {}
  table: {}
  input: {}
---

# Identité du poste DayOne

Le tableau de bord s'inspire des marges, repères et annotations d'une fiche de suivi. L'accent vert indique une opération validée, le lilas une lecture à vérifier et le corail une action bloquée. Les couleurs seules ne portent jamais le statut : chaque état a un libellé.

L'interface est en français et s'adresse à une équipe qui travaille sur des données synthétiques. Elle doit rendre visibles les actions restantes, la provenance des champs et l'état du bot local. La typographie de titre évoque le registre ; les données, contrôles et valeurs utilisent une sans sérif lisible. Aucune police ni ressource distante n'est requise.

La signature visuelle est une marge verticale de dossier dans la liste de relecture. Elle encode l'état sans diminuer l'espace des données. Le reste de l'interface est sobre : contours fins, surfaces blanches, ombres rares et espacements réguliers. La référence n'est ni une application de diagnostic clinique ni une page marketing.

Ce document est la source des valeurs de couleur, de typo et de rayon recopiées dans `static/styles.css`. Toute modification durable doit modifier les deux fichiers ensemble.
