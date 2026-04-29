"""
5_border_proximity.py

For each OSM road segment (across all 7 annual layers in osm_roads_clipped.gpkg),
determines which portion of the segment falls within 25m, 25–50m, 50–100m, or
>100m of the municipal boundary.

Each segment is clipped to 4 non-overlapping rings derived from the dissolved
municipal polygon boundary, and tagged with binary flags in_25m / in_50m / in_100m.
Because the 4 rings partition the municipal polygon completely, summing all rows
per (mpio_id, year) recovers the original total road length — no flag filtering
needed for the length check.

Inputs:
    data/outputs/osm_roads_clipped.gpkg     (layers: year_2019 … year_2025)
    data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp
    data/municipios_sel.csv

Outputs:
    data/outputs/osm_roads_border_proximity.csv
        Columns: osm_id, fclass, length, mpio_id, municipio, departamento,
                 zone_type, year, in_25m, in_50m, in_100m

Run from the repo root:
    python src/5_border_proximity.py
"""

import os
import re

import geopandas as gpd
import pandas as pd

ZONES_SHP = "data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp"
MPIO_SEL = "data/municipios_sel.csv"
IN_GPKG = "data/outputs/osm_roads_clipped.gpkg"
OUT_CSV = "data/outputs/osm_roads_border_proximity.csv"

CRS = "EPSG:3116"

_LAYER_YEAR_RE = re.compile(r"year_(\d{4})$")


def load_municipalities():
    """Load DANE zones, dissolve to one polygon per municipality, filter to 698 selected."""
    print("Loading DANE zones shapefile...")
    zones = gpd.read_file(ZONES_SHP)
    print(f"  {len(zones):,} zones (national)")
    zones = zones.to_crs(CRS)

    sel = pd.read_csv(MPIO_SEL)
    sel["ID"] = sel["ID"].astype(str).str.zfill(5)

    # Merge brings in municipio/departamento columns and filters to 698 selected municipalities
    zones = zones.merge(
        sel.rename(columns={"ID": "MPIO_CDPMP"}),
        on="MPIO_CDPMP",
        how="inner",
    )
    zones = zones.rename(columns={"MPIO_CDPMP": "mpio_id"})

    # Preserve labels before dissolve (dissolve keeps only geometry + group key)
    attrs = (
        zones.groupby("mpio_id")[["municipio", "departamento"]]
        .first()
        .reset_index()
    )
    dissolved = zones.dissolve(by="mpio_id").reset_index()[["mpio_id", "geometry"]]
    dissolved = dissolved.merge(attrs, on="mpio_id")

    print(f"  {len(dissolved):,} municipalities after dissolve and filter")
    return dissolved


def build_ring_partitions(municipalities):
    """
    For each municipal polygon, compute 4 non-overlapping rings keyed by
    distance from the boundary. Each ring is clipped to the municipal polygon
    so that adjacent municipalities cannot share road segments.

    Returns dict: mpio_id -> list of (ring_geom, flags_dict).

    Rings (flags: in_25m, in_50m, in_100m):
        ring_25:   0–25m    True,  True,  True
        ring_50:   25–50m   False, True,  True
        ring_100:  50–100m  False, False, True
        ring_int:  >100m    False, False, False
    """
    print("Precomputing boundary buffer rings per municipality...")
    partitions = {}
    total = len(municipalities)
    for i, (_, row) in enumerate(municipalities.iterrows(), 1):
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total} municipalities", end="\r")
        poly = row.geometry
        boundary = poly.boundary
        buf_25 = boundary.buffer(25)
        buf_50 = boundary.buffer(50)
        buf_100 = boundary.buffer(100)

        # Clip each ring to the municipal polygon — prevents cross-municipality assignment
        ring_25 = buf_25.intersection(poly)
        ring_50 = buf_50.difference(buf_25).intersection(poly)
        ring_100 = buf_100.difference(buf_50).intersection(poly)
        ring_int = poly.difference(buf_100)

        partitions[row["mpio_id"]] = [
            (ring_25,  {"in_25m": True,  "in_50m": True,  "in_100m": True}),
            (ring_50,  {"in_25m": False, "in_50m": True,  "in_100m": True}),
            (ring_100, {"in_25m": False, "in_50m": False, "in_100m": True}),
            (ring_int, {"in_25m": False, "in_50m": False, "in_100m": False}),
        ]
    print()
    return partitions


def clip_roads_to_rings(roads, ring_partitions):
    """Clip road segments to each ring partition and attach proximity flags."""
    roads_sindex = roads.sindex
    results = []
    total = len(ring_partitions)
    for i, (mpio_id, rings) in enumerate(ring_partitions.items(), 1):
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total} municipalities processed", end="\r")
        for ring_geom, flags in rings:
            if ring_geom is None or ring_geom.is_empty:
                continue
            idx = list(roads_sindex.intersection(ring_geom.bounds))
            if not idx:
                continue
            candidates = roads.iloc[idx]
            intersecting = candidates[candidates.intersects(ring_geom)]
            if intersecting.empty:
                continue
            clipped = intersecting.copy()
            clipped.geometry = clipped.geometry.intersection(ring_geom)
            clipped = clipped[~clipped.geometry.is_empty]
            if clipped.empty:
                continue
            clipped["in_25m"] = flags["in_25m"]
            clipped["in_50m"] = flags["in_50m"]
            clipped["in_100m"] = flags["in_100m"]
            results.append(clipped)
    print()
    if not results:
        raise RuntimeError("No segments produced — check CRS and geometry validity.")
    return gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=roads.crs)


def discover_layers(gpkg_path):
    """Return sorted list of (year: int, layer_name: str) from the GPKG."""
    layer_info = gpd.list_layers(gpkg_path)
    layers = []
    for name in layer_info["name"]:
        m = _LAYER_YEAR_RE.match(name)
        if m:
            layers.append((int(m.group(1)), name))
    return sorted(layers)


def main():
    os.makedirs("data/outputs", exist_ok=True)

    municipalities = load_municipalities()
    ring_partitions = build_ring_partitions(municipalities)

    layers = discover_layers(IN_GPKG)
    if not layers:
        raise RuntimeError(f"No year_YYYY layers found in {IN_GPKG}")
    print(f"\nFound {len(layers)} layer(s): {[y for y, _ in layers]}")

    all_results = []
    for year, layer_name in layers:
        print(f"\n=== Year {year} ===")
        roads = gpd.read_file(IN_GPKG, layer=layer_name)
        print(f"  {len(roads):,} segments loaded")
        assert roads.crs.to_epsg() == 3116, (
            f"Expected EPSG:3116 for layer {layer_name}, got {roads.crs}"
        )

        tagged = clip_roads_to_rings(roads, ring_partitions)
        tagged["length"] = tagged.geometry.length
        tagged["year"] = year
        print(f"  {len(tagged):,} sub-segments after ring clipping")
        all_results.append(tagged)

    combined = pd.concat(all_results, ignore_index=True)
    out_cols = [
        "osm_id", "fclass", "length", "mpio_id", "municipio", "departamento",
        "zone_type", "year", "in_25m", "in_50m", "in_100m",
    ]
    combined = combined[out_cols]
    combined = combined.sort_values(
        ["year", "mpio_id", "zone_type", "fclass"]
    ).reset_index(drop=True)
    combined.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {len(combined):,} rows to {OUT_CSV}")
    print("Done.")


if __name__ == "__main__":
    main()
