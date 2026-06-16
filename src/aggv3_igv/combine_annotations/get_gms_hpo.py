"""Get GMS HPO terms"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gms_hpo")


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            snakemake.input[0],
            sep="\t",
            usecols=[
                "participant_id",
                "value_code",
                "normalised_hpo_id",
                "normalised_hpo_term",
            ],
        )
        .check.nrows(msg="Input rows")
        .check.value_counts(column="value_code")
        .loc[pd.col("value_code") == "present"]
        .drop("value_code", axis=1)
        .check.nrows(msg="Rows after keeping 'present' HPO terms")
        .assign(normalised_hpo_term=pd.col("normalised_hpo_term").str.replace(" ", "_"))
        .check.info()
        .dropna()
        .check.nrows(msg="Rows after drop NaNs")
        .groupby("participant_id")
        .agg(
            hpo_terms=("normalised_hpo_term", lambda x: ",".join(x)),
            hpo_ids=("normalised_hpo_id", lambda x: ",".join(x)),
        )
        .reset_index()
        .loc[:, ["participant_id", "hpo_terms", "hpo_ids"]]
        .pipe(ab.write, snakemake.output[0], header=None)
    )


if __name__ == "__main__":
    df = main()
