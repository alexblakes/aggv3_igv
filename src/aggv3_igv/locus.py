"""Parse and normalise genomic locus strings."""

import re
import sys


def _add_chr_prefix(chrom: str) -> str:
    if re.fullmatch(r"\d+|X|Y|MT|M", chrom, re.IGNORECASE):
        return f"chr{chrom}"
    return chrom


def parse_locus(raw: str, window: int | None = None) -> str:
    raw = raw.strip()

    # Variant form: chr:pos:ref:alt (3 or more colons)
    if raw.count(":") >= 3:
        parts = raw.split(":")
        chrom = _add_chr_prefix(parts[0])
        try:
            pos = int(parts[1].replace(",", ""))
        except ValueError:
            sys.exit(f"Invalid variant locus '{raw}': position must be an integer.")
        if window is not None:
            return f"{chrom}:{max(1, pos - window)}-{pos + window}"
        return f"{chrom}:{pos}"

    # Coordinate range or single position
    # Strip commas used as thousands separators in numeric positions
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", raw)

    # Reject bare gene symbols (e.g. "BRCA1" has no colon)
    if ":" not in cleaned:
        sys.exit(
            f"Unrecognised locus '{raw}'. Gene symbols are not supported. "
            "Use a coordinate (e.g. chr7:117120000 or chr7:117120000-117200000) "
            "or a variant ID (e.g. chr12:1234567:G:A)."
        )

    chrom, rest = cleaned.split(":", 1)
    chrom = _add_chr_prefix(chrom)
    return f"{chrom}:{rest}"
