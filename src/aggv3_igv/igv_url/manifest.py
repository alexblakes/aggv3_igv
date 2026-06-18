"""Download, cache, and join the five S3 manifest files."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_checks as pdc

CACHE_DIR = Path.home() / ".cache" / "aggv3_igv"


def _local_path(key: str, s3_uri: str) -> Path:
    suffix = Path(s3_uri).suffix
    return CACHE_DIR / f"{key}{suffix}"


def _download(s3_uri: str, dest: Path) -> None:
    try:
        import boto3
    except ImportError:
        sys.exit("boto3 is required. Install it with: pip install boto3")

    parts = s3_uri.removeprefix("s3://").split("/", 1)
    bucket, key = parts[0], parts[1]

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading s3://{bucket}/{key} → {dest}", file=sys.stderr)
    try:
        boto3.client("s3").download_file(bucket, key, str(dest))
    except Exception as e:
        sys.exit(
            f"Failed to download {s3_uri}: {e}\n"
            "Check your IAM permissions or run with --refresh-cache after resolving."
        )


def ensure_cached(s3_files: dict, refresh: bool = False) -> dict[str, Path]:
    paths = {key: _local_path(key, uri) for key, uri in s3_files.items()}
    for key, uri in s3_files.items():
        dest = paths[key]
        if refresh or not dest.exists():
            _download(uri, dest)
    return paths


def _load_ids(path: Path) -> pd.DataFrame:
    return (
        pd.read_csv(
            path,
            sep=",",
            low_memory=False,
            usecols=[
                "participant_id",
                "family_grouping",
                "platekey",
                "dragen_karyotypic_sex_estimation",
                "type",
            ],
        )
        .rename(
            columns={
                "dragen_karyotypic_sex_estimation": "karyotype_est",
                "platekey": "sample_id",
            }
        )
        .drop_duplicates("participant_id")
    )


def _load_gel_bams(path: Path) -> pd.DataFrame:
    return (
        pd.read_csv(
            path,
            sep="\t",
            low_memory=False,
            usecols=[
                "participant_id",
                "delivery_date",
                "genome_build",
                "weka_file_path",
                "file_sub_type",
            ],
            header=0,
        )
        .rename(columns={"weka_file_path": "file_path"})
        .loc[lambda df: df["file_sub_type"] == "BAM"]
        .sort_values(["genome_build", "delivery_date"], ascending=False)
        .drop_duplicates("participant_id")
        .loc[:, ["participant_id", "genome_build", "file_path"]]
        .check.head()
        .check.function(lambda x: x["participant_id"] == "112003459")
    )


def _load_gms_bams(path: Path) -> pd.DataFrame:
    return (
        pd.read_csv(
            path,
            sep="\t",
            low_memory=False,
            usecols=[
                "participant_id",
                "delivery_date",
                "genome_build",
                "path",
                "file_sub_type",
            ],
            header=0,
        )
        .rename(columns={"path": "file_path"})
        .loc[lambda df: df["file_sub_type"] == "CRAM"]
        .sort_values("delivery_date", ascending=False)
        .drop_duplicates("participant_id")
        .loc[:, ["participant_id", "genome_build", "file_path"]]
    )


def _load_gel_participant(path: Path) -> pd.DataFrame:
    return (
        pd.read_csv(
            path,
            sep="\t",
            low_memory=False,
            usecols=[
                "participant_id",
                "participant_type",
                "biological_relationship_to_proband",
                "other_biological_relationship_to_proband",
            ],
        )
        .assign(
            biological_relationship_to_proband=lambda x: np.where(
                x["biological_relationship_to_proband"] == "Other",
                x["other_biological_relationship_to_proband"],
                x["biological_relationship_to_proband"],
            )
        )
        .rename(
            columns={"biological_relationship_to_proband": "relationship_to_proband"}
        )
        .assign(
            proband=lambda x: x["participant_type"].map(
                {"Proband": True, "Relative": False}
            )
        )
        .drop_duplicates("participant_id")
        .loc[:, ["participant_id", "relationship_to_proband", "proband"]]
    )


def _load_gms_participant(path: Path) -> pd.DataFrame:
    return (
        pd.read_csv(
            path,
            sep="\t",
            low_memory=False,
            usecols=[
                "participant_id",
                "referral_participant_is_proband",
                "relationship_to_proband",
            ],
        )
        .rename(columns={"referral_participant_is_proband": "proband"})
        .replace({"proband": {"t": True, "f": False}})
        .drop_duplicates("participant_id")
        .loc[:, ["participant_id", "relationship_to_proband", "proband"]]
    )


def build_manifest(s3_files: dict, refresh: bool = False) -> pd.DataFrame:
    paths = ensure_cached(s3_files, refresh)

    ids = _load_ids(paths["aggv3_sample_list"])

    gel_bams = _load_gel_bams(paths["gel_file_paths"])
    gms_bams = _load_gms_bams(paths["gms_file_paths"])
    dna = pd.concat([gel_bams, gms_bams], ignore_index=True).rename(
        columns={"genome_build": "dna_assembly", "file_path": "dna_bam"}
    )

    gel_rel = _load_gel_participant(paths["gel_participant"])
    gms_rel = _load_gms_participant(paths["gms_participant"])
    relation = pd.concat([gel_rel, gms_rel], ignore_index=True).drop_duplicates(
        "participant_id"
    )

    return ids.merge(dna, on="participant_id", how="left").merge(
        relation, on="participant_id", how="left"
    )
