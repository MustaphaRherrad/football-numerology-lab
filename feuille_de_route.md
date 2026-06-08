# Feuille de route du projet

## Phase 1 — Collecte complète des données

Objectif : constituer une base historique locale, proprement organisée, sans encore faire d’analyse.

### 1.1. Identifier les championnats disponibles

Tu peux commencer par les grands championnats :

```text
Angleterre : E0, E1, E2, E3, EC
France     : F1, F2
Espagne    : SP1, SP2
Italie     : I1, I2
Allemagne  : D1, D2
Pays-Bas   : N1
Portugal   : P1
Belgique   : B1
Écosse     : SC0, SC1
Turquie    : T1
Grèce      : G1
```

Pour l’étude, il vaut mieux collecter large, mais garder une priorité :

```text
Priorité 1 : Big 5 + deuxième divisions
Priorité 2 : Pays-Bas, Portugal, Belgique, Écosse
Priorité 3 : autres championnats disponibles
```

---

### 1.2. Télécharger les fichiers historiques

Organisation conseillée :

```text
data/
  raw/
    football-data/
      1993-1994/
        E0.csv
        E1.csv
      1994-1995/
        E0.csv
        E1.csv
      ...
      2025-2026/
        E0.csv
        F1.csv
        SP1.csv
```

Il faut garder les fichiers bruts **intacts**.

Règle importante :

```text
Ne jamais modifier les fichiers raw.
```

On créera ensuite :

```text
data/processed/
data/interim/
data/features/
```

---

### 1.3. Créer un inventaire des fichiers collectés

Avant nettoyage, il faut créer un fichier catalogue :

```text
data/catalog/football_data_files.csv
```

Avec :

```text
season
country
division
file_path
download_url
download_date
n_rows
n_columns
status
error_message
```

Ce catalogue servira à repérer :

```text
fichiers manquants
fichiers vides
fichiers illisibles
championnats non disponibles certaines saisons
colonnes différentes selon les années
```

C’est une étape très importante, car les CSV football-data n’ont pas toujours exactement les mêmes colonnes d’une saison à l’autre.

---

## Phase 2 — Ingestion et standardisation

Objectif : fusionner tous les CSV dans une structure commune.

### 2.1. Lire tous les fichiers

On crée une table unique :

```text
matches_raw_all
```

Avec au minimum :

```text
source_file
season
division
Date
HomeTeam
AwayTeam
FTHG
FTAG
FTR
```

Et on conserve aussi toutes les colonnes disponibles :

```text
B365H
B365D
B365A
AvgH
AvgD
AvgA
MaxH
MaxD
MaxA
HS
AS
HST
AST
HC
AC
HY
AY
HR
AR
...
```

---

### 2.2. Harmoniser les colonnes anciennes/récentes

Certaines colonnes ont changé de nom ou sont absentes selon les saisons.

Exemples d’équivalences à prévoir :

```text
FTHG / HG  = buts domicile
FTAG / AG  = buts extérieur
FTR / Res  = résultat final
```

Le fichier `notes.txt` précise justement que `FTHG` et `HG` désignent les buts domicile, `FTAG` et `AG` les buts extérieur, et `FTR` ou `Res` le résultat final. ([Football Data][2])

Il faudra donc construire un dictionnaire :

```python
COLUMN_ALIASES = {
    "HG": "FTHG",
    "AG": "FTAG",
    "Res": "FTR"
}
```

---

### 2.3. Créer un schéma canonique

Table principale :

```text
matches
```

Colonnes minimales :

```text
match_id
season
country
division
date
home_team
away_team
home_goals
away_goals
result
home_points
away_points
total_goals
goal_diff
source_file
```

Colonnes utiles pour la suite :

```text
b365_h
b365_d
b365_a
avg_h
avg_d
avg_a
max_h
max_d
max_a
```

Colonnes optionnelles :

```text
home_shots
away_shots
home_shots_target
away_shots_target
home_corners
away_corners
home_yellow_cards
away_yellow_cards
home_red_cards
away_red_cards
```

---

