from __future__ import annotations

import hashlib

import pandas as pd

from src.config import (
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


RAW_FILE = INTERIM_DATA_DIR / "matches_raw_all.parquet"
OUTPUT_FILE = PROCESSED_DATA_DIR / "matches_clean.parquet"
OUTPUT_SAMPLE = PROCESSED_DATA_DIR / "matches_clean_sample.csv"
CLEANING_REPORT = DATA_REPORTS_DIR / "cleaning_report.csv"
ISSUES_FILE = DATA_REPORTS_DIR / "cleaning_issues.csv"


def parse_dates(series: pd.Series) -> pd.Series:
    """
    Les dates football-data sont généralement en format jour/mois/année.
    On force dayfirst=True.
    """
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def to_numeric_int(series: pd.Series) -> pd.Series:
    """
    Convertit une série en numérique nullable Int64.
    """
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def normalize_text(series: pd.Series) -> pd.Series:
    """
    Nettoyage léger des textes.
    """
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )


def compute_points(result: pd.Series) -> tuple[pd.Series, pd.Series]:
    home_points = result.map({"H": 3, "D": 1, "A": 0}).astype("Int64")
    away_points = result.map({"H": 0, "D": 1, "A": 3}).astype("Int64")
    return home_points, away_points


def build_match_id(row: pd.Series) -> str:
    """
    Identifiant stable basé sur les infos principales.
    """
    raw = (
        f"{row['date']}|{row['league_code']}|{row['season']}|"
        f"{row['home_team']}|{row['away_team']}|"
        f"{row['home_goals']}|{row['away_goals']}"
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def clean_matches() -> pd.DataFrame:
    ensure_directories()

    raw = pd.read_parquet(RAW_FILE)

    initial_rows = len(raw)

    # Colonnes nécessaires
    required_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"]

    missing_cols = [col for col in required_cols if col not in raw.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans la base brute : {missing_cols}")

    df = pd.DataFrame()

    df["date"] = parse_dates(raw["Date"])
    df["season"] = normalize_text(raw["season"])
    df["season_start_year"] = to_numeric_int(raw["season_start_year"])
    df["season_code"] = normalize_text(raw["season_code"])
    df["league_code"] = normalize_text(raw["league_code"])
    df["country"] = normalize_text(raw["country"])
    df["division"] = normalize_text(raw["division"])

    df["home_team"] = normalize_text(raw["HomeTeam"])
    df["away_team"] = normalize_text(raw["AwayTeam"])

    df["home_goals"] = to_numeric_int(raw["FTHG"])
    df["away_goals"] = to_numeric_int(raw["FTAG"])

    df["result"] = normalize_text(raw["FTR"]).str.upper()

    df["source_file"] = normalize_text(raw["source_file"])
    df["source_status"] = normalize_text(raw["source_status"])
    df["read_encoding"] = normalize_text(raw["read_encoding"])

    # Garder les cotes principales si disponibles
    odds_cols = ["B365H", "B365D", "B365A", "AvgH", "AvgD", "AvgA", "MaxH", "MaxD", "MaxA"]

    for col in odds_cols:
        if col in raw.columns:
            df[col.lower()] = pd.to_numeric(raw[col], errors="coerce")

    # Supprimer les lignes invalides principales
    issue_rows = []

    def add_issue(mask: pd.Series, issue: str) -> None:
        if mask.any():
            temp = df.loc[mask].copy()
            temp["issue"] = issue
            issue_rows.append(temp)

    add_issue(df["date"].isna(), "missing_or_invalid_date")
    add_issue(df["home_team"].isna() | (df["home_team"] == ""), "missing_home_team")
    add_issue(df["away_team"].isna() | (df["away_team"] == ""), "missing_away_team")
    add_issue(df["home_goals"].isna(), "missing_home_goals")
    add_issue(df["away_goals"].isna(), "missing_away_goals")
    add_issue(~df["result"].isin(["H", "D", "A"]), "invalid_result")

    valid_mask = (
        df["date"].notna()
        & df["home_team"].notna()
        & df["away_team"].notna()
        & df["home_goals"].notna()
        & df["away_goals"].notna()
        & df["result"].isin(["H", "D", "A"])
    )

    df = df.loc[valid_mask].copy()

    # Vérifier cohérence résultat / score
    expected_result = pd.Series(index=df.index, dtype="string")
    expected_result[df["home_goals"] > df["away_goals"]] = "H"
    expected_result[df["home_goals"] == df["away_goals"]] = "D"
    expected_result[df["home_goals"] < df["away_goals"]] = "A"

    inconsistent_mask = df["result"] != expected_result

    if inconsistent_mask.any():
        temp = df.loc[inconsistent_mask].copy()
        temp["expected_result"] = expected_result.loc[inconsistent_mask]
        temp["issue"] = "result_score_inconsistency"
        issue_rows.append(temp)

    df = df.loc[~inconsistent_mask].copy()

    # Variables dérivées
    df["home_points"], df["away_points"] = compute_points(df["result"])
    df["total_goals"] = (df["home_goals"] + df["away_goals"]).astype("Int64")
    df["goal_diff"] = (df["home_goals"] - df["away_goals"]).astype("Int64")

    # Supprimer les doublons exacts sur l'identité du match
    before_dedup = len(df)

    dedup_subset = [
        "date",
        "league_code",
        "season",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "result",
    ]

    duplicates_mask = df.duplicated(subset=dedup_subset, keep="first")

    if duplicates_mask.any():
        temp = df.loc[duplicates_mask].copy()
        temp["issue"] = "duplicate_match"
        issue_rows.append(temp)

    df = df.drop_duplicates(subset=dedup_subset, keep="first").copy()

    # Identifiant final
    df["match_id"] = df.apply(build_match_id, axis=1)

    # Réordonner
    first_cols = [
        "match_id",
        "date",
        "season",
        "season_start_year",
        "season_code",
        "league_code",
        "country",
        "division",
        "home_team",
        "away_team",
        "home_goals",
        "away_goals",
        "result",
        "home_points",
        "away_points",
        "total_goals",
        "goal_diff",
    ]

    other_cols = [col for col in df.columns if col not in first_cols]
    df = df[first_cols + other_cols].sort_values(["date", "country", "league_code"]).reset_index(drop=True)

    # Sauvegardes
    df.to_parquet(OUTPUT_FILE, index=False)
    df.head(1000).to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    # Issues
    if issue_rows:
        issues = pd.concat(issue_rows, ignore_index=True, sort=False)
        issues.to_csv(ISSUES_FILE, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(columns=["issue"]).to_csv(ISSUES_FILE, index=False, encoding="utf-8-sig")

    # Rapport
    report = pd.DataFrame(
        [
            {"metric": "initial_raw_rows", "value": initial_rows},
            {"metric": "clean_rows", "value": len(df)},
            {"metric": "removed_rows", "value": initial_rows - len(df)},
            {"metric": "duplicates_removed", "value": before_dedup - len(df)},
            {"metric": "min_date", "value": str(df["date"].min())},
            {"metric": "max_date", "value": str(df["date"].max())},
            {"metric": "n_leagues", "value": df["league_code"].nunique()},
            {"metric": "n_teams_raw_names", "value": pd.concat([df["home_team"], df["away_team"]]).nunique()},
        ]
    )

    report.to_csv(CLEANING_REPORT, index=False, encoding="utf-8-sig")

    return df


def print_summary(df: pd.DataFrame) -> None:
    print("\nBase nettoyée")
    print("=============")
    print(f"Lignes : {len(df):,}")
    print(f"Colonnes : {len(df.columns):,}")
    print(f"Période : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"Championnats/divisions : {df['league_code'].nunique()}")
    print(f"Équipes différentes : {pd.concat([df['home_team'], df['away_team']]).nunique()}")

    print("\nDistribution des résultats :")
    print(df["result"].value_counts(normalize=True).mul(100).round(2).astype(str) + " %")

    print("\nLignes par championnat :")
    summary = (
        df.groupby(["league_code", "country", "division"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    print(summary.to_string(index=False))

    print("\nFichiers créés :")
    print(OUTPUT_FILE)
    print(OUTPUT_SAMPLE)
    print(CLEANING_REPORT)
    print(ISSUES_FILE)


if __name__ == "__main__":
    clean_df = clean_matches()
    print_summary(clean_df)