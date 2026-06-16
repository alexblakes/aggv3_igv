"""Make IGV URLs"""

# %%
import ab_utils as ab
import numpy as np
import pandas as pd


def main() -> pd.DataFrame:
    snakemake = ab.inject_snakemake("igv_tidy_data_for_igv")

    return (
        ab.read(
            snakemake.input[0],
            usecols=[
                "participant_id",
                "karyotype_est",
                "type",
                "family_grouping",
                "relationship_to_proband",
                "proband",
                "dna_assembly",
                "dna_bam",
            ],
            dtype={"participant_id": str},
        )
        .loc[pd.col("type") == "rare disease germline"]
        .drop("type", axis=1)
        .check.nrows("Rows after filter for rare disease samples")
        .loc[lambda x: ~x["dna_bam"].isna()]
        .check.nrows("Rows after keeping samples with DNA BAMs")
        .fillna({"proband": False})
        .check.value_counts("proband", dropna=False)
        .assign(
            relationship_to_proband=lambda x: x["relationship_to_proband"].str.lower()
        )
        .check.value_counts("relationship_to_proband", dropna=False)
        .assign(
            relationship_to_proband=lambda x: pd.Series(
                np.where(
                    x["proband"],
                    "proband",
                    x["relationship_to_proband"],
                ),
                index=x.index,
            ).str.replace(r"\s+", "_", regex=True)
        )
        .drop("proband", axis=1)
        .check.value_counts(
            "relationship_to_proband",
            dropna=False,
            msg="Relationship value counts after including probands:",
        )
        .check.ndups("participant_id")
        .check.function(
            lambda x: (
                x.groupby("family_grouping")["relationship_to_proband"]
                .agg(lambda x: (x == "proband").sum())
                .rename("probands_in_family")
                .value_counts()
                .sort_index()
            ),
            msg="Probands per family",
        )
        .assign(name=lambda x: x["relationship_to_proband"] + "_" + x["karyotype_est"])
        .drop(["relationship_to_proband", "karyotype_est"], axis=1)
        .check.value_counts("name")
        .pipe(ab.write, snakemake.output[0])
    )


if __name__ == "__main__":
    df = main()
