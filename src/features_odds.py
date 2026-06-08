from __future__ import annotations

import pandas as pd

from src.config import (
    FEATURES_DATA_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity.parquet"
OUTPUT_FILE = FEATURES_DATA_DIR / "matches_with_prior_affinity_and_odds.parquet"
OUTPUT_SAMPLE = FEATURES_DATA_DIR / "matches_with_prior_affinity_and_odds_sample.csv"
REPORT_FILE = DATA_REPORTS_DIR / "odds_features_report.csv"


ODDS_GROUPS = {
    "home": ["b365h", "maxh", "avgh"],
    "draw": ["b365d", "maxd", "avgd"],
    "away": ["b365a", "maxa", "avga"],
}


def clean_odds(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    values = values.where(values > 1.0)
    return values


def add_odds_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Nettoyage des colonnes disponibles
    for cols in ODDS_GROUPS.values():
        for col in cols:
            if col in df.columns:
                df[col] = clean_odds(df[col])

    # Version 1 : market odds recommandée
    df["market_odds_home"] = df["avgh"].combine_first(df["b365h"])
    df["market_odds_draw"] = df["avgd"].combine_first(df["b365d"])
    df["market_odds_away"] = df["avga"].combine_first(df["b365a"])

    # Version 2 : moyenne de toutes les colonnes disponibles
    for outcome, cols in ODDS_GROUPS.items():
        existing_cols = [col for col in cols if col in df.columns]
        df[f"mean_odds_{outcome}"] = df[existing_cols].mean(axis=1, skipna=True)
        df[f"n_odds_{outcome}"] = df[existing_cols].notna().sum(axis=1)

    # Validité 1X2
    df["has_market_odds_1x2"] = (
        df["market_odds_home"].notna()
        & df["market_odds_draw"].notna()
        & df["market_odds_away"].notna()
    )

    df["has_mean_odds_1x2"] = (
        df["mean_odds_home"].notna()
        & df["mean_odds_draw"].notna()
        & df["mean_odds_away"].notna()
    )

    # Picks
    market_cols = ["market_odds_home", "market_odds_draw", "market_odds_away"]
    mean_cols = ["mean_odds_home", "mean_odds_draw", "mean_odds_away"]

    market_map = {
        "market_odds_home": "H",
        "market_odds_draw": "D",
        "market_odds_away": "A",
    }

    mean_map = {
        "mean_odds_home": "H",
        "mean_odds_draw": "D",
        "mean_odds_away": "A",
    }

    df["bookmaker_pick_market"] = pd.NA
    df["bookmaker_pick_mean"] = pd.NA

    valid_market_mask = df["has_market_odds_1x2"]
    valid_mean_mask = df["has_mean_odds_1x2"]

    df.loc[valid_market_mask, "bookmaker_pick_market"] = (
        df.loc[valid_market_mask, market_cols]
        .idxmin(axis=1)
        .map(market_map)
    )

    df.loc[valid_mean_mask, "bookmaker_pick_mean"] = (
        df.loc[valid_mean_mask, mean_cols]
        .idxmin(axis=1)
        .map(mean_map)
    )

    df["bookmaker_pick_market_correct"] = df["bookmaker_pick_market"] == df["result"]
    df["bookmaker_pick_mean_correct"] = df["bookmaker_pick_mean"] == df["result"]

    # Probabilités implicites normalisées version market
    inv_home = 1 / df["market_odds_home"]
    inv_draw = 1 / df["market_odds_draw"]
    inv_away = 1 / df["market_odds_away"]
    inv_sum = inv_home + inv_draw + inv_away

    df["market_prob_home"] = inv_home / inv_sum
    df["market_prob_draw"] = inv_draw / inv_sum
    df["market_prob_away"] = inv_away / inv_sum

    return df


def build_dataset() -> pd.DataFrame:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)
    enriched = add_odds_features(df)

    enriched.to_parquet(OUTPUT_FILE, index=False)
    enriched.head(1000).to_csv(OUTPUT_SAMPLE, index=False, encoding="utf-8-sig")

    valid_market = enriched[enriched["has_market_odds_1x2"]].copy()
    valid_mean = enriched[enriched["has_mean_odds_1x2"]].copy()

    valid_both = enriched[
        enriched["has_market_odds_1x2"] & enriched["has_mean_odds_1x2"]
    ].copy()

    same_pick = (
        valid_both["bookmaker_pick_market"]
        == valid_both["bookmaker_pick_mean"]
    ).mean()

    report = pd.DataFrame(
        [
            {"metric": "rows_total", "value": len(enriched)},
            {"metric": "rows_with_market_odds_1x2", "value": int(enriched["has_market_odds_1x2"].sum())},
            {"metric": "coverage_market_odds_1x2_pct", "value": round(enriched["has_market_odds_1x2"].mean() * 100, 3)},
            {"metric": "rows_with_mean_odds_1x2", "value": int(enriched["has_mean_odds_1x2"].sum())},
            {"metric": "coverage_mean_odds_1x2_pct", "value": round(enriched["has_mean_odds_1x2"].mean() * 100, 3)},
            {"metric": "market_pick_accuracy_pct", "value": round(valid_market["bookmaker_pick_market_correct"].mean() * 100, 3)},
            {"metric": "mean_pick_accuracy_pct", "value": round(valid_mean["bookmaker_pick_mean_correct"].mean() * 100, 3)},
            {"metric": "market_vs_mean_same_pick_pct", "value": round(same_pick * 100, 3)},
            {"metric": "market_home_pick_share_pct", "value": round(valid_market["bookmaker_pick_market"].eq("H").mean() * 100, 3)},
            {"metric": "market_draw_pick_share_pct", "value": round(valid_market["bookmaker_pick_market"].eq("D").mean() * 100, 3)},
            {"metric": "market_away_pick_share_pct", "value": round(valid_market["bookmaker_pick_market"].eq("A").mean() * 100, 3)},
        ]
    )

    report.to_csv(REPORT_FILE, index=False, encoding="utf-8-sig")

    return enriched, report


def print_summary(df: pd.DataFrame, report: pd.DataFrame) -> None:
    print("\nDataset enrichi avec cotes")
    print("==========================")
    print(report.to_string(index=False))

    print("\nDistribution bookmaker_pick_market :")
    print(df.loc[df["has_market_odds_1x2"], "bookmaker_pick_market"].value_counts(normalize=True).mul(100).round(3))

    print("\nFichiers créés :")
    print(OUTPUT_FILE)
    print(OUTPUT_SAMPLE)
    print(REPORT_FILE)


if __name__ == "__main__":
    enriched_df, report_df = build_dataset()
    print_summary(enriched_df, report_df)