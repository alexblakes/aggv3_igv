"""Get GEL HPO terms"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_get_gel_hpo")


def main() -> pd.DataFrame:

    return (
        pd.read_csv(
            snakemake.input[0],
            sep="\t",
            usecols=[
                "participant_id",
                "hpo_present",
                "normalised_hpo_term",
                "normalised_hpo_id",
            ],
        )
        .check.nrows(msg="Input rows")
        .loc[pd.col("hpo_present") == "Yes"]
        .drop("hpo_present", axis=1)
        .check.nrows(msg="Rows after filter for present HPO terms")
        .assign(normalised_hpo_term=pd.col("normalised_hpo_term").str.replace(" ", "_"))
        .check.info()
        .dropna()
        .check.nrows(msg="Rows after drop NaNs")
        .check.head()
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
