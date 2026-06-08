from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import CATALOG_DIR


CATALOG_FILE = CATALOG_DIR / "football_data_files.csv"


def inspect_catalog() -> None:
    catalog = pd.read_csv(CATALOG_FILE)

    print("\nAperçu du catalogue")
    print("===================")
    print(catalog.head())

    print("\nDimensions du catalogue")
    print("=======================")
    print(catalog.shape)

    print("\nRépartition des statuts")
    print("=======================")
    print(catalog["status"].value_counts(dropna=False))

    print("\nFichiers avec erreur de lecture")
    print("==============================")
    errors = catalog[catalog["status"] == "downloaded_but_read_error"].copy()

    if errors.empty:
        print("Aucun fichier avec erreur de lecture.")
    else:
        cols = [
            "season",
            "league_code",
            "country",
            "division",
            "local_path",
            "file_size_bytes",
            "error_message",
        ]
        print(errors[cols].to_string(index=False))

        output_file = CATALOG_DIR / "read_errors.csv"
        errors[cols].to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nExport des erreurs : {output_file}")

    print("\nFichiers non disponibles")
    print("========================")
    missing = catalog[catalog["status"] == "not_available"].copy()

    if missing.empty:
        print("Aucun fichier non disponible.")
    else:
        cols = [
            "season",
            "league_code",
            "country",
            "division",
            "download_url",
            "http_status",
            "error_message",
        ]
        print(missing[cols].to_string(index=False))

        output_file = CATALOG_DIR / "not_available.csv"
        missing[cols].to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nExport des fichiers non disponibles : {output_file}")

    print("\nTop fichiers par nombre de lignes")
    print("=================================")
    valid = catalog[catalog["n_rows"].notna()].copy()
    valid["n_rows"] = valid["n_rows"].astype(int)

    cols = ["season", "league_code", "country", "division", "n_rows", "n_columns"]
    print(valid.sort_values("n_rows", ascending=False)[cols].head(20).to_string(index=False))

    print("\nRésumé lignes par championnat")
    print("=============================")
    summary = (
        valid.groupby(["league_code", "country", "division"], dropna=False)
        .agg(
            files=("local_path", "count"),
            rows=("n_rows", "sum"),
            min_season=("season", "min"),
            max_season=("season", "max"),
        )
        .reset_index()
        .sort_values(["country", "league_code"])
    )

    print(summary.to_string(index=False))

    output_file = CATALOG_DIR / "collection_summary_by_league.csv"
    summary.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\nExport résumé championnats : {output_file}")


if __name__ == "__main__":
    inspect_catalog()