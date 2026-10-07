"""Command-line interface for the agriscope-ml package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from .data.datasets import save_versioned_dataset, validate_user_csv
from .data.nasa_power import NasaPowerClient
from .data.synthetic import generate_synthetic_et_dataset
from .registry import ModelRegistry
from .train import load_dataset_from_source, train_all_models, train_single_model


def build_dataset_command(args: argparse.Namespace) -> int:
    """Build dataset from NASA POWER or synthetic offline fallback."""
    output_dir = Path(args.output_dir)
    source = args.source.lower()
    version = args.version

    print(f"[*] AgriScope ML: Building dataset (requested source: {source})...")

    df = None
    provenance = source
    is_synthetic = False

    if source == "nasa":
        try:
            print("[*] Contacting NASA POWER Agroclimatology API for global stations...")
            client = NasaPowerClient()
            df, report = client.fetch_multi_station_dataset(
                start_date=args.start_date,
                end_date=args.end_date,
                max_stations=args.max_stations,
            )
            if df.empty or len(df) == 0:
                raise RuntimeError("NASA POWER query returned 0 valid records.")
            print(
                f"[+] Successfully fetched {len(df)} records across {report.locations_processed} stations."
            )
            provenance = "nasa_power"
            is_synthetic = False
        except Exception as e:
            print(
                f"[!] WARNING: NASA POWER API unavailable ({e}). Falling back to SYNTHETIC data generation.",
                file=sys.stderr,
            )
            print(
                "[!] NOTE: Dataset will be stamped with provenance='synthetic'. Never present synthetic data as real.",
                file=sys.stderr,
            )
            source = "synthetic"

    if source == "synthetic":
        print(f"[*] Generating {args.num_samples} physically-consistent synthetic records...")
        df = generate_synthetic_et_dataset(
            num_samples=args.num_samples,
            seed=args.seed,
        )
        provenance = "synthetic"
        is_synthetic = True

    if df is None or df.empty:
        print("[x] Error: Failed to generate or download dataset.", file=sys.stderr)
        return 1

    pq_path, csv_path, meta = save_versioned_dataset(
        df=df,
        output_dir=output_dir,
        dataset_name=args.name,
        version=version,
        provenance=provenance,
        is_synthetic=is_synthetic,
    )

    print("[+] Dataset build complete!")
    print(f"    Parquet: {pq_path}")
    print(f"    CSV:     {csv_path}")
    print(f"    Rows:    {meta.row_count}")
    print(f"    SHA-256: {meta.content_hash}")
    print(f"    Origin:  {meta.provenance} (is_synthetic={meta.is_synthetic})")
    return 0


def validate_csv_command(args: argparse.Namespace) -> int:
    """Validate user-uploaded CSV against AgriScope physical boundary schema."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[x] Error: File '{file_path}' does not exist.", file=sys.stderr)
        return 1

    print(f"[*] Validating CSV schema for: {file_path}...")
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"[x] Failed to read CSV: {e}", file=sys.stderr)
        return 1

    report = validate_user_csv(df)
    if report.is_valid:
        print(f"[+] CSV is VALID! Found {report.row_count} rows.")
        if report.warnings:
            for w in report.warnings:
                print(f"    [!] Warning: {w}")
        return 0
    else:
        print(f"[x] CSV validation FAILED with {len(report.errors)} errors:", file=sys.stderr)
        for err in report.errors:
            print(f"    - {err}", file=sys.stderr)
        return 1


def resolve_dataset_file(dataset_arg: Optional[str]) -> Path:
    """Resolve dataset argument to an existing file path or raise FileNotFoundError."""
    if dataset_arg:
        p = Path(dataset_arg)
        if p.exists():
            return p
        # Check standard search locations
        for cand in [
            Path("data/processed") / f"{dataset_arg}.parquet",
            Path("data/processed") / f"{dataset_arg}.csv",
            Path("data/processed") / dataset_arg,
            Path(f"{dataset_arg}.parquet"),
            Path(f"{dataset_arg}.csv"),
        ]:
            if cand.exists():
                return cand

    # If no argument, search for any dataset in data/processed
    proc_dir = Path("data/processed")
    if proc_dir.exists():
        files = list(proc_dir.glob("*.parquet")) + list(proc_dir.glob("*.csv"))
        if files:
            return sorted(files)[-1]

    raise FileNotFoundError(
        f"Dataset '{dataset_arg}' not found. Please provide a valid file or run 'agriscope-ml build-dataset'."
    )


