"""Construct IGV URLs"""

# %%
import ab_utils as ab
import numpy as np
import pandas as pd

PORT = "60151"
LOCUS_37 = "22:43011250-43011399"
LOCUS_38 = "22:42615244-42615393"
GENOME_37 = "/public_data_resources/IGV/hg19/hg19_local.genome"
GENOME_38 = "/public_data_resources/IGV/hg38/hg38_local.json"  # "/public_data_resources/IGV/hg38/hg38.fa"
MERGE = "false"


def main() -> pd.DataFrame:
    snakemake = ab.inject_snakemake("igv_construct_igv_url")

    return (
        ab.read(snakemake.input[0])
        .fillna({"name": "_"})
        .sort_values("name")
        .groupby(["family_grouping", "dna_assembly"], sort=False)
        .agg(
            name=("name", ",".join),
            url=("dna_bam", ",".join),
            name_tmp=("name", list),
            proband_id=("participant_id", list),
        )
        .assign(
            name=lambda x: x["name"].str.strip(","),
            url=lambda x: x["url"].str.strip(","),
        )
        .reset_index()
        .check.nrows("Rows after grouping on family and assembly")
        .check.nunique("family_grouping", msg="Unique families")
        .explode(["name_tmp", "proband_id"])
        .check.nrows("Rows after exploding 'name_tmp' and 'proband_id'")
        .loc[lambda x: x["name_tmp"].str.startswith("proband")]
        .check.nrows("Rows after dropping non-probands")
        .check.nunique(
            "family_grouping", msg="Unique families after dropping non-probands"
        )
        .check.ndups(["family_grouping", "proband_id"])
        .check.ndups("family_grouping")
        .check.value_counts("dna_assembly", dropna=True)
        .assign(
            port=PORT,
            locus=lambda x: np.where(x["dna_assembly"] == "GRCh38", LOCUS_38, LOCUS_37),
            genome=lambda x: np.where(
                x["dna_assembly"] == "GRCh38", GENOME_38, GENOME_37
            ),
            merge=MERGE,
            igv=lambda x: (
                "http://localhost:"
                + x["port"]
                + "/load?file="
                + x["url"]
                + "&locus="
                + x["locus"]
                + "&genome="
                + x["genome"]
                + "&merge="
                + x["merge"]
                + "&name="
                + x["name"]
                + " "
            ),
        )
        .loc[:, ["proband_id", "family_grouping", "dna_assembly", "igv"]]
        .pipe(ab.write, snakemake.output[0])
    )


if __name__ == "__main__":
    df = main()

# %%
