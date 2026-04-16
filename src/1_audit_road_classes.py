"""
1_audit_road_classes.py

Loads the Overture Maps road segment parquet, reprojects to EPSG:3116,
and reports the raw class distribution by segment count and total length.

Output: data/outputs/overture_class_audit.csv

Run from the repo root:
    python src/1_audit_road_classes.py
"""

import os
import geopandas as gpd
import pandas as pd

ROADS_PATH = "data/overture/roads_colombia_mainland_segments.parquet"
OUTPUT_PATH = "data/outputs/overture_class_audit.csv"
CRS = "EPSG:3116"


def main():
    os.makedirs("data/outputs", exist_ok=True)

    print("Loading Overture roads parquet...")
    roads = gpd.read_parquet(ROADS_PATH)
    print(f"  Loaded {len(roads):,} segments")

    print(f"Reprojecting to {CRS}...")
    roads = roads.to_crs(CRS)

    roads.columns = [c.lower() for c in roads.columns]

    print("Filtering to subtype == 'road'...")
    roads = roads[roads["subtype"] == "road"].copy()
    print(f"  {len(roads):,} road segments remaining")

    roads = roads[["id", "class", "geometry"]].copy()
    roads["length"] = roads.geometry.length

    print("Aggregating by class...")
    total_length = roads["length"].sum()

    audit = (
        roads.groupby("class", dropna=False)
        .agg(segment_count=("id", "count"), total_length_m=("length", "sum"))
        .reset_index()
    )
    audit["total_length_km"] = audit["total_length_m"] / 1000
    audit["pct_share"] = audit["total_length_m"] / total_length * 100
    audit = audit.sort_values("total_length_m", ascending=False).reset_index(drop=True)

    print("\nOverture road class audit (EPSG:3116, Colombia mainland):")
    print(
        audit.to_string(
            index=False,
            float_format=lambda x: f"{x:,.1f}",
        )
    )

    audit.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
