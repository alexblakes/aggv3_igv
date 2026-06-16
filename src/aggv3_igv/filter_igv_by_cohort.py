"""Filter IGV URLs by cohort"""

# %%
import ab_utils as ab
import pandas as pd


def main() -> pd.DataFrame:
    snakemake = ab.inject_snakemake("igv_filter_igv_by_cohort")

    igv = (
        ab.read(snakemake.input.igv)
        .rename(columns={"proband_id": "participant_id"})
        .check.head()
    )

    return (
        ab.read(snakemake.input.variants)
        .merge(igv, how="inner", validate="m:1")
        .check.nrows("Rows after merge with IGV URLs")
        .check.nunique("participant_id")
        .pipe(ab.write, snakemake.output[0])
    )


if __name__ == "__main__":
    df = main()
