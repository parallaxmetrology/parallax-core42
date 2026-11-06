"""Does a cohort split by how it was made? A provenance fingerprint from Core42 measurements.

Input: a CSV with one row per patch (or per slide), a grouping column you suspect
(site, scanner, batch, route...), a unit column to aggregate to (slide or patient),
and the 42 Core42 axes, e.g. the output of `parallax-core42 ... --output m.csv`
joined to your own metadata.

    python examples/fingerprint_cohort.py measurements.csv --group site --unit slide_id --out report/

Outputs, in --out:
  axis_auc.csv      per-axis AUC for every pair of groups (no fitting)
  unit_medians.csv  per-unit medians of the 42 axes
  pca.png           first two principal components, coloured by group (projection fitted without labels)
  summary.txt       counts, the most separating axes, and a leave-one-unit-out shrinkage LDA (a fitted readout)

Requires: pandas, scipy, scikit-learn, matplotlib (`pip install -e ".[examples]"`).
"""
from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from parallax_core42 import AXES


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--group", required=True, help="column holding the suspected grouping")
    ap.add_argument("--unit", required=True, help="column to aggregate to (slide or patient id)")
    ap.add_argument("--out", default="fingerprint_report")
    ap.add_argument("--min-patches", type=int, default=4)
    a = ap.parse_args()

    from sklearn.decomposition import PCA
    from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.preprocessing import StandardScaler

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(a.csv)
    if "status" in df:
        df = df[df.status == "ok"]
    n = df.groupby(a.unit).size()
    df = df[df[a.unit].isin(n[n >= a.min_patches].index)]
    med = df.groupby([a.unit, a.group])[list(AXES)].median().reset_index()
    med.to_csv(out / "unit_medians.csv", index=False)
    groups = sorted(med[a.group].unique())
    lines = [f"units per group: {med[a.group].value_counts().to_dict()} (units with < {a.min_patches} patches dropped: {int((n < a.min_patches).sum())})"]
    multi = med[a.unit].duplicated(keep=False)
    if multi.any():
        lines.append(f"warning: {med.loc[multi, a.unit].nunique()} units appear in more than one group; each unit-group pair is treated separately")
    axes = [ax for ax in AXES if med[ax].notna().any()]
    if len(axes) < len(AXES):
        lines.append("axes with no finite values, left out: " + ", ".join(ax for ax in AXES if ax not in axes))

    rows = []
    for g1, g2 in itertools.combinations(groups, 2):
        A, B = med[med[a.group] == g1], med[med[a.group] == g2]
        for ax in axes:
            x, y = B[ax].dropna(), A[ax].dropna()
            auc = mannwhitneyu(x, y).statistic / (len(x) * len(y)) if len(x) and len(y) else np.nan
            rows.append({"contrast": f"{g2} vs {g1}", "axis": ax, "auc": auc, "n_a": len(y), "n_b": len(x)})
    auc = pd.DataFrame(rows)
    auc["separation"] = (auc.auc - 0.5).abs()
    auc.to_csv(out / "axis_auc.csv", index=False)
    for c, g in auc.groupby("contrast"):
        top = g.sort_values("separation", ascending=False).head(6)
        strong = int(((g.auc >= 0.8) | (g.auc <= 0.2)).sum())
        lines.append(f"{c}: {strong}/{len(axes)} axes with AUC >= 0.8 or <= 0.2; strongest: " + ", ".join(f"{r.axis} {r.auc:.2f}" for r in top.itertuples()))

    X = med[axes].fillna(med[axes].median())
    y = med[a.group].to_numpy()
    sizes = med[a.group].value_counts()
    fit_groups = sorted(sizes[sizes >= 2].index)
    if len(fit_groups) < 2:
        lines.append("leave-one-unit-out LDA skipped: needs at least two groups with two or more units each")
    else:
        if len(fit_groups) < len(groups):
            lines.append("LDA uses groups with two or more units only; left out: " + ", ".join(g for g in groups if g not in fit_groups))
        keep = np.isin(y, fit_groups)
        Xk, yk = X[keep].reset_index(drop=True), y[keep]
        pred = np.empty(len(yk), dtype=object)
        for i in range(len(yk)):
            m = np.arange(len(yk)) != i
            sc = StandardScaler().fit(Xk[m])
            lda = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto", priors=np.ones(len(fit_groups)) / len(fit_groups))
            pred[i] = lda.fit(sc.transform(Xk[m]), yk[m]).predict(sc.transform(Xk.iloc[[i]]))[0]
        lines.append(f"leave-one-unit-out shrinkage LDA (fitted readout), balanced accuracy {balanced_accuracy_score(yk, pred):.3f} (chance {1 / len(fit_groups):.3f})")
        lines.append(pd.crosstab(pd.Series(yk, name="true"), pd.Series(pred, name="predicted")).to_string())

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    Xs = StandardScaler().fit_transform(X)
    Z = PCA(2).fit(Xs)
    pcs = Z.transform(Xs)
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for g in groups:
        m = y == g
        ax.scatter(pcs[m, 0], pcs[m, 1], s=22, label=f"{g} ({m.sum()})", edgecolors="white", linewidths=0.6)
    ax.set_xlabel(f"PC1 ({Z.explained_variance_ratio_[0]:.0%})")
    ax.set_ylabel(f"PC2 ({Z.explained_variance_ratio_[1]:.0%})")
    ax.legend(fontsize=8, frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out / "pca.png", dpi=150)
    (out / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
