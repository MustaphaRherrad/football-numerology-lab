from __future__ import annotations

import pandas as pd

from src.config import (
    FEATURES_DATA_DIR,
    TABLES_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity.parquet"

OUTPUT_TABLE = TABLES_DIR / "prior_affinity_bucket_analysis.csv"
OUTPUT_TABLE_BY_THRESHOLD = TABLES_DIR / "prior_affinity_bucket_analysis_by_threshold.csv"
OUTPUT_REPORT = DATA_REPORTS_DIR / "prior_affinity_signal_report.csv"


def make_bucket(series: pd.Series) -> pd.Series:
    """
    Buckets fixes pour interprétation stable.
    delta_affinity_prior = affinité home - affinité away.
    """
    bins = [-999, -0.60, -0.30, -0.10, 0.10, 0.30, 0.60, 999]
    labels = [
        "very_negative",
        "negative",
        "slightly_negative",
        "neutral",
        "slightly_positive",
        "positive",
        "very_positive",
    ]

    return pd.cut(series, bins=bins, labels=labels)


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    summary = (
        df.groupby(group_cols, observed=True)
        .agg(
            matches=("result", "count"),
            home_wins=("result", lambda x: (x == "H").sum()),
            draws=("result", lambda x: (x == "D").sum()),
            away_wins=("result", lambda x: (x == "A").sum()),
            avg_delta_affinity=("delta_affinity_prior", "mean"),
            avg_home_prior_matches=("home_prior_matches_on_num", "mean"),
            avg_away_prior_matches=("away_prior_matches_on_num", "mean"),
        )
        .reset_index()
    )

    summary["home_win_rate"] = summary["home_wins"] / summary["matches"]
    summary["draw_rate"] = summary["draws"] / summary["matches"]
    summary["away_win_rate"] = summary["away_wins"] / summary["matches"]

    # Export en pourcentage lisible
    pct_cols = ["home_win_rate", "draw_rate", "away_win_rate"]
    for col in pct_cols:
        summary[col] = (summary[col] * 100).round(3)

    numeric_cols = [
        "avg_delta_affinity",
        "avg_home_prior_matches",
        "avg_away_prior_matches",
    ]

    for col in numeric_cols:
        summary[col] = summary[col].round(4)

    return summary


def run_analysis() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)

    # On garde uniquement les matchs où le signal existe
    base = df[df["delta_affinity_prior"].notna()].copy()

    base["affinity_bucket"] = make_bucket(base["delta_affinity_prior"])

    # Analyse globale tous seuils confondus
    global_summary = summarize(base, ["affinity_bucket"])
    global_summary.to_csv(OUTPUT_TABLE, index=False, encoding="utf-8-sig")

    # Analyse par seuil de robustesse
    threshold_frames = []

    thresholds = [0, 5, 10, 20, 30]

    for threshold in thresholds:
        temp = base[
            (base["home_prior_matches_on_num"] >= threshold)
            & (base["away_prior_matches_on_num"] >= threshold)
        ].copy()

        if temp.empty:
            continue

        temp_summary = summarize(temp, ["affinity_bucket"])
        temp_summary["min_prior_matches_on_num"] = threshold
        threshold_frames.append(temp_summary)

    by_threshold = pd.concat(threshold_frames, ignore_index=True)
    by_threshold = by_threshold[
        [
            "min_prior_matches_on_num",
            "affinity_bucket",
            "matches",
            "home_wins",
            "draws",
            "away_wins",
            "home_win_rate",
            "draw_rate",
            "away_win_rate",
            "avg_delta_affinity",
            "avg_home_prior_matches",
            "avg_away_prior_matches",
        ]
    ]

    by_threshold.to_csv(OUTPUT_TABLE_BY_THRESHOLD, index=False, encoding="utf-8-sig")

    # Rapport général
    report = pd.DataFrame(
        [
            {"metric": "input_rows", "value": len(df)},
            {"metric": "rows_with_delta_affinity", "value": len(base)},
            {"metric": "rows_both_prior_ge_5", "value": int(((base["home_prior_matches_on_num"] >= 5) & (base["away_prior_matches_on_num"] >= 5)).sum())},
            {"metric": "rows_both_prior_ge_10", "value": int(((base["home_prior_matches_on_num"] >= 10) & (base["away_prior_matches_on_num"] >= 10)).sum())},
            {"metric": "rows_both_prior_ge_20", "value": int(((base["home_prior_matches_on_num"] >= 20) & (base["away_prior_matches_on_num"] >= 20)).sum())},
            {"metric": "global_home_win_rate_pct", "value": round((base["result"].eq("H").mean() * 100), 3)},
            {"metric": "global_draw_rate_pct", "value": round((base["result"].eq("D").mean() * 100), 3)},
            {"metric": "global_away_win_rate_pct", "value": round((base["result"].eq("A").mean() * 100), 3)},
        ]
    )

    report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")

    return global_summary, by_threshold, report


def print_summary(global_summary: pd.DataFrame, by_threshold: pd.DataFrame, report: pd.DataFrame) -> None:
    print("\nSignal prédictif delta_affinity_prior")
    print("=====================================")

    print("\nRapport général :")
    print(report.to_string(index=False))

    print("\nBuckets tous matchs avec delta disponible :")
    print(global_summary.to_string(index=False))

    print("\nBuckets avec seuil >= 10 matchs prior équipe × nombre :")
    subset_10 = by_threshold[by_threshold["min_prior_matches_on_num"] == 10]
    print(subset_10.to_string(index=False))

    print("\nBuckets avec seuil >= 20 matchs prior équipe × nombre :")
    subset_20 = by_threshold[by_threshold["min_prior_matches_on_num"] == 20]
    print(subset_20.to_string(index=False))

    print("\nFichiers créés :")
    print(OUTPUT_TABLE)
    print(OUTPUT_TABLE_BY_THRESHOLD)
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    global_summary_df, by_threshold_df, report_df = run_analysis()
    print_summary(global_summary_df, by_threshold_df, report_df)