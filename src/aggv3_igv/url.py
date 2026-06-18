"""Build igv:// protocol-handler URLs."""

import re
import sys
from urllib.parse import quote

import pandas as pd

_GENOME_FALLBACK = {
    "GRCh38": "hg38",
    "GRCh37": "hg19",
}


def build_url(
    group: pd.DataFrame,
    locus: str,
    genomes: dict,
    port: str,
    no_participant_id: bool = False,
) -> str:
    def _rel(row: pd.Series) -> str:
        flag = row.get("proband")
        if pd.notna(flag) and bool(flag):
            return "proband"
        rel = row.get("relationship_to_proband") or "unknown"
        return re.sub(r"\s+", "_", str(rel).lower())

    # Order tracks alphabetically by relationship_to_proband (the proband is
    # labelled "proband"); participant_id breaks ties deterministically.
    work = group.copy()
    work["_rel"] = [_rel(row) for _, row in work.iterrows()]
    ordered = work.sort_values(["_rel", "participant_id"], kind="stable").reset_index(
        drop=True
    )

    dna_assembly = ordered["dna_assembly"].iloc[0]
    genome_path = genomes.get(dna_assembly)
    if genome_path is None:
        fallback = _GENOME_FALLBACK.get(dna_assembly, dna_assembly)
        print(
            f"Warning: no genome path configured for '{dna_assembly}'; "
            f"falling back to IGV built-in '{fallback}'.",
            file=sys.stderr,
        )
        genome_path = fallback

    def _label(row: pd.Series) -> str:
        rel = row["_rel"]
        kary = row.get("karyotype_est") or "unknown"
        if no_participant_id:
            return f"{rel}_{kary}"
        pid = row.get("participant_id") or "unknown"
        return f"{pid}_{rel}_{kary}"

    files = ordered["dna_bam"].tolist()
    names = [_label(row) for _, row in ordered.iterrows()]

    # Build query string manually so comma-separated file/name lists aren't
    # double-encoded; NFS paths contain slashes that must be encoded in the
    # file= value but not in the genome= path.
    file_val = ",".join(quote(f, safe="") for f in files)
    name_val = ",".join(quote(n, safe="") for n in names)
    locus_val = quote(locus, safe=":-")
    genome_val = quote(str(genome_path), safe="/._-")

    return (
        f"http://localhost:{port}/load?"
        f"file={file_val}"
        f"&locus={locus_val}"
        f"&genome={genome_val}"
        f"&merge=false"
        f"&name={name_val}"
    )
