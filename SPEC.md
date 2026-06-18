# SPEC: `aggv3_igv` CLI Tool

## Context
This is a CLI tool to produce URLs ready for use in the Integrative Genomics Viewer.
Given a set of sample IDs and a
genomic locus, it fetches current metadata from S3, constructs IGV REST API
URLs (`http://localhost:<port>/load?...`), and prints a TSV. The primary use is interactive 
viewing of DNA BAMs in IGV for selected participants and their relations.

---

## Design Overview

```
5 S3 files (boto3 + IAM instance profile, paths from config)
        │
        ▼
  Local cache (~/.cache/aggv3_igv/)
        │
        ▼
  Manifest join (on participant_id)
        │
  filter by supplied IDs (participant ID or sample ID)
        │
  group by (family_grouping, dna_assembly)
        │
  build IGV REST URL per group
        │
  one output row per supplied participant/sample ID
        │
  emit TSV to stdout / -o file
```

---

## Data Sources

Five S3 files are enumerated in the `[s3_files]` section of the config file.

### Join logic

**Step 1 — IDs** (`aggv3_sample_list`): columns `participant_id`,
`family_grouping`, `platekey` (= `sample_id`),
`dragen_karyotypic_sex_estimation` (→ `karyotype_est`), `type`. Deduplicated on
`participant_id` (first row kept).

**Step 2 — DNA paths**: read `gel_file_paths` (filter `file_sub_type == "BAM"`,
keep most recent per `participant_id`) and `gms_file_paths` (filter
`file_sub_type == "CRAM"`, keep most recent per `participant_id`); concatenate
both; rename `genome_build` → `dna_assembly`, `file_path` → `dna_bam`.

**Step 3 — Proband / relation**:
- GEL: from `gel_participant` extract `participant_id`,
  `biological_relationship_to_proband` (→ `relationship_to_proband`),
  `participant_type` (→ `proband` bool: `Proband` = True, `Relative` = False).
- GMS: from `gms_participant` extract `participant_id`,
  `relationship_to_proband`, `referral_participant_is_proband`
  (→ `proband` bool: `"t"` = True, `"f"` = False).
- Concatenate both.

**Step 4 — Merge**: left-join IDs → DNA paths → proband/relation, all on
`participant_id`. This produces the working dataframe for filtering and URL
construction.

### Required columns in joined result

| Column | Source |
|---|---|
| `participant_id` | `aggv3_sample_list` |
| `sample_id` | `platekey` from `aggv3_sample_list` |
| `family_grouping` | `aggv3_sample_list` |
| `karyotype_est` | `dragen_karyotypic_sex_estimation` from `aggv3_sample_list` |
| `dna_bam` | `gel_file_paths` / `gms_file_paths` |
| `dna_assembly` | `gel_file_paths` / `gms_file_paths` |
| `relationship_to_proband` | `gel_participant` / `gms_participant` |
| `proband` | `gel_participant` / `gms_participant` |

---

## Data Access and Caching

S3 files are accessed via **boto3** using the default credential chain (IAM
instance profile in the research environment — no explicit credentials needed).

- On first invocation the tool downloads all five S3 files and saves them to
  `~/.cache/aggv3_igv/` using fixed filenames matching the config keys (e.g.
  `aggv3_sample_list.csv`, `gel_file_paths.tsv`).
- Subsequent invocations load from the cache; no S3 call is made.
- Cache has no TTL. It persists.

---

## Configuration File

Location: `.config/aggv3_igv/config.toml` within the repo (doubles as the
deployed user config; users place it at this path relative to their working
directory or at `~/.config/aggv3_igv/config.toml`).

- The `[genomes]` paths are passed as the `genome=` parameter in IGV URLs.
- For CRAM files, IGV derives the FASTA reference from the genome descriptor.
- If a genome entry is absent from the config, the tool falls back to the IGV
  built-in genome ID string (`hg38`, `hg19`) and emits a warning.

---

## CLI Interface

Entry point: `aggv3_igv`

```
aggv3_igv [OPTIONS] -r/--region LOCUS
```

### Required
| Flag | Description |
|---|---|
| `-r / --region LOCUS` | Genomic locus (see Locus Formats below) |

