from __future__ import annotations

import pandas as pd

from src.config import (
    FEATURES_DATA_DIR,
    TABLES_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity_and_odds.parquet"

OUTPUT_TABLE = TABLES_DIR / "bookmaker_affinity_filter_analysis.csv"
OUTPUT_REPORT = DATA_REPORTS_DIR / "bookmaker_affinity_filter_report.csv"


def analyze_filters(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    thresholds = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]
    min_prior_thresholds = [0, 5, 10, 20]

    df = df[
        df["has_market_odds_1x2"]
        & df["bookmaker_pick_market"].notna()
        & df["delta_affinity_prior"].notna()
    ].copy()

    for min_prior in min_prior_thresholds:
        base = df[
            (df["home_prior_matches_on_num"] >= min_prior)
            & (df["away_prior_matches_on_num"] >= min_prior)
        ].copy()

        if base.empty:
            continue

        rows.append(
            {
                "min_prior_matches_on_num": min_prior,
                "filter_type": "bookmaker_all",
                "affinity_threshold": None,
                "selected_matches": len(base),
                "coverage_pct": 100.0,
                "accuracy": base["bookmaker_pick_market_correct"].mean() * 100,
                "home_pick_share_pct": base["bookmaker_pick_market"].eq("H").mean() * 100,
                "draw_pick_share_pct": base["bookmaker_pick_market"].eq("D").mean() * 100,
                "away_pick_share_pct": base["bookmaker_pick_market"].eq("A").mean() * 100,
            }
        )

        for threshold in thresholds:
            aligned = base[
                (
                    (base["bookmaker_pick_market"] == "H")
                    & (base["delta_affinity_prior"] >= threshold)
                )
                |
                (
                    (base["bookmaker_pick_market"] == "A")
                    & (base["delta_affinity_prior"] <= -threshold)
                )
            ].copy()

            contradicted = base[
                (
                    (base["bookmaker_pick_market"] == "H")
                    & (base["delta_affinity_prior"] <= -threshold)
                )
                |
                (
                    (base["bookmaker_pick_market"] == "A")
                    & (base["delta_affinity_prior"] >= threshold)
                )
            ].copy()

            if len(aligned) > 0:
                rows.append(
                    {
                        "min_prior_matches_on_num": min_prior,
                        "filter_type": "bookmaker_aligned_with_affinity",
                        "affinity_threshold": threshold,
                        "selected_matches": len(aligned),
                        "coverage_pct": len(aligned) / len(base) * 100,
                        "accuracy": aligned["bookmaker_pick_market_correct"].mean() * 100,
                        "home_pick_share_pct": aligned["bookmaker_pick_market"].eq("H").mean() * 100,
                        "draw_pick_share_pct": aligned["bookmaker_pick_market"].eq("D").mean() * 100,
                        "away_pick_share_pct": aligned["bookmaker_pick_market"].eq("A").mean() * 100,
                    }
                )

            if len(contradicted) > 0:
                rows.append(
                    {
                        "min_prior_matches_on_num": min_prior,
                        "filter_type": "bookmaker_contradicted_by_affinity",
                        "affinity_threshold": threshold,
                        "selected_matches": len(contradicted),
                        "coverage_pct": len(contradicted) / len(base) * 100,
                        "accuracy": contradicted["bookmaker_pick_market_correct"].mean() * 100,
                        "home_pick_share_pct": contradicted["bookmaker_pick_market"].eq("H").mean() * 100,
                        "draw_pick_share_pct": contradicted["bookmaker_pick_market"].eq("D").mean() * 100,
                        "away_pick_share_pct": contradicted["bookmaker_pick_market"].eq("A").mean() * 100,
                    }
                )

    result = pd.DataFrame(rows)

    numeric_cols = [
        "coverage_pct",
        "accuracy",
        "home_pick_share_pct",
        "draw_pick_share_pct",
        "away_pick_share_pct",
    ]

    for col in numeric_cols:
        result[col] = result[col].round(3)

    return result


def run_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)

    valid = df[
        df["has_market_odds_1x2"]
        & df["bookmaker_pick_market"].notna()
        & df["delta_affinity_prior"].notna()
    ].copy()

    analysis = analyze_filters(df)
    analysis.to_csv(OUTPUT_TABLE, index=False, encoding="utf-8-sig")

    report = pd.DataFrame(
        [
            {"metric": "rows_input", "value": len(df)},
            {"metric": "rows_valid_for_filter_test", "value": len(valid)},
            {"metric": "bookmaker_market_accuracy_pct", "value": round(valid["bookmaker_pick_market_correct"].mean() * 100, 3)},
            {"metric": "home_pick_share_pct", "value": round(valid["bookmaker_pick_market"].eq("H").mean() * 100, 3)},
            {"metric": "draw_pick_share_pct", "value": round(valid["bookmaker_pick_market"].eq("D").mean() * 100, 3)},
            {"metric": "away_pick_share_pct", "value": round(valid["bookmaker_pick_market"].eq("A").mean() * 100, 3)},
        ]
    )

    report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")

    return analysis, report


def print_summary(analysis: pd.DataFrame, report: pd.DataFrame) -> None:
    print("\nFiltre bookmaker + affinité")
    print("===========================")

    print("\nRapport :")
    print(report.to_string(index=False))

    print("\nSeuil prior >= 10 :")
    subset_10 = analysis[analysis["min_prior_matches_on_num"] == 10].copy()
    print(subset_10.to_string(index=False))

    print("\nSeuil prior >= 20 :")
    subset_20 = analysis[analysis["min_prior_matches_on_num"] == 20].copy()
    print(subset_20.to_string(index=False))

    print("\nFichiers créés :")
    print(OUTPUT_TABLE)
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    analysis_df, report_df = run_analysis()
    print_summary(analysis_df, report_df)