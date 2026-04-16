#!/bin/bash
# Reference only — roads_colombia_mainland_segments.parquet is already present in data/overture/
# Do NOT re-run this script unless you intend to replace the existing file.
#
# Bounding box covers Colombia mainland (excluding islands).
# Release date is pinned for reproducibility; update --release to download a newer version.
# Requires: pip install overturemaps

overturemaps download \
  --bbox=-79.00806,-4.22694,-66.85028,12.45833 \
  --release=2025-07-23 \
  -f geoparquet \
  --type=segment \
  -o data/overture/roads_colombia_mainland_segments.parquet
