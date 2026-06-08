from __future__ import annotations

import pandas as pd

from src.config import (
    FEATURES_DATA_DIR,
    TABLES_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_date_features.parquet"

OUTPUT_TABLE = TABLES_DIR / "team_date_num_affinity.csv"
OUTPUT_TOP_POSITIVE = TABLES_DIR / "team_date_num_top_positive_affinities.csv"
OUTPUT_TOP_NEGATIVE = TABLES_DIR / "team_date_num_top_negative_affinities.csv"
OUTPUT_REPORT = DATA_REPORTS_DIR / "team_date_num_affinity_report.csv"


def build_team_match_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforme la table match en table équipe-match.

    Une ligne match devient deux lignes :
    - une pour l'équipe domicile
    - une pour l'équipe extérieure
    """

    home = pd.DataFrame(
        {
            "match_id": df["match_id"],
            "date": df["date"],
            "season": df["season"],
            "season_start_year": df["season_start_year"],
            "league_code": df["league_code"],
            "country": df["country"],
            "division": df["division"],
            "team": df["home_team"],
            "opponent": df["away_team"],
            "venue": "home",
            "date_num_1_9": df["date_num_1_9"],
            "goals_for": df["home_goals"],
            "goals_against": df["away_goals"],
            "points": df["home_points"],
        }
    )

    away = pd.DataFrame(
        {
            "match_id": df["match_id"],
            "date": df["date"],
            "season": df["season"],
            "season_start_year": df["season_start_year"],
            "league_code": df["league_code"],
            "country": df["country"],
            "division": df["division"],
            "team": df["away_team"],
            "opponent": df["home_team"],
            "venue": "away",
            "date_num_1_9": df["date_num_1_9"],
            "goals_for": df["away_goals"],
            "goals_against": df["home_goals"],
            "points": df["away_points"],
        }
    )

    long_df = pd.concat([home, away], ignore_index=True)

    long_df["goal_diff"] = long_df["goals_for"] - long_df["goals_against"]
    long_df["win"] = (long_df["points"] == 3).astype(int)
    long_df["draw"] = (long_df["points"] == 1).astype(int)
    long_df["loss"] = (long_df["points"] == 0).astype(int)

    return long_df


def classify_sample_size(matches: int) -> str:
    if matches < 20:
        return "very_fragile"
    if matches < 50:
        return "fragile"
    if matches < 100:
        return "usable"
    return "strong"


def build_affinity_table(long_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule l'affinité équipe × nombre de date.
    """

    # Moyenne globale par équipe
    team_global = (
        long_df.groupby("team")
        .agg(
            team_total_matches=("match_id", "count"),
            team_global_points_per_match=("points", "mean"),
            team_global_win_rate=("win", "mean"),
            team_global_goal_diff_avg=("goal_diff", "mean"),
        )
        .reset_index()
    )

    # Performance par équipe et nombre
    affinity = (
        long_df.groupby(["team", "date_num_1_9"])
        .agg(
            matches=("match_id", "count"),
            points_per_match=("points", "mean"),
            win_rate=("win", "mean"),
            draw_rate=("draw", "mean"),
            loss_rate=("loss", "mean"),
            goal_diff_avg=("goal_diff", "mean"),
        )
        .reset_index()
    )

    affinity = affinity.merge(team_global, on="team", how="left")

    affinity["delta_points_vs_team_avg"] = (
        affinity["points_per_match"] - affinity["team_global_points_per_match"]
    )

    affinity["delta_win_rate_vs_team_avg"] = (
        affinity["win_rate"] - affinity["team_global_win_rate"]
    )

    affinity["delta_goal_diff_vs_team_avg"] = (
        affinity["goal_diff_avg"] - affinity["team_global_goal_diff_avg"]
    )

    affinity["sample_quality"] = affinity["matches"].apply(classify_sample_size)

    # Score simple : delta pondéré par la taille de l'échantillon.
    # Ce n'est pas encore un test statistique, juste un indicateur de tri.
    affinity["signal_strength"] = affinity["delta_points_vs_team_avg"] * (
        affinity["matches"] ** 0.5
    )

    # Arrondis pour export lisible
    numeric_cols = [
        "points_per_match",
        "win_rate",
        "draw_rate",
        "loss_rate",
        "goal_diff_avg",
        "team_global_points_per_match",
        "team_global_win_rate",
        "team_global_goal_diff_avg",
        "delta_points_vs_team_avg",
        "delta_win_rate_vs_team_avg",
        "delta_goal_diff_vs_team_avg",
        "signal_strength",
    ]

    for col in numeric_cols:
        affinity[col] = affinity[col].round(4)

    return affinity.sort_values(
        ["sample_quality", "signal_strength"], ascending=[True, False]
    )


def build_analysis() -> pd.DataFrame:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)

    long_df = build_team_match_long(df)
    affinity = build_affinity_table(long_df)

    affinity.to_csv(OUTPUT_TABLE, index=False, encoding="utf-8-sig")

    # Pour éviter les faux signaux, on sort surtout les cas avec au moins 50 matchs.
    reliable = affinity[affinity["matches"] >= 50].copy()

    top_positive = reliable.sort_values("signal_strength", ascending=False).head(50)
    top_negative = reliable.sort_values("signal_strength", ascending=True).head(50)

    top_positive.to_csv(OUTPUT_TOP_POSITIVE, index=False, encoding="utf-8-sig")
    top_negative.to_csv(OUTPUT_TOP_NEGATIVE, index=False, encoding="utf-8-sig")

    report = pd.DataFrame(
        [
            {"metric": "team_match_rows", "value": len(long_df)},
            {"metric": "unique_teams", "value": long_df["team"].nunique()},
            {"metric": "affinity_rows", "value": len(affinity)},
            {"metric": "affinity_rows_matches_ge_20", "value": int((affinity["matches"] >= 20).sum())},
            {"metric": "affinity_rows_matches_ge_50", "value": int((affinity["matches"] >= 50).sum())},
            {"metric": "affinity_rows_matches_ge_100", "value": int((affinity["matches"] >= 100).sum())},
            {"metric": "max_matches_team_num", "value": int(affinity["matches"].max())},
            {"metric": "min_matches_team_num", "value": int(affinity["matches"].min())},
        ]
    )

    report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")

    return affinity


def print_summary(affinity: pd.DataFrame) -> None:
    print("\nAnalyse équipe × nombre de date")
    print("================================")
    print(f"Lignes d'affinité : {len(affinity):,}")
    print(f"Équipes : {affinity['team'].nunique():,}")

    print("\nQualité des échantillons :")
    print(affinity["sample_quality"].value_counts())

    reliable = affinity[affinity["matches"] >= 50].copy()

    print("\nTop affinités positives, minimum 50 matchs :")
    cols = [
        "team",
        "date_num_1_9",
        "matches",
        "points_per_match",
        "team_global_points_per_match",
        "delta_points_vs_team_avg",
        "win_rate",
        "signal_strength",
    ]
    print(reliable.sort_values("signal_strength", ascending=False)[cols].head(20).to_string(index=False))

    print("\nTop affinités négatives, minimum 50 matchs :")
    print(reliable.sort_values("signal_strength", ascending=True)[cols].head(20).to_string(index=False))

    print("\nFichiers créés :")
    print(OUTPUT_TABLE)
    print(OUTPUT_TOP_POSITIVE)
    print(OUTPUT_TOP_NEGATIVE)
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    affinity_df = build_analysis()
    print_summary(affinity_df)