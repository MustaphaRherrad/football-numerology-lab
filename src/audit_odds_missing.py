from __future__ import annotations

import pandas as pd

from src.config import (
    FEATURES_DATA_DIR,
    TABLES_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity.parquet"

OUTPUT_ODDS_MISSING = TABLES_DIR / "odds_missing_audit.csv"
OUTPUT_ODDS_COVERAGE_BY_SEASON = TABLES_DIR / "odds_coverage_by_season.csv"
OUTPUT_ODDS_COVERAGE_BY_LEAGUE = TABLES_DIR / "odds_coverage_by_league.csv"
OUTPUT_REPORT = DATA_REPORTS_DIR / "odds_missing_report.csv"


# Colonnes 1X2 classiques connues dans football-data
ODDS_GROUPS = {
    "home": [
        "b365h", "bwh", "iwh", "lbh", "psh", "whh", "vch",
        "gbh", "sbh", "sjh", "bsh", "psch",
        "maxh", "avgh"
    ],
    "draw": [
        "b365d", "bwd", "iwd", "lbd", "psd", "whd", "vcd",
        "gbd", "sbd", "sjd", "bsd", "pscd",
        "maxd", "avgd"
    ],
    "away": [
        "b365a", "bwa", "iwa", "lba", "psa", "wha", "vca",
        "gba", "sba", "sja", "bsa", "psca",
        "maxa", "avga"
    ],
}


def get_existing_odds_columns(df: pd.DataFrame) -> dict[str, list[str]]:
    existing = {}

    for outcome, cols in ODDS_GROUPS.items():
        existing[outcome] = [col for col in cols if col in df.columns]

    return existing


def audit_individual_columns(df: pd.DataFrame, existing_cols: dict[str, list[str]]) -> pd.DataFrame:
    rows = []

    for outcome, cols in existing_cols.items():
        for col in cols:
            values = pd.to_numeric(df[col], errors="coerce")

            rows.append(
                {
                    "outcome": outcome,
                    "column": col,
                    "rows": len(df),
                    "non_missing": int(values.notna().sum()),
                    "missing": int(values.isna().sum()),
                    "coverage_pct": round(values.notna().mean() * 100, 3),
                    "min_value": values.min(),
                    "max_value": values.max(),
                }
            )

    return pd.DataFrame(rows).sort_values(["outcome", "coverage_pct"], ascending=[True, False])


def add_mean_odds_columns(df: pd.DataFrame, existing_cols: dict[str, list[str]]) -> pd.DataFrame:
    df = df.copy()

    for outcome, cols in existing_cols.items():
        numeric_frame = df[cols].apply(pd.to_numeric, errors="coerce")

        df[f"mean_odds_{outcome}"] = numeric_frame.mean(axis=1, skipna=True)
        df[f"n_odds_{outcome}"] = numeric_frame.notna().sum(axis=1)

    df["has_mean_odds_home"] = df["mean_odds_home"].notna()
    df["has_mean_odds_draw"] = df["mean_odds_draw"].notna()
    df["has_mean_odds_away"] = df["mean_odds_away"].notna()

    df["has_complete_mean_odds_1x2"] = (
        df["has_mean_odds_home"]
        & df["has_mean_odds_draw"]
        & df["has_mean_odds_away"]
    )

    df["n_odds_min_1x2"] = df[["n_odds_home", "n_odds_draw", "n_odds_away"]].min(axis=1)

    return df


def coverage_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "metric": "rows_total",
            "value": len(df),
        },
        {
            "metric": "rows_with_home_mean_odds",
            "value": int(df["has_mean_odds_home"].sum()),
        },
        {
            "metric": "rows_with_draw_mean_odds",
            "value": int(df["has_mean_odds_draw"].sum()),
        },
        {
            "metric": "rows_with_away_mean_odds",
            "value": int(df["has_mean_odds_away"].sum()),
        },
        {
            "metric": "rows_with_complete_mean_odds_1x2",
            "value": int(df["has_complete_mean_odds_1x2"].sum()),
        },
        {
            "metric": "coverage_complete_mean_odds_1x2_pct",
            "value": round(df["has_complete_mean_odds_1x2"].mean() * 100, 3),
        },
        {
            "metric": "rows_with_at_least_2_bookmakers_per_outcome",
            "value": int((df["n_odds_min_1x2"] >= 2).sum()),
        },
        {
            "metric": "coverage_at_least_2_bookmakers_per_outcome_pct",
            "value": round((df["n_odds_min_1x2"] >= 2).mean() * 100, 3),
        },
        {
            "metric": "rows_with_at_least_3_bookmakers_per_outcome",
            "value": int((df["n_odds_min_1x2"] >= 3).sum()),
        },
        {
            "metric": "coverage_at_least_3_bookmakers_per_outcome_pct",
            "value": round((df["n_odds_min_1x2"] >= 3).mean() * 100, 3),
        },
    ]

    return pd.DataFrame(rows)


