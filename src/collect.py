from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from src.config import (
    CATALOG_DIR,
    FOOTBALL_DATA_BASE_URL,
    FOOTBALL_DATA_RAW_DIR,
    LEAGUES,
    START_SEASON,
    END_SEASON,
    ensure_directories,
    season_label,
    season_to_code,
)


CATALOG_FILE = CATALOG_DIR / "football_data_files.csv"


def build_download_url(season_start_year: int, league_code: str) -> str:
    """
    Exemple :
    saison 2023-2024 -> code 2324
    league E0 -> https://www.football-data.co.uk/mmz4281/2324/E0.csv
    """
    season_code = season_to_code(season_start_year)
    return f"{FOOTBALL_DATA_BASE_URL}/{season_code}/{league_code}.csv"


def get_local_file_path(season_start_year: int, league_code: str) -> Path:
    """
    Exemple :
    data/raw/football-data/2023-2024/E0.csv
    """
    season_dir = FOOTBALL_DATA_RAW_DIR / season_label(season_start_year)
    return season_dir / f"{league_code}.csv"


def try_read_csv_info(file_path: Path) -> tuple[int | None, int | None, str | None]:
    """
    Lit rapidement le CSV téléchargé pour récupérer nombre de lignes/colonnes.
    Retourne aussi un message d'erreur si lecture impossible.
    """
    try:
        df = pd.read_csv(file_path)
        return len(df), len(df.columns), None
    except Exception as exc:
        return None, None, str(exc)


def download_csv(
    url: str,
    output_path: Path,
    timeout: int = 20,
    overwrite: bool = False,
) -> dict:
    """
    Télécharge un fichier CSV.
    Retourne un dictionnaire de statut pour le catalogue.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        n_rows, n_columns, read_error = try_read_csv_info(output_path)

        return {
            "status": "already_exists",
            "http_status": None,
            "file_size_bytes": output_path.stat().st_size,
            "n_rows": n_rows,
            "n_columns": n_columns,
            "error_message": read_error,
        }

    try:
        response = requests.get(url, timeout=timeout)

        if response.status_code != 200:
            return {
                "status": "not_available",
                "http_status": response.status_code,
                "file_size_bytes": None,
                "n_rows": None,
                "n_columns": None,
                "error_message": f"HTTP {response.status_code}",
            }

        content = response.content

        # Certains fichiers absents peuvent retourner du HTML ou une page vide.
        if len(content) < 50:
            return {
                "status": "empty_or_invalid",
                "http_status": response.status_code,
                "file_size_bytes": len(content),
                "n_rows": None,
                "n_columns": None,
                "error_message": "Content too small",
            }

        output_path.write_bytes(content)

        n_rows, n_columns, read_error = try_read_csv_info(output_path)

        if read_error:
            status = "downloaded_but_read_error"
        else:
            status = "downloaded"

        return {
            "status": status,
            "http_status": response.status_code,
            "file_size_bytes": output_path.stat().st_size,
            "n_rows": n_rows,
            "n_columns": n_columns,
            "error_message": read_error,
        }

    except Exception as exc:
        return {
            "status": "request_error",
            "http_status": None,
            "file_size_bytes": None,
            "n_rows": None,
            "n_columns": None,
            "error_message": str(exc),
        }


def collect_football_data(
    start_season: int = START_SEASON,
    end_season: int = END_SEASON,
    leagues: dict = LEAGUES,
    overwrite: bool = False,
    sleep_seconds: float = 0.2,
) -> pd.DataFrame:
    """
    Collecte les CSV football-data.co.uk pour plusieurs saisons et championnats.

    end_season correspond à l'année de début de la dernière saison à tester.
    Exemple : 2025 = saison 2025-2026.
    """
    ensure_directories()

    records = []
    downloaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    jobs = []

    for season_start_year in range(start_season, end_season + 1):
        for league_code, league_info in leagues.items():
            jobs.append((season_start_year, league_code, league_info))

    for season_start_year, league_code, league_info in tqdm(jobs, desc="Collecte football-data"):
        url = build_download_url(season_start_year, league_code)
        local_path = get_local_file_path(season_start_year, league_code)

        result = download_csv(
            url=url,
            output_path=local_path,
            overwrite=overwrite,
        )

        records.append(
            {
                "season": season_label(season_start_year),
                "season_start_year": season_start_year,
                "season_code": season_to_code(season_start_year),
                "league_code": league_code,
                "country": league_info.get("country"),
                "division": league_info.get("division"),
                "download_url": url,
                "local_path": str(local_path),
                "downloaded_at": downloaded_at,
                **result,
            }
        )

        time.sleep(sleep_seconds)

    catalog = pd.DataFrame(records)
    catalog.to_csv(CATALOG_FILE, index=False, encoding="utf-8-sig")

    return catalog


def print_collection_summary(catalog: pd.DataFrame) -> None:
    """
    Affiche un résumé simple après collecte.
    """
    print("\nRésumé de collecte")
    print("===================")

    print("\nStatuts :")
    print(catalog["status"].value_counts(dropna=False))

    print("\nFichiers téléchargés ou déjà présents :")
    ok_statuses = ["downloaded", "already_exists"]
    ok_files = catalog[catalog["status"].isin(ok_statuses)]
    print(f"{len(ok_files)} fichiers OK")

    print("\nLignes collectées au total :")
    print(int(ok_files["n_rows"].fillna(0).sum()))

    print("\nCatalogue :")
    print(CATALOG_FILE)


if __name__ == "__main__":
    catalog_df = collect_football_data(
        start_season=1993,
        end_season=2025,
        leagues=LEAGUES,
        overwrite=False,
        sleep_seconds=0.2,
    )

    print_collection_summary(catalog_df)