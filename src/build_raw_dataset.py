from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.config import CATALOG_DIR, INTERIM_DATA_DIR, ensure_directories


CATALOG_FILE = CATALOG_DIR / "football_data_files.csv"
RECOVERY_FILE = CATALOG_DIR / "read_errors_recovery_test.csv"
OUTPUT_FILE = INTERIM_DATA_DIR / "matches_raw_all.parquet"
OUTPUT_CSV_SAMPLE = INTERIM_DATA_DIR / "matches_raw_all_sample.csv"
INGESTION_REPORT = CATALOG_DIR / "raw_ingestion_report.csv"


def read_csv_robust(file_path: Path, preferred_encoding: str | None = None) -> tuple[pd.DataFrame | None, dict]:
    """
    Lecture robuste des CSV football-data.

    Retourne :
    - DataFrame ou None
    - dictionnaire de métadonnées de lecture
    """

    attempts = []

    if preferred_encoding:
        attempts.append({"encoding": preferred_encoding, "on_bad_lines": "skip"})

    attempts.extend(
        [
            {"encoding": "utf-8", "on_bad_lines": "error"},
            {"encoding": "utf-8-sig", "on_bad_lines": "skip"},
            {"encoding": "latin1", "on_bad_lines": "skip"},
            {"encoding": "cp1252", "on_bad_lines": "skip"},
        ]
    )

    # éviter les doublons d'essais
    seen = set()
    unique_attempts = []

    for attempt in attempts:
        key = (attempt["encoding"], attempt["on_bad_lines"])
        if key not in seen:
            unique_attempts.append(attempt)
            seen.add(key)

    last_error = None

    for attempt in unique_attempts:
        try:
            df = pd.read_csv(file_path, **attempt)

            return df, {
                "read_status": "ok",
                "read_encoding": attempt["encoding"],
                "read_on_bad_lines": attempt["on_bad_lines"],
                "read_error": None,
            }

        except Exception as exc:
            last_error = str(exc)

    return None, {
        "read_status": "failed",
        "read_encoding": None,
        "read_on_bad_lines": None,
        "read_error": last_error,
    }


def build_preferred_encoding_map() -> dict[str, str]:
    """
    Récupère les encodages qui ont réussi dans read_errors_recovery_test.csv.
    """
    if not RECOVERY_FILE.exists():
        return {}

    recovery = pd.read_csv(RECOVERY_FILE)

    ok = recovery[recovery["read_status"] == "ok"].copy()

    return dict(zip(ok["local_path"], ok["encoding"]))


def build_raw_dataset() -> pd.DataFrame:
    ensure_directories()

    catalog = pd.read_csv(CATALOG_FILE)
    preferred_encoding_map = build_preferred_encoding_map()

    usable_statuses = ["downloaded", "already_exists", "downloaded_but_read_error"]
    files = catalog[catalog["status"].isin(usable_statuses)].copy()

    all_frames = []
    report_rows = []

    for _, row in tqdm(files.iterrows(), total=len(files), desc="Fusion des CSV"):
        file_path = Path(row["local_path"])

        preferred_encoding = preferred_encoding_map.get(str(file_path))

        df, read_info = read_csv_robust(
            file_path=file_path,
            preferred_encoding=preferred_encoding,
        )

        report_row = {
            "season": row["season"],
            "season_start_year": row["season_start_year"],
            "season_code": row["season_code"],
            "league_code": row["league_code"],
            "country": row["country"],
            "division": row["division"],
            "local_path": str(file_path),
            "source_status": row["status"],
            **read_info,
            "n_rows_read": None if df is None else len(df),
            "n_columns_read": None if df is None else len(df.columns),
        }

        if df is None:
            report_rows.append(report_row)
            continue

        # Supprimer les lignes totalement vides
        df = df.dropna(how="all").copy()

        # Ajouter métadonnées de source
        df["season"] = row["season"]
        df["season_start_year"] = row["season_start_year"]
        df["season_code"] = row["season_code"]
        df["league_code"] = row["league_code"]
        df["country"] = row["country"]
        df["division"] = row["division"]
        df["source_file"] = str(file_path)
        df["source_status"] = row["status"]
        df["read_encoding"] = read_info["read_encoding"]

        all_frames.append(df)
        report_rows.append(report_row)

    report = pd.DataFrame(report_rows)
    report.to_csv(INGESTION_REPORT, index=False, encoding="utf-8-sig")

    if not all_frames:
        raise RuntimeError("Aucun fichier CSV n'a pu être fusionné.")

    raw_all = pd.concat(all_frames, ignore_index=True, sort=False)

    # Important :
    # La base brute contient des colonnes hétérogènes selon les saisons.
    # Certaines colonnes mélangent nombres et textes.
    # Pour éviter les erreurs PyArrow, on force tout en texte dans la couche brute.
    raw_all = raw_all.astype("string")

    # Sauvegarde parquet
    raw_all.to_parquet(OUTPUT_FILE, index=False)

    # Petit échantillon CSV pour inspection rapide
    raw_all.head(1000).to_csv(OUTPUT_CSV_SAMPLE, index=False, encoding="utf-8-sig")

    return raw_all


def print_summary(df: pd.DataFrame) -> None:
    print("\nBase brute fusionnée")
    print("====================")
    print(f"Lignes : {len(df):,}")
    print(f"Colonnes : {len(df.columns):,}")

    print("\nColonnes principales disponibles :")
    important_cols = [
        "Date",
        "HomeTeam",
        "AwayTeam",
        "FTHG",
        "FTAG",
        "FTR",
        "HG",
        "AG",
        "Res",
        "B365H",
        "B365D",
        "B365A",
        "AvgH",
        "AvgD",
        "AvgA",
    ]

    for col in important_cols:
        if col in df.columns:
            print(f"OK  - {col}")
        else:
            print(f"NON - {col}")

    print("\nNombre de lignes par championnat :")
    summary = (
        df.groupby(["league_code", "country", "division"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    print(summary.to_string(index=False))

    print("\nFichier créé :")
    print(OUTPUT_FILE)

    print("\nRapport d'ingestion :")
    print(INGESTION_REPORT)


if __name__ == "__main__":
    raw_df = build_raw_dataset()
    print_summary(raw_df)