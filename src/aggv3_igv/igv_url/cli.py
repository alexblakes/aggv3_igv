"""aggv3_igv CLI entry point."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import load_config
from .locus import parse_locus
from .manifest import build_manifest
from .url import build_url


def _read_id_file(path: Path) -> list[str]:
    lines = path.read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def _collect_ids(flag_value: str | None, file_path: Path | None) -> list[str]:
    ids: list[str] = []
    if flag_value:
        ids.extend(i.strip() for i in flag_value.split(",") if i.strip())
    if file_path:
        ids.extend(_read_id_file(file_path))
    return list(dict.fromkeys(ids))  # deduplicate, preserve order


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aggv3_igv",
        description="Construct igv:// URLs for participants or samples in AggV3.",
    )
    parser.add_argument("-r", "--region", required=True, help="Genomic locus")
    parser.add_argument("-p", "--participants", metavar="IDs", help="Comma-separated participant IDs")
    parser.add_argument("-P", "--participants-file", type=Path, metavar="FILE", help="File with one participant ID per line")
    parser.add_argument("-s", "--samples", metavar="IDs", help="Comma-separated sample IDs (platekeys)")
    parser.add_argument("-S", "--samples-file", type=Path, metavar="FILE", help="File with one sample ID per line")
    parser.add_argument("-w", "--window", type=int, metavar="BP", help="Half-window around a variant locus")
    parser.add_argument("--no-participant-id", action="store_true", help="Exclude participant ID from track labels")
    parser.add_argument("-a", "--assembly", metavar="BUILD", help="Override genome build (e.g. GRCh38); other assemblies skipped")
    parser.add_argument("--refresh-cache", action="store_true", help="Re-download all S3 files before running")
    parser.add_argument("-o", "--output", type=Path, metavar="FILE", help="Write TSV to this file (default: stdout)")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Validate: must use participants OR samples, not both, not neither
    using_participants = bool(args.participants or args.participants_file)
    using_samples = bool(args.samples or args.samples_file)

    if using_participants and using_samples:
        parser.error("--participants/--participants-file and --samples/--samples-file are mutually exclusive.")
    if not using_participants and not using_samples:
        parser.error("Provide at least one of --participants, --participants-file, --samples, --samples-file.")

    cfg = load_config()
    locus = parse_locus(args.region, window=args.window)

    print("Loading manifest…", file=sys.stderr)
    manifest = build_manifest(cfg["s3_files"], refresh=args.refresh_cache)

    # Collect and resolve supplied IDs
    if using_participants:
        supplied_ids = _collect_ids(args.participants, args.participants_file)
        id_col = "participant_id"
    else:
        supplied_ids = _collect_ids(args.samples, args.samples_file)
        id_col = "sample_id"

    # Filter manifest to matched rows; warn on unknowns
    known = set(manifest[id_col].dropna())
    unknown = [i for i in supplied_ids if i not in known]
    for uid in unknown:
        print(f"Warning: '{uid}' not found in manifest; skipping.", file=sys.stderr)
    valid_ids = [i for i in supplied_ids if i in known]
    if not valid_ids:
        sys.exit("No valid IDs remain after lookup. Exiting.")

    matched = manifest.loc[manifest[id_col].isin(valid_ids)].copy()

    # Drop rows without a BAM/CRAM path
    no_bam = matched["dna_bam"].isna()
    if no_bam.any():
        missing_pids = matched.loc[no_bam, "participant_id"].unique()
        for pid in missing_pids:
            print(f"Warning: no BAM/CRAM found for participant '{pid}'; skipping.", file=sys.stderr)
        matched = matched.loc[~no_bam]

    # Optionally filter by assembly
    if args.assembly:
        excluded = matched.loc[matched["dna_assembly"] != args.assembly, "participant_id"].unique()
        for pid in excluded:
            print(
                f"Warning: participant '{pid}' has no data for assembly '{args.assembly}'; skipping.",
                file=sys.stderr,
            )
        matched = matched.loc[matched["dna_assembly"] == args.assembly]
        if matched.empty:
            sys.exit(f"No samples remain after filtering for assembly '{args.assembly}'. Exiting.")

    if matched.empty:
        sys.exit("No samples with BAM/CRAM paths remain. Exiting.")

    # Build one URL per (family_grouping, dna_assembly) group
    group_url: dict[tuple, str] = {}
    for (family, assembly), grp in matched.groupby(["family_grouping", "dna_assembly"]):
        group_url[(family, assembly)] = build_url(
            grp,
            locus=locus,
            genomes=cfg.get("genomes", {}),
            no_participant_id=args.no_participant_id,
        )

    # Emit one row per supplied ID per assembly
    rows = []
    for input_id in valid_ids:
        id_rows = matched.loc[matched[id_col] == input_id]
        for (family, assembly), _ in id_rows.groupby(["family_grouping", "dna_assembly"]):
            pid = id_rows.loc[id_rows["dna_assembly"] == assembly, "participant_id"].iloc[0]
            rows.append(
                {
                    "participant_id": pid,
                    "family_id": family,
                    "genome_assembly": assembly,
                    "igv_url": group_url[(family, assembly)],
                }
            )

    result = pd.DataFrame(rows, columns=["participant_id", "family_id", "genome_assembly", "igv_url"])

    tsv = result.to_csv(sep="\t", index=False)
    if args.output:
        args.output.write_text(tsv)
    else:
        print(tsv, end="")


if __name__ == "__main__":
    main()