def coverage_by_season(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby("season")
        .agg(
            matches=("match_id", "count"),
            complete_odds=("has_complete_mean_odds_1x2", "sum"),
            avg_n_bookmakers_home=("n_odds_home", "mean"),
            avg_n_bookmakers_draw=("n_odds_draw", "mean"),
            avg_n_bookmakers_away=("n_odds_away", "mean"),
        )
        .reset_index()
    )

    result["coverage_pct"] = (result["complete_odds"] / result["matches"] * 100).round(3)

    for col in ["avg_n_bookmakers_home", "avg_n_bookmakers_draw", "avg_n_bookmakers_away"]:
        result[col] = result[col].round(3)

    return result


def coverage_by_league(df: pd.DataFrame) -> pd.DataFrame:
    result = (
        df.groupby(["league_code", "country", "division"], dropna=False)
        .agg(
            matches=("match_id", "count"),
            complete_odds=("has_complete_mean_odds_1x2", "sum"),
            avg_n_bookmakers_home=("n_odds_home", "mean"),
            avg_n_bookmakers_draw=("n_odds_draw", "mean"),
            avg_n_bookmakers_away=("n_odds_away", "mean"),
        )
        .reset_index()
    )

    result["coverage_pct"] = (result["complete_odds"] / result["matches"] * 100).round(3)

    for col in ["avg_n_bookmakers_home", "avg_n_bookmakers_draw", "avg_n_bookmakers_away"]:
        result[col] = result[col].round(3)

    return result.sort_values("coverage_pct", ascending=False)


def run_audit() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)

    existing_cols = get_existing_odds_columns(df)

    print("\nColonnes de cotes détectées")
    print("===========================")
    for outcome, cols in existing_cols.items():
        print(f"{outcome}: {cols}")

    column_audit = audit_individual_columns(df, existing_cols)
    df_odds = add_mean_odds_columns(df, existing_cols)

    report = coverage_summary(df_odds)
    by_season = coverage_by_season(df_odds)
    by_league = coverage_by_league(df_odds)

    column_audit.to_csv(OUTPUT_ODDS_MISSING, index=False, encoding="utf-8-sig")
    by_season.to_csv(OUTPUT_ODDS_COVERAGE_BY_SEASON, index=False, encoding="utf-8-sig")
    by_league.to_csv(OUTPUT_ODDS_COVERAGE_BY_LEAGUE, index=False, encoding="utf-8-sig")
    report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")

    return column_audit, by_season, by_league, report


def print_summary(
    column_audit: pd.DataFrame,
    by_season: pd.DataFrame,
    by_league: pd.DataFrame,
    report: pd.DataFrame,
) -> None:
    print("\nRapport global cotes")
    print("====================")
    print(report.to_string(index=False))

    print("\nAudit colonnes individuelles")
    print("============================")
    print(column_audit.to_string(index=False))

    print("\nCouverture par saison")
    print("=====================")
    print(by_season.to_string(index=False))

    print("\nCouverture par championnat")
    print("==========================")
    print(by_league.to_string(index=False))

    print("\nFichiers créés :")
    print(OUTPUT_ODDS_MISSING)
    print(OUTPUT_ODDS_COVERAGE_BY_SEASON)
    print(OUTPUT_ODDS_COVERAGE_BY_LEAGUE)
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    column_audit_df, by_season_df, by_league_df, report_df = run_audit()
    print_summary(column_audit_df, by_season_df, by_league_df, report_df)