"""Get GEL exit questionnaire outomes"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gel_eq_outcomes")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            FILE_IN,
            sep="\t",
            usecols=["participant_id", "gmc_exit_q_event_date", "case_solved_family"],
        )
        .check.nrows(msg="Input rows")
        .check.ndups(subset="participant_id")
        .check.print("Keep only most recent EQ outcomes")
        .sort_values("gmc_exit_q_event_date", ascending=False)
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after dropping duplicate IDs")
        .check.value_counts(
            column="case_solved_family",
            msg="Case solved value_counts",
            dropna=False,
        )
        .loc[:, ["participant_id", "case_solved_family"]]
        .pipe(ab.write, FILE_OUT, header=None)
    )


if __name__ == "__main__":
    df = main()

# %%
