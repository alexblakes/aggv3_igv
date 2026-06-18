"""aggv3_igv CLI entry point."""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from .config import load_config
from .locus import parse_locus
from .manifest import build_manifest
from .url import build_url


def _read_id_file(path: Path) -> list[str]:
    lines = path.read_text().splitlines()
    return [s.strip() for s in lines if s.strip() and not s.strip().startswith("#")]


def _split_ids(value: str) -> list[str]:
    return [i.strip() for i in value.split(",") if i.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aggv3_igv",
        description="""
        Construct IGV URLs in CloudOS.

        Run this tool in any interactive CloudOS environment. The tab-separated output
        includes an IGV URL for each participant. Click the URL, or copy/paste it into a
        browser, to launch an IGV session zoomed to the given region, and showing IGV 
        tracks for the given participant and their family members.
        """,
    )
    parser.add_argument("-r", "--region", required=True, help="chr:pos|chr:beg-end")

    ids = parser.add_mutually_exclusive_group(required=True)
    ids.add_argument(
        "-p", "--participants", metavar="IDs", help="Comma-separated participant IDs"
    )
    ids.add_argument(
        "-P",
        "--participants-file",
        type=Path,
        metavar="FILE",
        help="File with one participant ID per line",
    )
    ids.add_argument(
        "-s", "--samples", metavar="IDs", help="Comma-separated sample IDs (platekeys)"
    )
    ids.add_argument(
        "-S",
        "--samples-file",
        type=Path,
        metavar="FILE",
        help="File with one sample ID (platekey) per line",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="FILE",
        help="Write TSV to this file (default: stdout)",
    )
    parser.add_argument(
        "-w",
        "--window",
        type=int,
        metavar="bp",
        help="Show +/- this distance (in nt) around the given region",
    )

    parser.add_argument(
        "-a",
        "--assembly",
        metavar="ASSEMBLY",
        help="Override genome build (e.g. GRCh38); other assemblies skipped",
    )

    parser.add_argument(
        "--no-identifiers",
        action="store_true",
        help="Exclude participant ID from the track labels",
    )

    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Re-download all S3 files before running",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    cfg = load_config()
    locus = parse_locus(args.region, window=args.window)

    print("Loading manifest…", file=sys.stderr)
    manifest = build_manifest(cfg["s3_files"], refresh=args.refresh_cache)

    # Resolve the single supplied ID source (argparse guarantees exactly one)
    if args.participants is not None:
        supplied_ids, id_col = _split_ids(args.participants), "participant_id"
    elif args.participants_file is not None:
        supplied_ids, id_col = _read_id_file(args.participants_file), "participant_id"
    elif args.samples is not None:
        supplied_ids, id_col = _split_ids(args.samples), "sample_id"
    else:  # args.samples_file
        supplied_ids, id_col = _read_id_file(args.samples_file), "sample_id"

    supplied_ids = list(dict.fromkeys(supplied_ids))  # dedupe, preserve order

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
            print(
                f"Warning: no BAM/CRAM found for participant '{pid}'; skipping.",
                file=sys.stderr,
            )
        matched = matched.loc[~no_bam]

    # Optionally filter by assembly
    if args.assembly:
        excluded = matched.loc[
            matched["dna_assembly"] != args.assembly, "participant_id"
        ].unique()
        for pid in excluded:
            print(
                f"Warning: participant '{pid}' has no data for assembly '{args.assembly}'; skipping.",
                file=sys.stderr,
            )
        matched = matched.loc[matched["dna_assembly"] == args.assembly]
        if matched.empty:
            sys.exit(
                f"No samples remain after filtering for assembly '{args.assembly}'. Exiting."
            )

    if matched.empty:
        sys.exit("No samples with BAM/CRAM paths remain. Exiting.")

    # Determine which (family_grouping, dna_assembly) groups the matched IDs
    # belong to, then build one URL per group from ALL family members with a
    # BAM/CRAM (relations included), mirroring the historic pipeline
    # (igv_url/construct_igv_url.py).
    target_groups = set(
        map(
            tuple,
            matched[["family_grouping", "dna_assembly"]].drop_duplicates().to_numpy(),
        )
    )
    # One row per participant per assembly: a participant with several
    # platekeys appears multiple times in the manifest, but their BAM/CRAM and
    # labels are participant-keyed, so collapse duplicates here to avoid listing
    # the same track more than once in the IGV URL.
    family_pool = manifest.loc[manifest["dna_bam"].notna()].drop_duplicates(
        ["participant_id", "dna_assembly"]
    )

    group_url: dict[tuple, str] = {}
    for (family, assembly), grp in family_pool.groupby(
        ["family_grouping", "dna_assembly"]
    ):
        if (family, assembly) not in target_groups:
            continue
        group_url[(family, assembly)] = build_url(
            grp,
            locus=locus,
            genomes=cfg.get("genomes", {}),
            port=str(cfg["url"]["port"]),
            no_participant_id=args.no_identifiers,
        )

    # Emit one row per supplied ID per assembly
    rows = []
    for input_id in valid_ids:
        id_rows = matched.loc[matched[id_col] == input_id]
        for (family, assembly), _ in id_rows.groupby(
            ["family_grouping", "dna_assembly"]
        ):
            row = id_rows.loc[id_rows["dna_assembly"] == assembly].iloc[0]
            type_val = (
                "" if pd.isna(row["type"]) else re.sub(r"\s+", "_", str(row["type"]))
            )
            rows.append(
                {
                    "participant_id": row["participant_id"],
                    "platekey": row["sample_id"],
                    "type": type_val,
                    "family_id": family,
                    "genome_assembly": assembly,
                    "igv_url": group_url[(family, assembly)],
                }
            )

    result = pd.DataFrame(
        rows,
        columns=[
            "participant_id",
            "platekey",
            "type",
            "family_id",
            "genome_assembly",
            "igv_url",
        ],
    )

    tsv = result.to_csv(sep="\t", index=False)
    if args.output:
        args.output.write_text(tsv)
    else:
        print(tsv, end="")


if __name__ == "__main__":
    main()
