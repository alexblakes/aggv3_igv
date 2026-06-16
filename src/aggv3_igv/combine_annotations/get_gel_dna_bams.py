"""Get GEL DNA BAMs"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gel_dna_bams")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            FILE_IN,
            sep="\t",
            names=[
                "participant_id",
                "lab_sample_id",
                "platekey",
                "delivery_id",
                "delivery_date",
                "delivery_version",
                "genome_build",
                "type",
                "file_path",
                "filename",
                "file_sub_type",
                "file_type",
            ],
            usecols=[
                "participant_id",
                "platekey",
                "delivery_date",
                "genome_build",
                "file_path",
                "file_sub_type",
            ],
            header=0,
        )
        .check.nrows(msg="Input rows")
        .loc[pd.col("file_sub_type") == "BAM"]
        .check.nrows(msg="Rows after filter for BAMs")
        .check.ndups(subset="participant_id")
        .check.print("Keep most recent sample per participant")
        .sort_values(["genome_build", "delivery_date"], ascending=False)
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after drop duplicated participant IDs")
        .check.ndups(subset="participant_id")
        .check.ndups(subset="platekey")
        .loc[:, ["participant_id", "genome_build", "file_path"]]
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()

# %%