### ID selection (at least one required)

The `--participants` and `--samples` groups are mutually exclusive — only one
ID type may be used per invocation.

**Participant IDs** (match against `participant_id` column):
| Flag | Description |
|---|---|
| `-p / --participants p1,p2,p3` | Comma-separated participant IDs |
| `-P / --participants-file FILE` | Path to a text file with one participant ID per line (blank lines and `#` comments ignored) |

**Sample IDs** (match against `sample_id` / `platekey` column):
| Flag | Description |
|---|---|
| `-s / --samples s1,s2,s3` | Comma-separated sample IDs (platekeys, e.g. `LP1234567-DNA_A01`) |
| `-S / --samples-file FILE` | Path to a text file with one sample ID per line (blank lines and `#` comments ignored) |

Within each group, the comma flag and the file flag may be combined; the union
of IDs is used.

### Optional
| Flag | Default | Description |
|---|---|---|
| `-o / --output FILE` | stdout | Write TSV to this file instead of stdout |
| `-w / --window BP` | IGV default | Half-window in bp around a variant locus (see below) |
| `--no-participant-id` | off | Exclude `participant_id` from track labels |
| `--assembly BUILD` | from manifest | Override genome build for all samples (e.g. `GRCh38`); samples not matching this build are skipped with a warning |
| `--refresh-cache` | off | Re-download all S3 files and overwrite the local cache, then proceed normally |

---

## Locus Formats

The `-r` / `--region` argument accepts three forms:

| Form | Example | Behaviour |
|---|---|---|
| Coordinate range | `chr7:117,120,000-117,200,000` | Passed through verbatim (commas stripped) |
| Single position | `chr7:117120000` | Passed through verbatim |
| Variant ID | `chr12:1234567:G:A` | Detected by the presence of ≥3 colons; position extracted as `chr12:1234567`. If `--window BP` is given, locus becomes `chr12:{pos-BP}-{pos+BP}`. Otherwise passed as `chr12:1234567` (IGV default zoom). |

Chromosome prefix normalisation: `22` → `chr22` (add prefix if absent).

---

## URL Construction

### IGV REST API URL format
```
http://localhost:<port>/load?file=<path1>,<path2>,...&locus=<locus>&genome=<genome_path>&merge=false&name=<label1>,<label2>,...
```

- Uses the IGV local REST API (not the `igv://` protocol handler).
- Port is read from `[url] port` in the config file (default in the existing
  pipeline: `60151`).
- Multiple files are **comma-separated** within a single `file=` parameter.
- `name=` is a comma-separated list in the same order as `file=`.
- All values are URL-encoded (spaces → `%20`, etc.).
- NFS paths are used verbatim as absolute paths (e.g. `/mnt/data/sample.bam`).

### Grouping logic
1. Look up each supplied ID in the joined manifest using `participant_id` (if
   `--participants`/`--participants-file` was used) or `sample_id` (if
   `--samples`/`--samples-file` was used); unknown IDs produce a warning and
   are skipped.
2. Identify the `(family_grouping, dna_assembly)` groups the matched IDs belong
   to. For each such group, gather **all** family members with a BAM/CRAM in the
   manifest (relations are auto-included, not just the supplied IDs), mirroring
   the historic pipeline.
3. For each group, sort samples by their track label (`name`) value, matching
   the historic pipeline's `.sort_values("name")`.
4. Construct one URL per group, with the group's BAM paths and track labels
   comma-joined in `file=` / `name=`. The same URL appears in multiple output
   rows if more than one supplied ID belongs to the same family group.
5. Output one row **per supplied ID** that was successfully matched.

### Mixed-build handling
If `-a`/`--assembly` is not specified and a supplied sample set spans multiple
assemblies, samples are split by assembly, and **one URL per assembly group**
is emitted. A stderr notice lists the split. This means a participant whose
family has samples in both builds will appear in two output rows (one per
build), each with a different URL.

---

## Track Labels

Default label per track: `{participant_id}_{relationship_to_proband}_{karyotype_est}`

Example: `PT-001234_proband_46XX`

With `--no-participant-id`: `{relationship_to_proband}_{karyotype_est}`

