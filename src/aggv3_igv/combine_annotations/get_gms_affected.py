"""Get GMS affection status"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gms_rd_affected")
FILE_IN = snakemake.input[0]
FILE_OUT_AFFECTION = snakemake.output["affection"]
FILE_OUT_PROBAND = snakemake.output["proband"]
FILE_OUT_RELATION = snakemake.output["relation"]

def parse_gms_referral(path):
    return (
        pd.read_csv(
            path,
            sep="\t",
            usecols=[
                "participant_id",
                "referral_participant_is_proband",
                "disease_status",
                "relationship_to_proband",
            ],
        )
        .check.nrows(msg="Input rows")
        .rename(columns={"referral_participant_is_proband": "is_proband"})
        .drop_duplicates()
        .check.nrows(msg="Rows after dropping identical duplicates")
        .check.ndups(subset="participant_id")
    )


def write_affection_status(df, file_out):
    df.loc[:, ["participant_id", "disease_status"]].check.value_counts(
        column="disease_status", msg="Affection status value counts:"
    ).pipe(ab.write, file_out, header=None)

    return df


def write_proband_status(df, file_out):
    df.loc[:, ["participant_id", "is_proband"]].replace(
        {"is_proband": {"f": False, "t": True}}
    ).check.value_counts(
        column="is_proband", dropna=False, msg="Proband value counts"
    ).pipe(ab.write, file_out, header=None)

    return df


def write_relation(df, file_out):
    df.loc[:, ["participant_id", "relationship_to_proband"]].check.value_counts(
        column="relationship_to_proband",
        dropna=False,
        msg="Relation value counts:",
    ).pipe(ab.write, file_out, header=None)

    return df


def main() -> pd.DataFrame:
    return (
        parse_gms_referral(FILE_IN)
        .pipe(write_affection_status, FILE_OUT_AFFECTION)
        .pipe(write_proband_status, FILE_OUT_PROBAND)
        .pipe(write_relation, FILE_OUT_RELATION)
    )


if __name__ == "__main__":
    df = main()