def train_command(args: argparse.Namespace) -> int:
    """Train ML models and register artifacts into the model registry."""
    print("[*] AgriScope ML: Initiating training pipeline...")

    # Resolve dataset
    try:
        ds_path = resolve_dataset_file(args.dataset)
        print(f"[*] Loading training dataset from: {ds_path}")
        df = load_dataset_from_source(ds_path)
    except FileNotFoundError:
        print(
            "[!] No existing dataset found. Auto-generating 2000 synthetic samples for bootstrapping..."
        )
        df = generate_synthetic_et_dataset(num_samples=2000, seed=args.seed)

    registry = ModelRegistry(root_dir=args.artifacts_dir)
    algo = args.algorithm.lower().strip()

    print(f"[*] Target algorithm: {algo} | Schema: {args.schema} | Registry: {args.artifacts_dir}")
    print(f"    Dataset rows: {len(df)} | Columns: {list(df.columns)}")

    results = {}
    if algo == "all":
        results = train_all_models(
            df=df,
            version=args.version,
            feature_schema=args.schema,
            registry=registry,
            seed=args.seed,
        )
    else:
        res = train_single_model(
            df=df,
            algorithm=algo,
            version=args.version,
            feature_schema=args.schema,
            registry=registry,
            seed=args.seed,
        )
        results[algo] = res

    # Print summary table
    print("\n" + "=" * 90)
    print(
        f"{'Algorithm':<16} | {'Random R²':<10} | {'Random RMSE':<11} | {'Grouped R²':<10} | {'Grouped RMSE':<12} | {'Coverage':<8}"
    )
    print("-" * 90)
    for name, r in results.items():
        r_r2 = r.random_metrics.get("r2", 0.0)
        r_rmse = r.random_metrics.get("rmse", 0.0)
        g_r2 = r.grouped_metrics.get("r2", 0.0)
        g_rmse = r.grouped_metrics.get("rmse", 0.0)
        cov = r.conformal_metrics.get("empirical_coverage", 0.0)
        print(
            f"{name:<16} | {r_r2:<10.4f} | {r_rmse:<11.4f} | {g_r2:<10.4f} | {g_rmse:<12.4f} | {cov:<8.2%}"
        )
    print("=" * 90)
    print(
        f"[+] All requested models trained and registered successfully in {args.artifacts_dir}!\n"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agriscope-ml",
        description="AgriScope Machine Learning CLI for ET modeling and data workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # build-dataset
    build_parser = subparsers.add_parser(
        "build-dataset", help="Build and version training dataset."
    )
    build_parser.add_argument("--source", choices=["nasa", "synthetic"], default="synthetic")
    build_parser.add_argument("--output-dir", default="./data/processed")
    build_parser.add_argument("--name", default="agriscope_et")
    build_parser.add_argument("--version", default="v1")
    build_parser.add_argument("--num-samples", type=int, default=2000)
    build_parser.add_argument("--max-stations", type=int, default=5)
    build_parser.add_argument("--start-date", default="20220101")
    build_parser.add_argument("--end-date", default="20221231")
    build_parser.add_argument("--seed", type=int, default=42)
    build_parser.set_defaults(func=build_dataset_command)

    # validate-csv
    val_parser = subparsers.add_parser("validate-csv", help="Validate a user CSV schema.")
    val_parser.add_argument("--file", required=True, help="Path to CSV file.")
    val_parser.set_defaults(func=validate_csv_command)

    # train
    train_parser = subparsers.add_parser("train", help="Train and register ET models.")
    train_parser.add_argument("--algorithm", default="all")
    train_parser.add_argument("--dataset", default=None, help="Path or ID of dataset.")
    train_parser.add_argument("--version", default="v1.0")
    train_parser.add_argument("--schema", choices=["basic", "extended"], default="basic")
    train_parser.add_argument("--artifacts-dir", default="./artifacts")
    train_parser.add_argument("--seed", type=int, default=42)
    train_parser.set_defaults(func=train_command)

    parsed_args = parser.parse_args()
    exit_code = parsed_args.func(parsed_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
