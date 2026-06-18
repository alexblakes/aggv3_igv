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
    dna_assembly = group["dna_assembly"].iloc[0]
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
        flag = row.get("proband")
        is_proband = pd.notna(flag) and bool(flag)
        if is_proband:
            rel = "proband"
        else:
            rel = row.get("relationship_to_proband") or "unknown"
            rel = re.sub(r"\s+", "_", str(rel).lower())
        kary = row.get("karyotype_est") or "unknown"
        if no_participant_id:
            return f"{rel}_{kary}"
        pid = row.get("participant_id") or "unknown"
        return f"{pid}_{rel}_{kary}"

    # Sort file paths and labels by the track-label ("name") value, matching
    # the historic pipeline's `.sort_values("name")`.
    labeled = sorted(
        ((_label(row), row["dna_bam"]) for _, row in group.iterrows()),
        key=lambda pair: pair[0],
    )
    names = [name for name, _ in labeled]
    files = [path for _, path in labeled]

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
