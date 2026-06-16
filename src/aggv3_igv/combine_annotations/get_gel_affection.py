"""Get GEL affection status"""

# %%
import ab_utils as ab
import pandas as pd


def main() -> pd.DataFrame:
    snakemake = ab.inject_snakemake("annotations_get_gel_affection")

    return (
        ab.read(
            snakemake.input[0],
            usecols=["participant_id", "affection_status"],
        )
        .dropna(subset=["participant_id"])
        .check.nrows("Rows after dropping nans in participant_id")
        .astype({"participant_id": int})
        .check.dtypes()
        .check.nnulls()
        .check.ndups("participant_id")
        .check.ndups()
        .drop_duplicates()
        .check.nrows("Rows after dropping duplicates")
        .check.value_counts("affection_status", dropna=False)
        .check.print(
            "Where a participant is both affected and unaffected, label them as affected"
        )
        .assign(
            affection_status=lambda x: pd.Categorical(
                x["affection_status"], ["Affected", "Unaffected"], ordered=True
            )
        )
        .sort_values("affection_status")
        .drop_duplicates("participant_id")
        .check.nrows(
            "Rows after dropping 'unaffected' annotation for participants who are both affected and unaffected"
        )
        .pipe(ab.write, snakemake.output[0], header=None)
    )


if __name__ == "__main__":
    df = main()

