"""Get GMS EQ outcomes"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gms_eq_outcomes")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            FILE_IN,
            sep="\t",
            usecols=[
                "participant_id",
                "event_date",
                "case_solved_family",
            ],
        )
        .check.nrows(msg="Input rows")
        .check.ndups(subset="participant_id")
        .check.print("Keep most recent outcome per participant")
        .sort_values("event_date", ascending=False)
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after dropping duplicate IDs")
        .check.value_counts(
            column="case_solved_family",
            dropna=False,
            msg="Case solved value counts",
        )
        .loc[:, ["participant_id", "case_solved_family"]]
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()
