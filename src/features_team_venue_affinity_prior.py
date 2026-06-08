from __future__ import annotations

from collections import defaultdict

import pandas as pd
from tqdm import tqdm

from src.config import (
    FEATURES_DATA_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity_and_odds.parquet"
OUTPUT_FILE = FEATURES_DATA_DIR / "matches_with_venue_prior_affinity.parquet"
OUTPUT_SAMPLE = FEATURES_DATA_DIR / "matches_with_venue_prior_affinity_sample.csv"
REPORT_FILE = DATA_REPORTS_DIR / "venue_prior_affinity_features_report.csv"


def safe_divide(numerator: float, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def build_venue_prior_affinity_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["date", "country", "league_code", "home_team", "away_team"]
    ).reset_index(drop=True)

    # Historique par équipe + lieu global
    # clé : (team, venue)
    team_venue_matches = defaultdict(int)
    team_venue_points = defaultdict(float)
    team_venue_goal_diff = defaultdict(float)

    # Historique par équipe + lieu + nombre de date
    # clé : (team, venue, date_num)
    team_venue_num_matches = defaultdict(int)
    team_venue_num_points = defaultdict(float)
    team_venue_num_goal_diff = defaultdict(float)

    rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Calcul affinités venue prior"):
        home_team = row["home_team"]
        away_team = row["away_team"]
        date_num = int(row["date_num_1_9"])

        home_venue_key = (home_team, "home")
        away_venue_key = (away_team, "away")

        home_venue_num_key = (home_team, "home", date_num)
        away_venue_num_key = (away_team, "away", date_num)

        # Historique global à domicile de l'équipe domicile
        home_prior_home_matches = team_venue_matches[home_venue_key]
        home_prior_home_ppm = safe_divide(
            team_venue_points[home_venue_key],
            home_prior_home_matches,
        )
        home_prior_home_gd = safe_divide(
            team_venue_goal_diff[home_venue_key],
            home_prior_home_matches,
        )

        # Historique global à l'extérieur de l'équipe extérieure
        away_prior_away_matches = team_venue_matches[away_venue_key]
        away_prior_away_ppm = safe_divide(
            team_venue_points[away_venue_key],
            away_prior_away_matches,
        )
        away_prior_away_gd = safe_divide(
            team_venue_goal_diff[away_venue_key],
            away_prior_away_matches,
        )

        # Historique domicile + nombre pour home_team
        home_prior_home_matches_on_num = team_venue_num_matches[home_venue_num_key]
        home_prior_home_num_ppm = safe_divide(
            team_venue_num_points[home_venue_num_key],
            home_prior_home_matches_on_num,
        )
        home_prior_home_num_gd = safe_divide(
            team_venue_num_goal_diff[home_venue_num_key],
            home_prior_home_matches_on_num,
        )

        # Historique extérieur + nombre pour away_team
        away_prior_away_matches_on_num = team_venue_num_matches[away_venue_num_key]
        away_prior_away_num_ppm = safe_divide(
            team_venue_num_points[away_venue_num_key],
            away_prior_away_matches_on_num,
        )
        away_prior_away_num_gd = safe_divide(
            team_venue_num_goal_diff[away_venue_num_key],
            away_prior_away_matches_on_num,
        )

        # Affinités venue = performance sur ce nombre à ce lieu - performance globale à ce lieu
        if home_prior_home_num_ppm is not None and home_prior_home_ppm is not None:
            home_venue_affinity_prior = home_prior_home_num_ppm - home_prior_home_ppm
        else:
            home_venue_affinity_prior = None

        if away_prior_away_num_ppm is not None and away_prior_away_ppm is not None:
            away_venue_affinity_prior = away_prior_away_num_ppm - away_prior_away_ppm
        else:
            away_venue_affinity_prior = None

        if home_venue_affinity_prior is not None and away_venue_affinity_prior is not None:
            delta_venue_affinity_prior = home_venue_affinity_prior - away_venue_affinity_prior
        else:
            delta_venue_affinity_prior = None

        # Même logique en goal diff
        if home_prior_home_num_gd is not None and home_prior_home_gd is not None:
            home_venue_gd_affinity_prior = home_prior_home_num_gd - home_prior_home_gd
        else:
            home_venue_gd_affinity_prior = None

        if away_prior_away_num_gd is not None and away_prior_away_gd is not None:
            away_venue_gd_affinity_prior = away_prior_away_num_gd - away_prior_away_gd
        else:
            away_venue_gd_affinity_prior = None

        if home_venue_gd_affinity_prior is not None and away_venue_gd_affinity_prior is not None:
            delta_venue_gd_affinity_prior = (
                home_venue_gd_affinity_prior - away_venue_gd_affinity_prior
            )
        else:
            delta_venue_gd_affinity_prior = None

        rows.append(
            {
                "match_id": row["match_id"],

                "home_prior_home_matches": home_prior_home_matches,
                "away_prior_away_matches": away_prior_away_matches,
                "home_prior_home_matches_on_num": home_prior_home_matches_on_num,
                "away_prior_away_matches_on_num": away_prior_away_matches_on_num,

                "home_prior_home_ppm": home_prior_home_ppm,
                "away_prior_away_ppm": away_prior_away_ppm,
                "home_prior_home_num_ppm": home_prior_home_num_ppm,
                "away_prior_away_num_ppm": away_prior_away_num_ppm,

                "home_venue_affinity_prior": home_venue_affinity_prior,
                "away_venue_affinity_prior": away_venue_affinity_prior,
                "delta_venue_affinity_prior": delta_venue_affinity_prior,

                "home_prior_home_goal_diff": home_prior_home_gd,
                "away_prior_away_goal_diff": away_prior_away_gd,
                "home_prior_home_num_goal_diff": home_prior_home_num_gd,
                "away_prior_away_num_goal_diff": away_prior_away_num_gd,

                "home_venue_gd_affinity_prior": home_venue_gd_affinity_prior,
                "away_venue_gd_affinity_prior": away_venue_gd_affinity_prior,
                "delta_venue_gd_affinity_prior": delta_venue_gd_affinity_prior,
            }
        )

        # Mise à jour APRÈS calcul des variables prior
        home_points = int(row["home_points"])
        away_points = int(row["away_points"])

        home_goal_diff = int(row["goal_diff"])
        away_goal_diff = -home_goal_diff

        # home_team à domicile
        team_venue_matches[home_venue_key] += 1
        team_venue_points[home_venue_key] += home_points
        team_venue_goal_diff[home_venue_key] += home_goal_diff

        team_venue_num_matches[home_venue_num_key] += 1
        team_venue_num_points[home_venue_num_key] += home_points
        team_venue_num_goal_diff[home_venue_num_key] += home_goal_diff

        # away_team à l'extérieur
        team_venue_matches[away_venue_key] += 1
        team_venue_points[away_venue_key] += away_points
        team_venue_goal_diff[away_venue_key] += away_goal_diff

        team_venue_num_matches[away_venue_num_key] += 1
        team_venue_num_points[away_venue_num_key] += away_points
        team_venue_num_goal_diff[away_venue_num_key] += away_goal_diff

    prior = pd.DataFrame(rows)

    enriched = df.merge(prior, on="match_id", how="left")

    numeric_cols = [
        "home_prior_home_ppm",
        "away_prior_away_ppm",
        "home_prior_home_num_ppm",
        "away_prior_away_num_ppm",
        "home_venue_affinity_prior",
        "away_venue_affinity_prior",
        "delta_venue_affinity_prior",
        "home_prior_home_goal_diff",
        "away_prior_away_goal_diff",
        "home_prior_home_num_goal_diff",
        "away_prior_away_num_goal_diff",
        "home_venue_gd_affinity_prior",
        "away_venue_gd_affinity_prior",
        "delta_venue_gd_affinity_prior",
    ]

    for col in numeric_cols:
        enriched[col] = enriched[col].astype(float).round(6)

    return enriched


def build_dataset() -> pd.DataFrame:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)
    enriched = build_venue_prior_affinity_features(df)

    enriched.to_parquet(OUTPUT_FILE, index=False)
    enriched.head(1000).to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    report = pd.DataFrame(
        [
            {"metric": "rows", "value": len(enriched)},
            {"metric": "delta_venue_affinity_available", "value": int(enriched["delta_venue_affinity_prior"].notna().sum())},
            {"metric": "delta_venue_affinity_missing", "value": int(enriched["delta_venue_affinity_prior"].isna().sum())},
            {"metric": "matches_both_venue_num_ge_3", "value": int(((enriched["home_prior_home_matches_on_num"] >= 3) & (enriched["away_prior_away_matches_on_num"] >= 3)).sum())},
            {"metric": "matches_both_venue_num_ge_5", "value": int(((enriched["home_prior_home_matches_on_num"] >= 5) & (enriched["away_prior_away_matches_on_num"] >= 5)).sum())},
            {"metric": "matches_both_venue_num_ge_10", "value": int(((enriched["home_prior_home_matches_on_num"] >= 10) & (enriched["away_prior_away_matches_on_num"] >= 10)).sum())},
            {"metric": "matches_both_venue_num_ge_20", "value": int(((enriched["home_prior_home_matches_on_num"] >= 20) & (enriched["away_prior_away_matches_on_num"] >= 20)).sum())},
        ]
    )

    report.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

    return enriched


