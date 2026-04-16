"""
2_clip_and_aggregate.py

Clips Overture Maps road segments to each municipality zone (cabecera,
centro_poblado, rural) for the 698 selected municipalities, then aggregates
total road length by zone and Overture road class.

Inputs:
    data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp
    data/municipios_sel.csv
    data/overture/roads_colombia_mainland_segments.parquet

Outputs:
    data/outputs/overture_roads_by_class.csv
    data/outputs/overture_roads_clipped.gpkg

Run from the repo root:
    python src/2_clip_and_aggregate.py
"""

import os
import geopandas as gpd
import pandas as pd

ZONES_SHP = "data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp"
MPIO_SEL = "data/municipios_sel.csv"
ROADS_PATH = "data/overture/roads_colombia_mainland_segments.parquet"
OUT_CSV = "data/outputs/overture_roads_by_class.csv"
OUT_GPKG = "data/outputs/overture_roads_clipped.gpkg"

CRS = "EPSG:3116"

CLAS_MAP = {
    "1": "cabecera",
    "2": "centro_poblado",
    "3": "rural",
}


def load_zones():
    print("Loading MGN_ANM_MPIOCL zones shapefile...")
    zones = gpd.read_file(ZONES_SHP)
    print(f"  Loaded {len(zones):,} zones (national)")

    print(f"Reprojecting zones to {CRS}...")
    zones = zones.to_crs(CRS)

    print("Loading selected municipalities...")
    sel = pd.read_csv(MPIO_SEL)
    sel["ID"] = sel["ID"].astype(str).str.zfill(5)

    zones = zones.merge(
        sel.rename(columns={"ID": "MPIO_CDPMP"}),
        on="MPIO_CDPMP",
        how="inner",
    )
    print(f"  {len(zones):,} zones after filtering to {sel['ID'].nunique()} selected municipalities")

    zones["zone_type"] = zones["CLAS_CCDGO"].map(CLAS_MAP)
    zones = zones.rename(columns={"MPIO_CDPMP": "mpio_id"})
    zones = zones[["mpio_id", "municipio", "departamento", "zone_type", "geometry"]].copy()

    # Summary
    print("\nZone type counts:")
    for zt, count in zones["zone_type"].value_counts().sort_index().items():
        print(f"  {zt}: {count}")

    sel_ids = set(sel["ID"])
    present_ids = set(zones["mpio_id"])
    missing = sel_ids - present_ids
    if missing:
        print(f"\nWarning: {len(missing)} selected municipalities have no zones in the shapefile:")
        print(f"  {sorted(missing)}")

    for zt in CLAS_MAP.values():
        present_zt = set(zones[zones["zone_type"] == zt]["mpio_id"])
        missing_zt = present_ids - present_zt
        if missing_zt:
            print(f"  {len(missing_zt)} municipalities have no '{zt}' zone")

    return zones


def load_roads():
    print("\nLoading Overture roads parquet...")
    roads = gpd.read_parquet(ROADS_PATH)
    print(f"  Loaded {len(roads):,} segments")

    print(f"Reprojecting roads to {CRS}...")
    roads = roads.to_crs(CRS)

    roads.columns = [c.lower() for c in roads.columns]
    roads = roads[roads["subtype"] == "road"].copy()
    print(f"  {len(roads):,} road segments after filtering to subtype='road'")

    roads = roads[["id", "class", "geometry"]].copy()
    roads["length"] = roads.geometry.length
    return roads


def clip_roads_to_zones(roads, zones):
    print(f"\nClipping roads to {len(zones):,} zones (spatial index)...")
    roads_sindex = roads.sindex
    results = []
    total = len(zones)
    for i, (_, zone) in enumerate(zones.iterrows(), 1):
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total} zones processed", end="\r")
        idx = list(roads_sindex.intersection(zone.geometry.bounds))
        candidates = roads.iloc[idx]
        intersecting = candidates[candidates.intersects(zone.geometry)]
        if intersecting.empty:
            continue
        clipped = intersecting.copy()
        clipped.geometry = clipped.geometry.intersection(zone.geometry)
        clipped = clipped[~clipped.geometry.is_empty]
        if clipped.empty:
            continue
        for col in ["mpio_id", "municipio", "departamento", "zone_type"]:
            clipped[col] = zone[col]
        results.append(clipped)
    print()

    if not results:
        raise RuntimeError("No road segments were clipped — check that CRS and geometry are valid.")

    clipped_all = gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=roads.crs)
    print(f"  {len(clipped_all):,} clipped road segments")
    return clipped_all


def main():
    os.makedirs("data/outputs", exist_ok=True)

    zones = load_zones()
    roads = load_roads()
    clipped = clip_roads_to_zones(roads, zones)

    print("Recalculating lengths on clipped geometry...")
    clipped["length"] = clipped.geometry.length

    print("Aggregating by municipality zone and road class...")
    agg = (
        clipped.groupby(
            ["mpio_id", "municipio", "departamento", "zone_type", "class"],
            dropna=False,
        )["length"]
        .sum()
        .reset_index()
        .rename(columns={"length": "total_length_m"})
    )
    agg = agg.sort_values(["mpio_id", "zone_type", "class"]).reset_index(drop=True)

    agg.to_csv(OUT_CSV, index=False)
    print(f"Saved aggregated CSV to {OUT_CSV}  ({len(agg):,} rows)")

    gpkg_cols = ["id", "class", "zone_type", "mpio_id", "length", "geometry"]
    clipped[gpkg_cols].to_file(OUT_GPKG, driver="GPKG")
    print(f"Saved clipped roads GPKG to {OUT_GPKG}")

    print("\nDone.")


if __name__ == "__main__":
    main()
