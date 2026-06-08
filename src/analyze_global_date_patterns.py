from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency

from src.config import (
    FEATURES_DATA_DIR,
    TABLES_DIR,
    CHARTS_DIR,
    DATA_REPORTS_DIR,
    ensure_directories,
)


INPUT_FILE = FEATURES_DATA_DIR / "matches_with_date_features.parquet"

OUTPUT_TABLE = TABLES_DIR / "global_result_by_date_num.csv"
OUTPUT_CHART = CHARTS_DIR / "global_result_by_date_num.png"
OUTPUT_REPORT = DATA_REPORTS_DIR / "global_date_num_analysis.csv"


def analyze_global_patterns() -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_directories()

    df = pd.read_parquet(INPUT_FILE)

    # Moyenne générale
    global_rates = df["result"].value_counts(normalize=True).to_dict()

    # Table par nombre
    summary = (
        df.groupby("date_num_1_9")
        .agg(
            matches=("result", "count"),
            home_wins=("result", lambda x: (x == "H").sum()),
            draws=("result", lambda x: (x == "D").sum()),
            away_wins=("result", lambda x: (x == "A").sum()),
        )
        .reset_index()
    )

    summary["home_win_rate"] = summary["home_wins"] / summary["matches"]
    summary["draw_rate"] = summary["draws"] / summary["matches"]
    summary["away_win_rate"] = summary["away_wins"] / summary["matches"]

    summary["home_delta_vs_global"] = summary["home_win_rate"] - global_rates.get("H", 0)
    summary["draw_delta_vs_global"] = summary["draw_rate"] - global_rates.get("D", 0)
    summary["away_delta_vs_global"] = summary["away_win_rate"] - global_rates.get("A", 0)

    # Version pour lecture humaine en %
    percent_cols = [
        "home_win_rate",
        "draw_rate",
        "away_win_rate",
        "home_delta_vs_global",
        "draw_delta_vs_global",
        "away_delta_vs_global",
    ]

    summary_export = summary.copy()

    for col in percent_cols:
        summary_export[col] = (summary_export[col] * 100).round(3)

    summary_export.to_csv(OUTPUT_TABLE, index=False, encoding="utf-8-sig")

    # Test chi-square
    contingency = pd.crosstab(df["date_num_1_9"], df["result"])
    chi2, p_value, dof, expected = chi2_contingency(contingency)

    report = pd.DataFrame(
        [
            {"metric": "rows", "value": len(df)},
            {"metric": "chi2", "value": chi2},
            {"metric": "p_value", "value": p_value},
            {"metric": "degrees_of_freedom", "value": dof},
            {"metric": "global_home_win_rate_pct", "value": global_rates.get("H", 0) * 100},
            {"metric": "global_draw_rate_pct", "value": global_rates.get("D", 0) * 100},
            {"metric": "global_away_win_rate_pct", "value": global_rates.get("A", 0) * 100},
        ]
    )

    report.to_csv(OUTPUT_REPORT, index=False, encoding="utf-8-sig")

    return summary_export, report


def plot_global_patterns(summary: pd.DataFrame) -> None:
    plot_df = summary.copy()

    x = plot_df["date_num_1_9"].astype(str)

    plt.figure(figsize=(10, 6))

    plt.plot(x, plot_df["home_win_rate"], marker="o", label="Victoire domicile")
    plt.plot(x, plot_df["draw_rate"], marker="o", label="Nul")
    plt.plot(x, plot_df["away_win_rate"], marker="o", label="Victoire extérieur")

    plt.title("Distribution des résultats par nombre de date")
    plt.xlabel("Nombre de date réduit 1-9")
    plt.ylabel("Taux (%)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(OUTPUT_CHART, dpi=160)
    plt.close()


def print_summary(summary: pd.DataFrame, report: pd.DataFrame) -> None:
    print("\nAnalyse globale date_num_1_9 → résultat")
    print("========================================")
    print(summary.to_string(index=False))

    print("\nTest chi-square")
    print("================")
    print(report.to_string(index=False))

    p_value = float(report.loc[report["metric"] == "p_value", "value"].iloc[0])

    print("\nInterprétation rapide")
    print("=====================")

    if p_value < 0.05:
        print("Le test détecte une association statistique globale entre date_num_1_9 et résultat.")
        print("Attention : avec plus de 200 000 matchs, même de très petits écarts peuvent devenir significatifs.")
    else:
        print("Le test ne détecte pas d'association globale forte entre date_num_1_9 et résultat.")

    print("\nFichiers créés :")
    print(OUTPUT_TABLE)
    print(OUTPUT_CHART)
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    summary_df, report_df = analyze_global_patterns()
    plot_global_patterns(summary_df)
    print_summary(summary_df, report_df)