def print_summary(df: pd.DataFrame) -> None:
    print("\nDataset avec affinités venue prior")
    print("==================================")
    print(f"Lignes : {len(df):,}")
    print(f"Colonnes : {len(df.columns):,}")

    print("\nDisponibilité delta_venue_affinity_prior :")
    print(df["delta_venue_affinity_prior"].notna().value_counts())

    print("\nSeuils d'historique venue × nombre :")
    both_3 = ((df["home_prior_home_matches_on_num"] >= 3) & (df["away_prior_away_matches_on_num"] >= 3)).sum()
    both_5 = ((df["home_prior_home_matches_on_num"] >= 5) & (df["away_prior_away_matches_on_num"] >= 5)).sum()
    both_10 = ((df["home_prior_home_matches_on_num"] >= 10) & (df["away_prior_away_matches_on_num"] >= 10)).sum()
    both_20 = ((df["home_prior_home_matches_on_num"] >= 20) & (df["away_prior_away_matches_on_num"] >= 20)).sum()

    print(f"Home domicile et Away extérieur ont au moins 3 matchs prior sur ce nombre  : {both_3:,}")
    print(f"Home domicile et Away extérieur ont au moins 5 matchs prior sur ce nombre  : {both_5:,}")
    print(f"Home domicile et Away extérieur ont au moins 10 matchs prior sur ce nombre : {both_10:,}")
    print(f"Home domicile et Away extérieur ont au moins 20 matchs prior sur ce nombre : {both_20:,}")

    print("\nRésumé delta_venue_affinity_prior :")
    print(df["delta_venue_affinity_prior"].describe())

    print("\nFichiers créés :")
    print(OUTPUT_FILE)
    print(OUTPUT_SAMPLE)
    print(REPORT_FILE)


if __name__ == "__main__":
    enriched_df = build_dataset()
    print_summary(enriched_df)