"""Get GEL RD affected participants"""

# %%
import ab_utils as ab
import pandas as pd
import os
from rnu12 import io

f = open(os.devnull, "w")

snakemake = ab.inject_snakemake("cohorts_get_gel_rd_affection_proband")
FILE_IN = snakemake.input[0]
FILE_OUT_AFFECTION = snakemake.output["affection"]
FILE_OUT_PROBAND = snakemake.output["proband"]
# FILE_OUT_RELATION = snakemake.output["relation"]

def write_affection_status(df, file_out):
    (
        df.loc[:, ["participant_id", "affection_status"]]
        .assign(affection_status=lambda x: x["affection_status"].str.lower())
        .check.value_counts(
            column="affection_status", msg="Affection status value counts:"
        )
        .pipe(ab.write, file_out, header=None)
    )

    return df


def write_relation(df, file_out):
    (
        df.loc[:, ["participant_id", "biological_relationship_to_proband"]]
        .check.value_counts(column="biological_relationship_to_proband", dropna=False)
        .pipe(ab.write, file_out, header=None)
    )

    return df


def write_proband_status(df, file_out):
    df.loc[:, ["participant_id", "is_proband"]].check.value_counts(
        column="is_proband", msg="Proband value counts:"
    ).pipe(ab.write, file_out, header=None)
    return df


def main() -> pd.DataFrame:
    return (
        io.parse_gel_interpretation_data(FILE_IN)
        .pipe(write_affection_status, FILE_OUT_AFFECTION)
        .pipe(write_proband_status, FILE_OUT_PROBAND)
        # .pipe(write_relation, FILE_OUT_RELATION)
        .check.head()
    )


if __name__ == "__main__":
    df = main()

# %%
