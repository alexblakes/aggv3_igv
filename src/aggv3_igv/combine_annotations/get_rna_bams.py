"""Get RNA BAM paths"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_rna_bams")
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
                "delivery_id",
                "delivery_date",
                "genome_build",
                "software_version",
                "type",
                "folder_path",
                "file_path",
                "file_name",
                "file_type",
                "file_sub_type",
            ],
            header=0,
            usecols=[
                "participant_id",
                "platekey",
                "file_path",
                "delivery_date",
                "file_sub_type",
            ],
        )
        .check.nrows(msg="Input rows")
        .loc[pd.col("file_sub_type") == "BAM"]
        .drop("file_sub_type", axis=1)
        .check.nrows(msg="Rows after filter for BAMs")
        .check.nunique("participant_id")
        .check.nunique("platekey")
        .check.print("Keep the most recent sample per participant")
        .sort_values("delivery_date", ascending=False)
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after dropping duplicates")
        .loc[:, ["participant_id", "file_path"]]
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()
