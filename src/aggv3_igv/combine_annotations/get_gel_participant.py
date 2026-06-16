"""Get relationship to proband for GEL samples"""

# %%
import ab_utils as ab
import numpy as np
import pandas as pd


def main() -> pd.DataFrame:
    snakemake = ab.inject_snakemake("annotations_get_gel_participant")

    return (
        ab.read(snakemake.input[0])
        # Usecols fails - possibly due to file structure
        .loc[
            :,
            [
                "participant_id",
                "participant_type",
                "biological_relationship_to_proband",
                "other_biological_relationship_to_proband",
            ],
        ]
        .check.value_counts("biological_relationship_to_proband", dropna=False)
        .assign(
            biological_relationship_to_proband=lambda x: np.where(
                x["biological_relationship_to_proband"] == "Other",
                x["other_biological_relationship_to_proband"],
                x["biological_relationship_to_proband"],
            )
        )
        .check.value_counts(
            "biological_relationship_to_proband",
            dropna=False,
            msg="Relationship value counts after including 'other' relationships",
        )
        .check.ndups("participant_id")
        .pipe(
            ab.write,
            snakemake.output["relation"],
            fn=lambda x: x.loc[
                :, ["participant_id", "biological_relationship_to_proband"]
            ],
            header=None,
        )
        .loc[:, ["participant_id", "participant_type"]]
        .rename(columns={"participant_type": "proband"})
        .replace({"proband":{"Proband":True, "Relative":False}})
        .check.value_counts("proband", dropna=False)
        .dropna().check.nrows("Rows after dropna")
        .pipe(ab.write, snakemake.output["proband"], header=None)
    )


if __name__ == "__main__":
    df = main()

