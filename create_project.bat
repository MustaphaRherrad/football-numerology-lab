@echo off
chcp 65001 > nul
echo Création de l'arborescence du projet en cours...

:: --- Création de la structure des dossiers ---

:: Dossiers sous data
mkdir "data\raw\football-data"
mkdir "data\interim"
mkdir "data\processed"
mkdir "data\features"
mkdir "data\catalog"
mkdir "data\reports"

:: Autres dossiers principaux et sous-dossiers
mkdir "notebooks"
mkdir "src"
mkdir "outputs\tables"
mkdir "outputs\charts"
mkdir "outputs\models"
mkdir "outputs\logs"
mkdir "docs"

:: --- Création des fichiers vides ---

:: Notebooks (fichiers vides avec structure minimale JSON pour Jupyter)
set "empty_notebook={""cells"": [], ""metadata"": {}, ""nbformat"": 4, ""nbformat_minor"": 2}"

echo %empty_notebook% > "notebooks\01_collect_football_data.ipynb"
echo %empty_notebook% > "notebooks\02_inspect_raw_files.ipynb"
echo %empty_notebook% > "notebooks\03_clean_matches.ipynb"
echo %empty_notebook% > "notebooks\04_build_analytical_dataset.ipynb"
echo %empty_notebook% > "notebooks\05_numerology_date_features.ipynb"
echo %empty_notebook% > "notebooks\06_global_patterns_analysis.ipynb"
echo %empty_notebook% > "notebooks\07_team_date_affinity.ipynb"
echo %empty_notebook% > "notebooks\08_predictive_tests.ipynb"

:: Scripts Python (src)
type nul > "src\__init__.py"
type nul > "src\config.py"
type nul > "src\collect.py"
type nul > "src\clean.py"
type nul > "src\features_calendar.py"
type nul > "src\features_numerology.py"
type nul > "src\features_bookmakers.py"
type nul > "src\features_team_affinity.py"
type nul > "src\evaluation.py"
type nul > "src\plots.py"

:: Documents (docs)
type nul > "docs\roadmap.md"
type nul > "docs\data_dictionary.md"
type nul > "docs\methodology.md"

:: Fichiers à la racine
type nul > ".gitignore"
type nul > "requirements.txt"
type nul > "README.md"

echo.
echo C'est tout bon ! L'arborescence a été créée avec succès.
pause