"""Get GMS DNA BAMs"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gms_dna_bams")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            FILE_IN,
            sep="\t",
            names=[
                "participant_id",
                "platekey",
                "referral_id",
                "associated_interpretation_request_id",
                "delivery_type",
                "delivery_id",
                "delivery_date",
                "delivery_version",
                "genome_build",
                "software_version",
                "file_path",
                "filename",
                "type",
                "file_sub_type",
            ],
            usecols=[
                "participant_id",
                "platekey",
                "delivery_date",
                "file_path",
                "genome_build",
                "file_sub_type",
            ],
            header=0,
        )
        .check.nrows(msg="Input rows")
        .check.value_counts("file_sub_type")
        .loc[pd.col("file_sub_type") == "CRAM"]
        .check.nrows(msg="Rows after filter for CRAMs")
        .check.ndups(subset="participant_id")
        .check.print("Keep most recent sample per participant")
        .sort_values("delivery_date", ascending=False)
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after dropping duplicate participant IDs")
        .check.ndups(subset="platekey")
        .loc[:, ["participant_id", "genome_build", "file_path"]]
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()

# %%
