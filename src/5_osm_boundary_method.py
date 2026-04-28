"""
5_osm_boundary_method.py

Replicates the road-length aggregation of script 4 but uses the spatial
method from the deprecated 5_osm_date_comparison.py:
  - Zone polygons are converted to boundary lines.
  - Road segments are split at zone boundaries via gpd.overlay (identity).
  - Split segments are assigned to zones via gpd.sjoin (predicate='within').

Same zone source as script 4: MGN_ANM_MPIOCL.shp (cabecera / centro_poblado
/ rural). Same multi-year snapshot loop.

Outputs:
    data/outputs/osm_roads_boundary_method.csv
    data/outputs/osm_roads_boundary_method.gpkg  (one layer per year)

Run from the repo root:
    python src/5_osm_boundary_method.py
"""

import glob
import os
import re

import geopandas as gpd
import pandas as pd

ZONES_SHP = "data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp"
MPIO_SEL = "data/municipios_sel.csv"
OSM_DIR = "data/osm"
OSM_FILENAME = "gis_osm_roads_free_1.shp"
OUT_CSV = "data/outputs/osm_roads_boundary_method.csv"
OUT_GPKG = "data/outputs/osm_roads_boundary_method.gpkg"

CRS = "EPSG:3116"

CLAS_MAP = {
    "1": "cabecera",
    "2": "centro_poblado",
    "3": "rural",
}

_DIR_YEAR_RE = re.compile(r"osm_(\d{2})\d{4}$")


def discover_snapshots(osm_dir=OSM_DIR):
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
    print(f"  Loading {shp_path} ...")
    roads = gpd.read_file(shp_path)
    print(f"    {len(roads):,} segments loaded")
    roads = roads.to_crs(CRS)
    roads.columns = [c.lower() for c in roads.columns]
    roads = roads[["osm_id", "fclass", "geometry"]].copy()
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
    print(
        f"  {len(zones):,} zones after filtering to {sel['ID'].nunique()} selected municipalities"
    )

    zones["zone_type"] = zones["CLAS_CCDGO"].map(CLAS_MAP)
    zones = zones.rename(columns={"MPIO_CDPMP": "mpio_id"})
    zones = zones[
        ["mpio_id", "municipio", "departamento", "zone_type", "geometry"]
    ].copy()
    return zones


def clip_roads_boundary_method(roads, zones):
    """
    Split OSM road lines at zone polygon boundaries, then assign each split
    segment to the zone it falls within (sjoin predicate='within').

    This mirrors the approach in the deprecated 5_osm_date_comparison.py.
    """
    print(f"  Converting {len(zones):,} zone polygons to boundary lines...")
    zone_boundaries = zones.copy()
    zone_boundaries["geometry"] = zone_boundaries.geometry.boundary

    print("  Splitting road segments at zone boundaries (overlay identity)...")
    roads_split = gpd.overlay(roads, zone_boundaries[["geometry"]], how="identity")
    roads_split = roads_split[~roads_split.geometry.is_empty].copy()
    print(f"    {len(roads_split):,} segments after split")

    print("  Spatial join: assigning split segments to zones (within)...")
    joined = gpd.sjoin(roads_split, zones, how="inner", predicate="within")
    joined = joined.drop(columns=["index_right"])
    joined["length"] = joined.geometry.length
    print(f"    {len(joined):,} segments assigned to zones")

    return joined


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
        joined = clip_roads_boundary_method(roads, zones)

        agg = (
            joined.groupby(
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

        layer_name = f"year_{year}"
        joined.to_file(OUT_GPKG, layer=layer_name, driver="GPKG")
        print(f"  Written GeoPackage layer '{layer_name}'")

    combined = pd.concat(all_results, ignore_index=True)
    combined = combined[
        [
            "mpio_id",
            "municipio",
            "departamento",
            "zone_type",
            "fclass",
            "year",
            "total_length_m",
        ]
    ]
    combined = combined.sort_values(
        ["year", "mpio_id", "zone_type", "fclass"]
    ).reset_index(drop=True)

    combined.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(combined):,} rows to {OUT_CSV}")
    print(f"GeoPackage layers written to {OUT_GPKG}")
    print("Done.")


if __name__ == "__main__":
    main()
