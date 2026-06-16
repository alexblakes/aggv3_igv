"""Merge cohort annotations"""

# %%
import ab_utils as ab
import pandas as pd

snakemake = ab.inject_snakemake("cohorts_merge_annotations")
file_ids = snakemake.input["ids"]
file_affection = snakemake.input["affection"]
file_relation = snakemake.input["relation"]
file_proband = snakemake.input["proband"]
file_dna = snakemake.input["dna"]
file_rna = snakemake.input["rna"]
file_eq = snakemake.input["eq"]
file_dx_discovery = snakemake.input["dx_discovery"]
file_hpo = snakemake.input["hpo"]

PID = "participant_id"


def validate_merge(left, right, name):
    left.check.print(f"Merging {name}").check.nrows(msg="Left rows")
    right.check.nrows(msg="Right rows").check.head(3, msg="Right header:")

    return (
        left.merge(right, how="left", validate="1:1", indicator=True)
        .check.value_counts(column="_merge", msg="Merge indicator value counts:")
        .drop("_merge", axis=1)
    )


def main() -> pd.DataFrame:

    ids = pd.read_csv(file_ids, sep="\t", low_memory=False)
    affection = pd.read_csv(
        file_affection, sep="\t", header=None, names=[PID, "affection"]
    )
    relation = ab.read(
        file_relation, header=None, names=[PID, "relationship_to_proband"]
    )
    proband = pd.read_csv(file_proband, sep="\t", header=None, names=[PID, "proband"])
    dna = pd.read_csv(
        file_dna, sep="\t", header=None, names=[PID, "dna_assembly", "dna_bam"]
    )
    rna = pd.read_csv(
        file_rna,
        sep="\t",
        header=None,
        names=[PID, "rna_bam"],
        dtype={"participant_id": "str"},
    )
    eq = pd.read_csv(file_eq, sep="\t", header=None, names=[PID, "case_solved"])
    dx_discovery = pd.read_csv(
        file_dx_discovery,
        sep="\t",
        header=None,
        names=[PID],
        dtype={"participant_id": "str"},
    ).assign(in_dx_discovery=True)
    hpo = pd.read_csv(
        file_hpo, sep="\t", header=None, names=[PID, "hpo_terms", "hpo_ids"]
    )

    return (
        ids.check.nrows(msg="Input rows from tidy IDs")
        .pipe(validate_merge, affection, "affection status")
        .pipe(validate_merge, relation, "relationship to proband")
        .pipe(validate_merge, proband, "proband status")
        .pipe(validate_merge, dna, "DNA BAM paths")
        .pipe(validate_merge, rna, "RNA BAM paths")
        .pipe(validate_merge, eq, "exit questionnaire outcomes")
        .pipe(validate_merge, dx_discovery, "diagnostic discovery outcomes")
        .pipe(validate_merge, hpo, "HPO terms")
        .check.nunique("participant_id")
        .check.value_counts("type", msg="Participant type value counts:")
        .pipe(ab.write, snakemake.output[0])
    )


if __name__ == "__main__":
    df = main()
