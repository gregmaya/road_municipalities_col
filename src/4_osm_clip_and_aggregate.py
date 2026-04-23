"""
4_osm_clip_and_aggregate.py

Clips OpenStreetMap road segments to each municipality zone (cabecera,
centro_poblado, rural) for the 698 selected municipalities across multiple
annual snapshots downloaded from Geofabrik, then aggregates total road
length by zone, OSM road class (fclass), and year.

Data source:
    OSM annual snapshots were manually downloaded from:
    https://download.geofabrik.de/south-america/colombia.html
    File: colombia-YYMMDD-free.shp.zip → roads layer: gis_osm_roads_free_1.shp
    Road class field: fclass (e.g. motorway, primary, residential, track …)
    Snapshots available: 2019-01-01, 2020-01-01, 2021-01-01,
                         2022-01-01, 2023-01-01, 2024-01-01

Inputs:
    data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp
    data/municipios_sel.csv
    data/osm/osm_YYMMDD/gis_osm_roads_free_1.shp  (one directory per snapshot)

Outputs:
    data/outputs/osm_roads_by_class_year.csv
        Columns: mpio_id, municipio, departamento, zone_type, fclass, year,
                 total_length_m

Run from the repo root:
    python src/4_osm_clip_and_aggregate.py
"""

import os
import re
import glob
import geopandas as gpd
import pandas as pd

ZONES_SHP = "data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp"
MPIO_SEL = "data/municipios_sel.csv"
OSM_DIR = "data/osm"
OSM_FILENAME = "gis_osm_roads_free_1.shp"
OUT_CSV = "data/outputs/osm_roads_by_class_year.csv"

CRS = "EPSG:3116"

CLAS_MAP = {
    "1": "cabecera",
    "2": "centro_poblado",
    "3": "rural",
}

_DIR_YEAR_RE = re.compile(r"osm_(\d{2})\d{4}$")


def discover_snapshots(osm_dir=OSM_DIR):
    """Return sorted list of (year: int, shp_path: str) for each valid OSM snapshot."""
    snapshots = []
    for d in sorted(glob.glob(os.path.join(osm_dir, "osm_*"))):
        m = _DIR_YEAR_RE.search(os.path.basename(d))
        if not m:
            continue
        year = 2000 + int(m.group(1))
        shp = os.path.join(d, OSM_FILENAME)
        if os.path.exists(shp):
            snapshots.append((year, shp))
    return snapshots


def load_roads(shp_path):
    """Load an OSM roads shapefile, reproject to CRS, and compute segment lengths."""
    print(f"  Loading {shp_path} ...")
    roads = gpd.read_file(shp_path)
    print(f"    {len(roads):,} segments loaded")
    roads = roads.to_crs(CRS)
    roads.columns = [c.lower() for c in roads.columns]
    roads = roads[["osm_id", "fclass", "geometry"]].copy()
    roads["length"] = roads.geometry.length
    return roads


def load_zones():
    print("Loading MGN_ANM_MPIOCL zones shapefile...")
    zones = gpd.read_file(ZONES_SHP)
    print(f"  Loaded {len(zones):,} zones (national)")

    zones = zones.to_crs(CRS)

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
    return zones


def clip_roads_to_zones(roads, zones):
    print(f"  Clipping roads to {len(zones):,} zones (spatial index)...")
    roads_sindex = roads.sindex
    results = []
    total = len(zones)
    for i, (_, zone) in enumerate(zones.iterrows(), 1):
        if i % 100 == 0 or i == total:
            print(f"    {i}/{total} zones processed", end="\r")
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
        raise RuntimeError("No road segments were clipped — check CRS and geometry validity.")
    return gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=roads.crs)


def main():
    os.makedirs("data/outputs", exist_ok=True)

    zones = load_zones()
    snapshots = discover_snapshots()

    if not snapshots:
        raise RuntimeError(
            f"No OSM snapshots found in {OSM_DIR}. "
            f"Expected subdirectories named osm_YYMMDD/ containing {OSM_FILENAME}."
        )
    print(f"\nFound {len(snapshots)} snapshot(s): {[y for y, _ in snapshots]}")

    all_results = []
    for year, shp_path in snapshots:
        print(f"\n=== Year {year} ===")
        roads = load_roads(shp_path)
        clipped = clip_roads_to_zones(roads, zones)
        clipped["length"] = clipped.geometry.length

        agg = (
            clipped.groupby(
                ["mpio_id", "municipio", "departamento", "zone_type", "fclass"],
                dropna=False,
            )["length"]
            .sum()
            .reset_index()
            .rename(columns={"length": "total_length_m"})
        )
        agg["year"] = year
        all_results.append(agg)
        print(f"  {len(agg):,} rows aggregated for {year}")

    combined = pd.concat(all_results, ignore_index=True)
    combined = combined[
        ["mpio_id", "municipio", "departamento", "zone_type", "fclass", "year", "total_length_m"]
    ]
    combined = combined.sort_values(
        ["year", "mpio_id", "zone_type", "fclass"]
    ).reset_index(drop=True)

    combined.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(combined):,} rows to {OUT_CSV}")
    print("Done.")


if __name__ == "__main__":
    main()
