from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import CATALOG_DIR


CATALOG_FILE = CATALOG_DIR / "football_data_files.csv"


READ_ATTEMPTS = [
    {"encoding": "utf-8", "on_bad_lines": "error"},
    {"encoding": "utf-8-sig", "on_bad_lines": "skip"},
    {"encoding": "latin1", "on_bad_lines": "skip"},
    {"encoding": "cp1252", "on_bad_lines": "skip"},
]


def try_read_file(file_path: Path) -> dict:
    for params in READ_ATTEMPTS:
        try:
            df = pd.read_csv(file_path, **params)

            return {
                "read_status": "ok",
                "encoding": params["encoding"],
                "on_bad_lines": params["on_bad_lines"],
                "n_rows": len(df),
                "n_columns": len(df.columns),
                "columns": " | ".join(df.columns.astype(str).tolist()[:20]),
                "error": None,
            }

        except Exception as exc:
            last_error = str(exc)

    return {
        "read_status": "failed",
        "encoding": None,
        "on_bad_lines": None,
        "n_rows": None,
        "n_columns": None,
        "columns": None,
        "error": last_error,
    }


def main() -> None:
    catalog = pd.read_csv(CATALOG_FILE)

    errors = catalog[catalog["status"] == "downloaded_but_read_error"].copy()

    results = []

    for _, row in errors.iterrows():
        file_path = Path(row["local_path"])
        test = try_read_file(file_path)

        results.append(
            {
                "season": row["season"],
                "league_code": row["league_code"],
                "country": row["country"],
                "division": row["division"],
                "local_path": row["local_path"],
                "original_error": row["error_message"],
                **test,
            }
        )

    result_df = pd.DataFrame(results)

    output_file = CATALOG_DIR / "read_errors_recovery_test.csv"
    result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print("\nTest de récupération des fichiers en erreur")
    print("==========================================")
    print(result_df["read_status"].value_counts(dropna=False))

    if not result_df.empty:
        print("\nAperçu :")
        cols = [
            "season",
            "league_code",
            "read_status",
            "encoding",
            "on_bad_lines",
            "n_rows",
            "n_columns",
            "error",
        ]
        print(result_df[cols].to_string(index=False))

    print(f"\nExport : {output_file}")


if __name__ == "__main__":
    main()