Example: `proband_46XX` (matches the existing pipeline's label format)

---

## Output Format

Tab-separated, written to stdout or `-o FILE`. Always includes a header row.

| Column | Content |
|---|---|
| `participant_id` | Participant ID for the supplied ID |
| `family_id` | `family_grouping` value |
| `genome_assembly` | `GRCh38` or `GRCh37` |
| `igv_url` | The full `http://localhost:<port>/load?...` URL |

One row per successfully matched input ID per assembly. If a participant has
BAM files for both assemblies, they will appear in two rows (one per assembly),
each with a different `igv_url`. If two input IDs belong to the same family
group and assembly, they each get their own row but share the same `igv_url`.

---

## Error Handling

| Condition | Behaviour |
|---|---|
| Unknown participant / sample ID | Warning to stderr; ID skipped |
| No valid IDs remain after lookup | Exit with error and message |
| S3 download fails | Exit with error; suggest `--refresh-cache` or checking IAM permissions |
| Missing config file | Exit with error and instructions |
| Missing `[genomes]` entry for a build | Warning; fall back to IGV built-in genome ID |
| `-a`/`--assembly` override skips some samples | Warning per skipped sample |
| All samples excluded by `-a`/`--assembly` filter | Exit with error |

---

## Dependencies

- `boto3` — S3 file download (uses IAM instance profile; no explicit credentials)
- `pandas` — manifest loading, joining, and filtering
- `tomllib` (stdlib ≥ 3.11) — config parsing

---

## Distribution

- Package: `aggv3_igv` on GitHub, installable via pixi as a PyPI dependency
  (already wired in `pyproject.toml`)
- Entry point defined in `pyproject.toml`:
  ```toml
  [project.scripts]
  aggv3_igv = "aggv3_igv.igv_url.cli:main"
  ```

---

## Files (implemented)

| File | Role |
|---|---|
| `src/aggv3_igv/cli.py` | Argument parsing, orchestration |
| `src/aggv3_igv/config.py` | Config file loading (`[url]` + `[genomes]` + `[s3_files]`) |
| `src/aggv3_igv/manifest.py` | S3 download, caching, join logic (mirrors `combine_annotations`) |
| `src/aggv3_igv/locus.py` | Locus string parsing and normalisation |
| `src/aggv3_igv/url.py` | IGV REST API URL construction |
| `pyproject.toml` | `[project.scripts]` entry and `boto3` dependency |

The code lives directly under `src/aggv3_igv/`. The legacy pipeline scripts
under `src/aggv3_igv/igv_url/` (`construct_igv_url.py`, `tidy_data_for_igv.py`,
`filter_igv_by_cohort.py`) are **not modified**.

---

## Verification

```bash
# 1. Populate cache (first run)
aggv3_igv --participants 111000001,111000002 -r chr22:43011250-43011399

# 2. Variant ID form with window
aggv3_igv --participants-file participants.txt -r chr12:1234567:G:A --window 150

# 3. Write to file, no participant ID in labels
aggv3_igv --participants 111000001 -r chr7:117120000 --no-participant-id -o out.tsv

# 4. Sample (platekey) input
aggv3_igv --samples LP1234567-DNA_A01 -r chr1:1000000-1001000

# 5. Participant with data in both assemblies (expect two rows)
aggv3_igv --participants 111000003 -r chr1:1000000-1001000

# 6. Unknown ID (expect warning + skip)
aggv3_igv --participants INVALID_ID -r chr1:1000000

# 7. Refresh cache then run
aggv3_igv --participants 111000001 -r chr1:1000000 --refresh-cache
```

Confirm output TSV has correct columns, URL scheme is `http://localhost:<port>/load?...`, track
names match the label format, and genome parameter reflects the config file
path.

---

## Open Questions / Deferred

- **Gene name resolution** (e.g. `BRCA1` → coordinates): deferred to a future
  release. Current locus parser rejects gene symbols with a clear error message.
- **`genome_build` normalisation**: the exact string values in the `genome_build`
  column of `gel_file_paths` / `gms_file_paths` need to be verified against
  what the existing pipeline produces (`GRCh38` / `GRCh37`) and normalised if
  they differ.
- **`list-samples` subcommand**: flagged as useful; deferred from initial scope.
