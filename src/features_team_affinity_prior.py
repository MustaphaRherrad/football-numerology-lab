from __future__ import annotations

from collections import defaultdict

import pandas as pd
from tqdm import tqdm

from src.config import (
    FEATURES_DATA_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_date_features.parquet"
OUTPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity.parquet"
OUTPUT_SAMPLE = FEATURES_DATA_DIR / "matches_with_prior_affinity_sample.csv"
REPORT_FILE = DATA_REPORTS_DIR / "prior_affinity_features_report.csv"


def safe_divide(numerator: float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def build_prior_affinity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les affinités équipe × date_num uniquement à partir du passé.

    On parcourt les matchs dans l'ordre chronologique.
    Pour chaque match :
      1. On lit les stats historiques disponibles avant ce match.
      2. On crée les variables prior.
      3. On met à jour l'historique avec le résultat du match.
    """

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["date", "country", "league_code", "home_team", "away_team"]
    ).reset_index(drop=True)

    # Historique par équipe tous nombres confondus
    team_total_matches = defaultdict(int)
    team_total_points = defaultdict(float)
    team_total_goal_diff = defaultdict(float)

    # Historique par équipe et nombre de date
    team_num_matches = defaultdict(int)
    team_num_points = defaultdict(float)
    team_num_goal_diff = defaultdict(float)

    rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Calcul affinités prior"):
        home_team = row["home_team"]
        away_team = row["away_team"]
        date_num = int(row["date_num_1_9"])

        home_key = (home_team, date_num)
        away_key = (away_team, date_num)

        # Historique global équipe avant match
        home_global_matches = team_total_matches[home_team]
        away_global_matches = team_total_matches[away_team]

        home_global_ppm = safe_divide(team_total_points[home_team], home_global_matches)
        away_global_ppm = safe_divide(team_total_points[away_team], away_global_matches)

        home_global_gd = safe_divide(team_total_goal_diff[home_team], home_global_matches)
        away_global_gd = safe_divide(team_total_goal_diff[away_team], away_global_matches)

        # Historique équipe × nombre avant match
        home_num_matches = team_num_matches[home_key]
        away_num_matches = team_num_matches[away_key]

        home_num_ppm = safe_divide(team_num_points[home_key], home_num_matches)
        away_num_ppm = safe_divide(team_num_points[away_key], away_num_matches)

        home_num_gd = safe_divide(team_num_goal_diff[home_key], home_num_matches)
        away_num_gd = safe_divide(team_num_goal_diff[away_key], away_num_matches)

        # Affinités = performance sur ce nombre - performance globale équipe
        if home_num_ppm is not None and home_global_ppm is not None:
            home_affinity_prior = home_num_ppm - home_global_ppm
        else:
            home_affinity_prior = None

        if away_num_ppm is not None and away_global_ppm is not None:
            away_affinity_prior = away_num_ppm - away_global_ppm
        else:
            away_affinity_prior = None

        if home_affinity_prior is not None and away_affinity_prior is not None:
            delta_affinity_prior = home_affinity_prior - away_affinity_prior
        else:
            delta_affinity_prior = None

        # Même logique en goal diff
        if home_num_gd is not None and home_global_gd is not None:
            home_gd_affinity_prior = home_num_gd - home_global_gd
        else:
            home_gd_affinity_prior = None

        if away_num_gd is not None and away_global_gd is not None:
            away_gd_affinity_prior = away_num_gd - away_global_gd
        else:
            away_gd_affinity_prior = None

        if home_gd_affinity_prior is not None and away_gd_affinity_prior is not None:
            delta_gd_affinity_prior = home_gd_affinity_prior - away_gd_affinity_prior
        else:
            delta_gd_affinity_prior = None

        rows.append(
            {
                "match_id": row["match_id"],
                "home_prior_total_matches": home_global_matches,
                "away_prior_total_matches": away_global_matches,
                "home_prior_matches_on_num": home_num_matches,
                "away_prior_matches_on_num": away_num_matches,
                "home_prior_global_ppm": home_global_ppm,
                "away_prior_global_ppm": away_global_ppm,
                "home_prior_num_ppm": home_num_ppm,
                "away_prior_num_ppm": away_num_ppm,
                "home_affinity_prior": home_affinity_prior,
                "away_affinity_prior": away_affinity_prior,
                "delta_affinity_prior": delta_affinity_prior,
                "home_prior_global_goal_diff": home_global_gd,
                "away_prior_global_goal_diff": away_global_gd,
                "home_prior_num_goal_diff": home_num_gd,
                "away_prior_num_goal_diff": away_num_gd,
                "home_gd_affinity_prior": home_gd_affinity_prior,
                "away_gd_affinity_prior": away_gd_affinity_prior,
                "delta_gd_affinity_prior": delta_gd_affinity_prior,
            }
        )

        # Mise à jour APRÈS avoir calculé les variables prior
        home_points = int(row["home_points"])
        away_points = int(row["away_points"])

        home_goal_diff = int(row["goal_diff"])
        away_goal_diff = -home_goal_diff

        team_total_matches[home_team] += 1
        team_total_points[home_team] += home_points
        team_total_goal_diff[home_team] += home_goal_diff

        team_total_matches[away_team] += 1
        team_total_points[away_team] += away_points
        team_total_goal_diff[away_team] += away_goal_diff

        team_num_matches[home_key] += 1
        team_num_points[home_key] += home_points
        team_num_goal_diff[home_key] += home_goal_diff

        team_num_matches[away_key] += 1
        team_num_points[away_key] += away_points
        team_num_goal_diff[away_key] += away_goal_diff

    prior = pd.DataFrame(rows)

    enriched = df.merge(prior, on="match_id", how="left")

    numeric_cols = [
        "home_prior_global_ppm",
        "away_prior_global_ppm",
        "home_prior_num_ppm",
        "away_prior_num_ppm",
        "home_affinity_prior",
        "away_affinity_prior",
        "delta_affinity_prior",
        "home_prior_global_goal_diff",
        "away_prior_global_goal_diff",
        "home_prior_num_goal_diff",
        "away_prior_num_goal_diff",
        "home_gd_affinity_prior",
        "away_gd_affinity_prior",
        "delta_gd_affinity_prior",
    ]

    for col in numeric_cols:
        enriched[col] = enriched[col].astype(float).round(6)

    return enriched


def build_dataset() -> pd.DataFrame:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)
    enriched = build_prior_affinity_features(df)

    enriched.to_parquet(OUTPUT_FILE, index=False)
    enriched.head(1000).to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    report = pd.DataFrame(
        [
            {"metric": "rows", "value": len(enriched)},
            {"metric": "delta_affinity_available", "value": int(enriched["delta_affinity_prior"].notna().sum())},
            {"metric": "delta_affinity_missing", "value": int(enriched["delta_affinity_prior"].isna().sum())},
            {"metric": "matches_home_num_ge_5", "value": int((enriched["home_prior_matches_on_num"] >= 5).sum())},
            {"metric": "matches_away_num_ge_5", "value": int((enriched["away_prior_matches_on_num"] >= 5).sum())},
            {"metric": "matches_both_num_ge_5", "value": int(((enriched["home_prior_matches_on_num"] >= 5) & (enriched["away_prior_matches_on_num"] >= 5)).sum())},
            {"metric": "matches_both_num_ge_10", "value": int(((enriched["home_prior_matches_on_num"] >= 10) & (enriched["away_prior_matches_on_num"] >= 10)).sum())},
            {"metric": "matches_both_num_ge_20", "value": int(((enriched["home_prior_matches_on_num"] >= 20) & (enriched["away_prior_matches_on_num"] >= 20)).sum())},
        ]
    )

    report.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

    return enriched


def print_summary(df: pd.DataFrame) -> None:
    print("\nDataset avec affinités historiques prior")
    print("========================================")
    print(f"Lignes : {len(df):,}")
    print(f"Colonnes : {len(df.columns):,}")

    print("\nDisponibilité delta_affinity_prior :")
    print(df["delta_affinity_prior"].notna().value_counts())

    print("\nSeuils d'historique équipe × nombre :")
    both_5 = ((df["home_prior_matches_on_num"] >= 5) & (df["away_prior_matches_on_num"] >= 5)).sum()
    both_10 = ((df["home_prior_matches_on_num"] >= 10) & (df["away_prior_matches_on_num"] >= 10)).sum()
    both_20 = ((df["home_prior_matches_on_num"] >= 20) & (df["away_prior_matches_on_num"] >= 20)).sum()

    print(f"Home et Away ont au moins 5 matchs prior sur ce nombre  : {both_5:,}")
    print(f"Home et Away ont au moins 10 matchs prior sur ce nombre : {both_10:,}")
    print(f"Home et Away ont au moins 20 matchs prior sur ce nombre : {both_20:,}")

    print("\nRésumé delta_affinity_prior :")
    print(df["delta_affinity_prior"].describe())

    print("\nFichiers créés :")
    print(OUTPUT_FILE)
    print(OUTPUT_SAMPLE)
    print(REPORT_FILE)


if __name__ == "__main__":
    enriched_df = build_dataset()
    print_summary(enriched_df)