# Data rules

- Data never goes in git. `.gitignore` blocks common sonar and raster formats.
- Location: environment variable `NETSIGHT_DATA_DIR`, default `<repo parent>/netsight-data`.
  Keep it outside OneDrive or any synced folder.
- Layout: `raw/<source>/...` for downloads exactly as published, `processed/<source>/...` for our outputs.
- Every dataset must have an entry in `licences/datasets.yaml` before any file is used.
  Only `tier: commercial` entries may feed commercial model weights; `research_only` data stays
  in benchmarks and is never mixed into training sets.
- Unit tests never read from the data directory; they generate synthetic data.
