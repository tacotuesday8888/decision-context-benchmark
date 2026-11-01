"""Postcollection layout repair from frozen result tables; no new statistics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scripts.study_v7.report import CONFIGS, CONDITIONS

    directory = Path(directory)
    inputs = [directory / name for name in (
        "primary-analysis.json", "descriptive-analysis.json", "matched-comparisons.json",
        "matched-comparisons.csv", "repeat-stability.json", "repeat-stability.csv",
        "analysis-driver.json", "artifact-manifest.json", "tables/analysis-tables.json")]
    before = {str(p.relative_to(directory)): sha(p) for p in inputs}
    package = json.loads((directory / "tables/analysis-tables.json").read_text())
    output = directory / "reviewed-figures"
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"svg.hashsalt": "Decision-Context-Benchmark-v7-reviewed", "font.size": 9})
    artifacts = []

    def save(fig, name):
        for suffix in ("png", "svg"):
            path = output / (name + "." + suffix)
            metadata = ({"Software": "Decision Context Benchmark"} if suffix == "png"
                        else {"Date": None, "Creator": "Decision Context Benchmark"})
            fig.savefig(path, dpi=160, metadata=metadata)
            artifacts.append(path)
        plt.close(fig)

    rows = package["tables"]["primary_contrasts"]
    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    fig.subplots_adjust(left=.35, right=.98, top=.80, bottom=.18)
    for i, row in enumerate(rows):
        for prefix, color, width, offset in (
            ("conservative_99_166667", "#90a9bf", 5, -.07),
            ("pointwise_95", "#173a55", 2, .07)):
            low, high = row[prefix + "_lower_pp"], row[prefix + "_upper_pp"]
            if low is not None:
                label = ("99.1667% per comparison" if offset < 0 else "95% pointwise") if i == 0 else None
                ax.hlines(i + offset, low, high, color=color, linewidth=width, label=label)
        if row["estimate_pp"] is not None:
            ax.plot(row["estimate_pp"], i, "o", color="#173a55", markersize=4)
    ax.axvline(0, color="#777777", linewidth=.8)
    ax.set_yticks(range(len(rows)), [
        f"{CONFIGS[r['config']]} / {CONDITIONS[r['control']]}  N={r['primary_complete_groups']}"
        for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Control − task balanced error (percentage points)\nPositive values favor authentic task information")
    ax.set_title("BrowseSafe++: shared complete-group native contrasts", pad=35)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.005), ncol=2, frameon=False)
    save(fig, "primary-contrasts")

    bounds = package["tables"]["planned_bounds"]
    fig, ax = plt.subplots(figsize=(10.4, 5.8))
    fig.subplots_adjust(left=.38, right=.98, top=.82, bottom=.18)
    for i, row in enumerate(bounds):
        if row["lower_pp"] is not None:
            ax.hlines(i, row["lower_pp"], row["upper_pp"], color="#925b19", linewidth=3)
    ax.axvline(0, color="#777777", linewidth=.8)
    ax.set_yticks(range(len(bounds)), [
        f"{CONFIGS[r['config']]} / {CONDITIONS[r['control']]}  planned N={r['planned_groups']}"
        for r in bounds])
    ax.invert_yaxis()
    ax.set_xlabel("Control − task error bounds (percentage points)")
    ax.set_title("BrowseSafe++: all 3,000 planned groups\nMissing-error bounds (not confidence intervals)", pad=12)
    save(fig, "planned-missingness-bounds")

    for name in ("browsesafe-error-coverage", "promptshield-error-coverage"):
        for suffix in ("png", "svg"):
            target = output / (name + "." + suffix)
            shutil.copyfile(directory / "figures" / target.name, target)
            artifacts.append(target)
    after = {str(p.relative_to(directory)): sha(p) for p in inputs}
    if before != after:
        raise ValueError("Frozen numerical or original-render inputs changed during layout repair")
    manifest = {
        "version": "study-v7-postcollection-reviewed-render-1",
        "scope": "Presentation layout, legend placement, title wrapping and direction label; numerical series unchanged; two other figures copied unchanged.",
        "new_statistics_calculated": False,
        "frozen_inputs_unchanged": True,
        "original_frozen_renders_preserved": True,
        "input_sha256": before,
        "render_code_sha256": sha(__file__),
        "artifact_sha256": {str(p.relative_to(directory)): sha(p) for p in artifacts}}
    path = directory / "reviewed-render-manifest.json"
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    render(parser.parse_args().results)


if __name__ == "__main__":
    main()
