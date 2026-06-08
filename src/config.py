from pathlib import Path

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Dossiers principaux
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
FEATURES_DATA_DIR = DATA_DIR / "features"
CATALOG_DIR = DATA_DIR / "catalog"
DATA_REPORTS_DIR = DATA_DIR / "reports"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TABLES_DIR = OUTPUTS_DIR / "tables"
CHARTS_DIR = OUTPUTS_DIR / "charts"
MODELS_DIR = OUTPUTS_DIR / "models"
LOGS_DIR = OUTPUTS_DIR / "logs"

DOCS_DIR = PROJECT_ROOT / "docs"

# Dossier spécifique football-data.co.uk
FOOTBALL_DATA_RAW_DIR = RAW_DATA_DIR / "football-data"

# URL de base football-data.co.uk
FOOTBALL_DATA_BASE_URL = "https://www.football-data.co.uk/mmz4281"

# Championnats à collecter dans une première version
# On pourra élargir ensuite.
LEAGUES = {
    "E0": {"country": "England", "division": "Premier League"},
    "E1": {"country": "England", "division": "Championship"},
    "E2": {"country": "England", "division": "League One"},
    "E3": {"country": "England", "division": "League Two"},
    "F1": {"country": "France", "division": "Ligue 1"},
    "F2": {"country": "France", "division": "Ligue 2"},
    "SP1": {"country": "Spain", "division": "La Liga"},
    "SP2": {"country": "Spain", "division": "Segunda Division"},
    "I1": {"country": "Italy", "division": "Serie A"},
    "I2": {"country": "Italy", "division": "Serie B"},
    "D1": {"country": "Germany", "division": "Bundesliga"},
    "D2": {"country": "Germany", "division": "2. Bundesliga"},
    "N1": {"country": "Netherlands", "division": "Eredivisie"},
    "P1": {"country": "Portugal", "division": "Primeira Liga"},
    "B1": {"country": "Belgium", "division": "Jupiler League"},
    "SC0": {"country": "Scotland", "division": "Premiership"},
    "SC1": {"country": "Scotland", "division": "Championship"},
    "T1": {"country": "Turkey", "division": "Super Lig"},
    "G1": {"country": "Greece", "division": "Super League"},
}

# Première saison à tenter
# football-data utilise un format type 2324 pour 2023-2024.
START_SEASON = 1993
END_SEASON = 2026


def season_to_code(start_year: int) -> str:
    """
    Convertit une saison 2023-2024 en code football-data : 2324.
    """
    end_year = start_year + 1
    return f"{str(start_year)[-2:]}{str(end_year)[-2:]}"


def season_label(start_year: int) -> str:
    """
    Convertit 2023 en label lisible : 2023-2024.
    """
    return f"{start_year}-{start_year + 1}"


def ensure_directories() -> None:
    """
    Crée les dossiers nécessaires si absents.
    """
    directories = [
        DATA_DIR,
        RAW_DATA_DIR,
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        FEATURES_DATA_DIR,
        CATALOG_DIR,
        DATA_REPORTS_DIR,
        OUTPUTS_DIR,
        TABLES_DIR,
        CHARTS_DIR,
        MODELS_DIR,
        LOGS_DIR,
        DOCS_DIR,
        FOOTBALL_DATA_RAW_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)