## Phase 3 — Nettoyage des données

Objectif : obtenir une base fiable avant toute exploration.

### 3.1. Nettoyage des dates

Points à gérer :

```text
dates en dd/mm/yy
dates en dd/mm/yyyy
problèmes de parsing selon les saisons
dates manquantes
dates incohérentes par rapport à la saison
```

Contrôles :

```text
une saison 2020-2021 ne doit pas contenir 2015
une saison 2025-2026 ne doit pas contenir 2023
```

On peut tolérer quelques matchs en juillet/août et mai/juin selon les saisons.

---

### 3.2. Nettoyage des noms d’équipes

C’est une étape critique.

Une même équipe peut avoir plusieurs noms selon les saisons :

```text
Man United / Manchester United
Tottenham / Tottenham Hotspur
Paris SG / PSG
Inter / Inter Milan
Ath Madrid / Atletico Madrid
```

Il faudra créer une table :

```text
team_aliases.csv
```

Avec :

```text
raw_team_name
canonical_team_name
country
notes
```

Exemple :

```text
Man United, Manchester United, England
Paris SG, Paris Saint-Germain, France
Ath Madrid, Atletico Madrid, Spain
```

Au début, on peut ne corriger que les alias détectés automatiquement.

Plus tard, on enrichira à la main.

---

### 3.3. Suppression des lignes invalides

À exclure :

```text
lignes sans date
lignes sans équipe domicile/extérieure
lignes sans résultat final
lignes avec FTR hors H/D/A
lignes avec buts manquants
lignes dupliquées exactes
```

À signaler mais pas forcément exclure :

```text
cotes manquantes
statistiques de match manquantes
nom d’arbitre absent
heure absente
```

---

### 3.4. Contrôle des résultats

Vérifier que :

```text
si home_goals > away_goals alors result = H
si home_goals = away_goals alors result = D
si home_goals < away_goals alors result = A
```

Toute incohérence doit être mise dans :

```text
data/reports/result_inconsistencies.csv
```

---

## Phase 4 — Construction de la base analytique

Objectif : créer une table propre, exploitable pour tous les modèles.

### 4.1. Table match-level

```text
analytical_matches.parquet
```

Une ligne = un match.

Colonnes :

```text
match_id
date
season
country
division
home_team
away_team
home_goals
away_goals
result
home_points
away_points
```

---

### 4.2. Ajout des variables calendaires classiques

Avant la numérologie, il faut des variables objectives :

```text
year
month
day
weekday
is_weekend
season_month
days_since_season_start
```

Cela permettra de vérifier si la variable numérologique ne capte pas simplement un effet calendrier.

Exemple :

```text
les matchs du samedi
les matchs de Boxing Day
les matchs de début ou fin de saison
```

---

### 4.3. Ajout des variables bookmaker

À partir des cotes :

```text
implied_prob_home = 1 / avg_h
implied_prob_draw = 1 / avg_d
implied_prob_away = 1 / avg_a
```

Puis normalisation :

```text
p_home = implied_prob_home / total
p_draw = implied_prob_draw / total
p_away = implied_prob_away / total
```

Cela donnera la baseline la plus importante.

---

## Phase 5 — Création des variables numérologiques

Objectif : construire les variables sans encore conclure.

### 5.1. Nombre du jour

Pour chaque match :

```text
date_num_1_9
date_num_master
```

Exemple :

```text
06/06/2026 → 0+6+0+6+2+0+2+6 = 22
avec maîtres : 22
réduit : 4
```

---

### 5.2. Plusieurs variantes à tester

Il ne faut pas se limiter à une seule méthode, car l’étude est exploratoire.

Variables possibles :

```text
date_num_full_digits
date_num_day_month_year
date_num_day_month_only
date_num_seasonal
weekday_num
```

Mais attention : plus on teste de variantes, plus le risque de faux motifs augmente.

Donc il faudra classer :

```text
Hypothèse principale :
date_num_1_9

Hypothèses secondaires :
date_num_master
date_num_day_month_only
```

---

## Phase 6 — Analyse descriptive globale

