# Football Numerology Lab

Projet exploratoire d’analyse statistique des résultats de football à partir des données historiques de football-data.co.uk.

L’objectif initial est de tester empiriquement si des variables dérivées des dates de match peuvent présenter un signal statistique ou prédictif sur les résultats H/D/A.

Le projet construit aussi une base football historique propre et réutilisable pour d’autres analyses ML.

## Structure

- `src/` : scripts Python réutilisables.
- `notebooks/` : notebooks d’exploration.
- `docs/` : notes méthodologiques.
- `data/` : données locales non versionnées.
- `outputs/` : sorties générées non versionnées.

## Données

Les datasets ne sont pas inclus dans le dépôt GitHub.

Les données brutes proviennent de football-data.co.uk et doivent être téléchargées localement via les scripts de collecte.

## Pipeline actuel

1. Collecte des fichiers CSV historiques.
2. Fusion en base brute.
3. Nettoyage des matchs.
4. Ajout de variables calendaires et numérologiques.
5. Calcul d’affinités historiques sans fuite temporelle.
6. Comparaison avec une baseline bookmaker.