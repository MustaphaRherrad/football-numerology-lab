from __future__ import annotations

import pandas as pd

from src.config import (
    PROCESSED_DATA_DIR,
    FEATURES_DATA_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = PROCESSED_DATA_DIR / "matches_clean.parquet"
OUTPUT_FILE = FEATURES_DATA_DIR / "matches_with_date_features.parquet"
OUTPUT_SAMPLE = FEATURES_DATA_DIR / "matches_with_date_features_sample.csv"
REPORT_FILE = DATA_REPORTS_DIR / "date_numerology_features_report.csv"


MASTER_NUMBERS = {11, 22, 33}


def reduce_number(value: int, keep_master: bool = False) -> int:
    """
    Réduit un nombre en 1-9.
    Si keep_master=True, conserve 11, 22, 33 lorsqu'ils apparaissent.
    """
    if pd.isna(value):
        return pd.NA

    n = int(value)

    if keep_master and n in MASTER_NUMBERS:
        return n

    while n > 9:
        n = sum(int(digit) for digit in str(n))

        if keep_master and n in MASTER_NUMBERS:
            return n

    return n


def date_digit_sum(date_value: pd.Timestamp) -> int:
    """
    Somme tous les chiffres de la date au format ddmmyyyy.
    Exemple :
    06/06/2026 -> 0+6+0+6+2+0+2+6 = 22
    """
    digits = date_value.strftime("%d%m%Y")
    return sum(int(digit) for digit in digits)


def day_month_digit_sum(date_value: pd.Timestamp) -> int:
    """
    Somme uniquement les chiffres jour + mois.
    Exemple :
    06/06 -> 0+6+0+6 = 12
    """
    digits = date_value.strftime("%d%m")
    return sum(int(digit) for digit in digits)


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["year"] = df["date"].dt.year.astype("Int64")
    df["month"] = df["date"].dt.month.astype("Int64")
    df["day"] = df["date"].dt.day.astype("Int64")

    # Monday=0, Sunday=6
    df["weekday"] = df["date"].dt.weekday.astype("Int64")
    df["weekday_name"] = df["date"].dt.day_name()

    df["is_weekend"] = df["weekday"].isin([5, 6])

    # Variables numérologiques principales
    df["date_digits_sum"] = df["date"].apply(date_digit_sum).astype("Int64")
    df["date_num_1_9"] = df["date_digits_sum"].apply(
        lambda x: reduce_number(x, keep_master=False)
    ).astype("Int64")

    df["date_num_master"] = df["date_digits_sum"].apply(
        lambda x: reduce_number(x, keep_master=True)
    ).astype("Int64")

    # Variante secondaire : jour + mois uniquement
    df["day_month_digits_sum"] = df["date"].apply(day_month_digit_sum).astype("Int64")
    df["day_month_num_1_9"] = df["day_month_digits_sum"].apply(
        lambda x: reduce_number(x, keep_master=False)
    ).astype("Int64")

    return df


def build_features() -> pd.DataFrame:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)
    featured = add_date_features(df)

    featured.to_parquet(OUTPUT_FILE, index=False)
    featured.head(1000).to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    report_rows = []

    report_rows.append({"metric": "rows", "value": len(featured)})
    report_rows.append({"metric": "min_date", "value": str(featured["date"].min())})
    report_rows.append({"metric": "max_date", "value": str(featured["date"].max())})
    report_rows.append({"metric": "date_num_1_9_missing", "value": int(featured["date_num_1_9"].isna().sum())})
    report_rows.append({"metric": "date_num_master_missing", "value": int(featured["date_num_master"].isna().sum())})

    report = pd.DataFrame(report_rows)
    report.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

    return featured


def print_summary(df: pd.DataFrame) -> None:
    print("\nBase enrichie avec variables calendaires et numérologiques")
    print("=========================================================")
    print(f"Lignes : {len(df):,}")
    print(f"Colonnes : {len(df.columns):,}")

    print("\nDistribution date_num_1_9 :")
    print(df["date_num_1_9"].value_counts().sort_index())

    print("\nDistribution date_num_master :")
    print(df["date_num_master"].value_counts().sort_index())

    print("\nDistribution des résultats par date_num_1_9 :")
    result_by_num = (
        pd.crosstab(df["date_num_1_9"], df["result"], normalize="index")
        .mul(100)
        .round(2)
    )
    print(result_by_num)

    print("\nFichiers créés :")
    print(OUTPUT_FILE)
    print(OUTPUT_SAMPLE)
    print(REPORT_FILE)


if __name__ == "__main__":
    features_df = build_features()
    print_summary(features_df)