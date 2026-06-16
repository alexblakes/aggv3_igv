"""Get GEL Dx discovery outcomes"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gel_dd_outcomes")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(FILE_IN, sep="\t", usecols=["participant_id"])
        .check.nrows(msg="Input rows")
        .check.ndups()
        .drop_duplicates()
        .check.nrows(msg="Rows after dropping duplicates")
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()
