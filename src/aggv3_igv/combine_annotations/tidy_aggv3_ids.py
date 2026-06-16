"""Tidy AggV3 participant IDs"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_tidy_aggv3_ids")
FILE_IN = snakemake.input[0]
FILE_OUT = snakemake.output[0]


def main() -> pd.DataFrame:
    return (
        pd.read_csv(
            FILE_IN,
            sep=",",
            low_memory=False,
            usecols=[
                "participant_id",
                "family_grouping",
                "platekey",
                "dragen_karyotypic_sex_estimation",
                "type",
                "study_source",
                "sample_source",
            ],
        )
        .check.nrows(msg="Input rows")
        .rename(columns={"dragen_karyotypic_sex_estimation": "karyotype_est"})
        .check.value_counts(column="karyotype_est", msg="karyotype value counts")
        .check.value_counts(column="type", msg="Cohort value counts")
        .check.value_counts(column="study_source", msg="study value counts")
        .check.function(
            lambda x: x.groupby("study_source")["type"].value_counts(),
            msg="Participant type by study source",
        )
        .check.value_counts(
            column="sample_source", msg="Sample tissue value counts"
        )
        .check.nunique("participant_id")
        .check.nunique("family_grouping")
        .check.nunique("platekey")
        .check.ndups(subset="participant_id")
        .drop_duplicates("participant_id")
        .check.nrows(msg="Rows after dropping duplicates")
        .check.head()
        .pipe(ab.write, FILE_OUT)
    )


if __name__ == "__main__":
    df = main()

# %%