Objectif : regarder si les nombres de date ont un effet global.

Questions :

```text
Les jours 1 à 9 ont-ils une distribution H/D/A différente ?
Certains nombres produisent-ils plus de nuls ?
Certains nombres produisent-ils plus de victoires extérieures ?
Les effets sont-ils stables par championnat ?
Les effets sont-ils stables par période ?
```

Sorties attendues :

```text
table_result_by_date_num.csv
chart_result_distribution_by_date_num.png
chi_square_test_results.csv
```

Exemple de tableau :

```text
date_num | matches | home_win_rate | draw_rate | away_win_rate
1        | 12500   | 44.1%         | 26.2%     | 29.7%
2        | 12180   | 45.0%         | 25.4%     | 29.6%
...
```

À ce stade, on ne parle pas encore d’équipes.

---

## Phase 7 — Analyse équipe × nombre

Objectif : voir si certaines équipes performent différemment selon les nombres.

### 7.1. Calcul des performances par équipe

Pour chaque équipe et chaque `date_num_1_9` :

```text
team
date_num
matches_total
points_per_match
win_rate
draw_rate
loss_rate
goal_diff_avg
home_matches
away_matches
home_points_per_match
away_points_per_match
```

Avec seuils :

```text
moins de 20 matchs : signal très fragile
20 à 49 matchs : signal faible
50 à 99 matchs : signal exploitable
100+ matchs : signal solide
```

---

### 7.2. Comparer à la moyenne de l’équipe

Le piège serait de dire :

```text
PSG gagne souvent les jours 4
```

Mais PSG gagne souvent tout court.

Donc il faut calculer :

```text
team_global_points_per_match
team_date_num_points_per_match
delta_vs_team_average
```

Exemple :

```text
PSG moyenne globale : 2.15 pts/match
PSG jour 4 : 2.28 pts/match
delta : +0.13
```

C’est le delta qui compte, pas le niveau brut.

---

### 7.3. Séparer domicile et extérieur

Il faudra faire deux analyses :

```text
team_home_date_num_affinity
team_away_date_num_affinity
```

Parce que le domicile est un facteur énorme.

---

## Phase 8 — Analyse dynamique sans fuite de données

Objectif : éviter de tricher avec le futur.

Pour chaque match, on calcule les affinités uniquement avec les matchs passés.

Exemple pour un match en 2024 :

```text
HomeTeam historique sur ce nombre avant la date du match
AwayTeam historique sur ce nombre avant la date du match
```

Variables :

```text
home_affinity_prior
away_affinity_prior
delta_affinity_prior
home_sample_size_prior
away_sample_size_prior
```

C’est cette table-là qui sera utilisée pour tester la prédiction.

C’est probablement la phase la plus importante du projet.

---

## Phase 9 — Tests prédictifs simples

Objectif : voir si le signal numérologique a une valeur prédictive minimale.

### 9.1. Test par buckets

On classe les matchs selon :

```text
delta_affinity_prior
```

Par exemple :

```text
très défavorable domicile
défavorable domicile
neutre
favorable domicile
très favorable domicile
```

Puis on regarde :

```text
% victoires domicile
% nuls
% victoires extérieur
ROI théorique selon cotes
```

Question centrale :

```text
Quand delta_affinity_prior est très favorable à domicile,
le taux de victoire domicile augmente-t-il vraiment ?
```

---

### 9.2. Test de filtre

Exemple :

```text
On ne garde que les matchs où :
bookmaker favorise HomeTeam
ET
delta_affinity_prior favorise HomeTeam
```

Puis comparaison :

```text
Favori bookmaker seul
vs
Favori bookmaker + filtre numérologique
```

Mesures :

```text
accuracy
precision sur matchs sélectionnés
nombre de matchs retenus
taux de couverture
log loss
Brier score
ROI théorique
```

Le filtre peut être intéressant même s’il réduit fortement le nombre de matchs.

---

## Phase 10 — Modélisation ML

Objectif : tester si les variables numérologiques améliorent un modèle.

### 10.1. Modèle baseline

Variables :

```text
p_home_bookmaker
p_draw_bookmaker
p_away_bookmaker
home_advantage
division
season
```

Modèles :

```text
Logistic Regression multinomiale
Random Forest
XGBoost
LightGBM
```

---

### 10.2. Modèle enrichi

Même modèle, mais avec :

```text
date_num_1_9
home_affinity_prior
away_affinity_prior
delta_affinity_prior
home_sample_size_prior
away_sample_size_prior
```

Comparaison :

```text
baseline sans numérologie
vs
modèle avec numérologie
```

Critères :

```text
accuracy
macro F1
log loss
Brier score
calibration
ROI simulé
```

Le signal est intéressant seulement si l’amélioration tient sur des saisons non vues.

---

## Phase 11 — Validation robuste

Objectif : ne pas se faire piéger par du bruit.

Tests indispensables :

```text
train/test par saison
validation walk-forward
test par championnat
test par période
test avec permutation aléatoire des nombres
```

Le test de permutation est très utile :

```text
On mélange les date_num au hasard.
Si le modèle fait aussi bien, le signal numérologique ne vaut rien.
```

---

## Phase 12 — Restitution des résultats

À la fin, tu peux produire un rapport :

```text
reports/
  01_data_collection_report.md
  02_data_quality_report.md
  03_global_numerology_analysis.md
  04_team_affinity_analysis.md
  05_predictive_tests.md
  06_final_conclusion.md
```

Avec des graphiques :

```text
distribution des résultats par nombre
heatmap équipe × nombre
delta de performance par nombre
courbes de performance hors échantillon
comparaison bookmaker vs bookmaker+filtre
```

---

# Structure de projet conseillée

```text
football-numerology-study/
  data/
    raw/
      football-data/
    interim/
    processed/
    features/
    catalog/
    reports/
  notebooks/
    01_collect_data.ipynb
    02_clean_data.ipynb
    03_data_quality_audit.ipynb
    04_global_date_number_analysis.ipynb
    05_team_number_affinity.ipynb
    06_predictive_tests.ipynb
  src/
    config.py
    collect.py
    clean.py
    features_calendar.py
    features_numerology.py
    features_bookmakers.py
    features_team_affinity.py
    evaluation.py
    plots.py
  outputs/
    tables/
    charts/
    models/
  README.md
```

---

# Ordre de travail recommandé

Je ferais dans cet ordre :

```text
1. Collecter toute la base football-data.co.uk
2. Créer le catalogue des fichiers
3. Fusionner tous les CSV en une table brute unique
4. Nettoyer dates, noms d’équipes, résultats
5. Créer une table analytique propre
6. Ajouter les variables calendaires
7. Ajouter les variables bookmaker
8. Ajouter les nombres de dates
9. Faire l’analyse globale nombre → H/D/A
10. Faire l’analyse équipe × nombre
11. Construire les affinités historiques sans fuite de données
12. Tester le filtre contre la baseline bookmaker
13. Tester un modèle ML avec/sans variables numérologiques
14. Conclure froidement
```

---

# Décision méthodologique importante

Pour cette étude, je te conseille de distinguer clairement deux niveaux :

```text
Niveau croyance :
La numérologie comme hypothèse culturelle ancienne.

Niveau data :
Les nombres ne sont que des variables catégorielles dérivées de la date.
```

Autrement dit, dans le code et les rapports, on ne dit pas :

```text
ce nombre domine celui-ci
```

On dit :

```text
cette variable catégorielle est-elle associée à une variation mesurable du résultat ?
```

C’est ce cadrage qui rendra l’étude propre, même si l’idée de départ est farfelue.

La prochaine étape logique serait de commencer par le **script de collecte automatique** de toute la base football-data.co.uk, avec un catalogue des fichiers téléchargés et un journal d’erreurs.

[1]: https://www.football-data.co.uk/data.php?utm_source=chatgpt.com "Football Results, Statistics & Soccer Betting Odds Data"
[2]: https://www.football-data.co.uk/notes.txt?utm_source=chatgpt.com "Notes"
