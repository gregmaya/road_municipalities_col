"""
3_zone_areas.py

Computes the area in km² of each DANE zone type (cabecera, centro_poblado,
rural) for the 698 selected Colombian municipalities.

Inputs:
    data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp
    data/municipios_sel.csv

Output:
    data/outputs/zone_areas_km2.csv

Run from the repo root:
    python src/3_zone_areas.py
"""

import os
import geopandas as gpd
import pandas as pd

ZONES_SHP = "data/dane_mgn/SHP_MGN2018_INTGRD_CLASECS/MGN_ANM_MPIOCL.shp"
MPIO_SEL = "data/municipios_sel.csv"
OUT_CSV = "data/outputs/zone_areas_km2.csv"

CRS = "EPSG:3116"

CLAS_MAP = {
    "1": "cabecera",
    "2": "centro_poblado",
    "3": "rural",
}


def main():
    os.makedirs("data/outputs", exist_ok=True)

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

    print("Calculating areas...")
    zones["area_km2"] = zones.geometry.area / 1_000_000

    print("Aggregating by municipality zone...")
    agg = (
        zones.groupby(["mpio_id", "municipio", "departamento", "zone_type"])["area_km2"]
        .sum()
        .reset_index()
    )
    agg = agg.sort_values(["mpio_id", "zone_type"]).reset_index(drop=True)

    agg.to_csv(OUT_CSV, index=False)
    print(f"Saved to {OUT_CSV}  ({len(agg):,} rows)")

    print("\nZone type summary:")
    summary = agg.groupby("zone_type")["area_km2"].agg(["count", "sum", "mean"])
    summary.columns = ["n_municipalities", "total_area_km2", "mean_area_km2"]
    print(summary.to_string(float_format=lambda x: f"{x:,.2f}"))

    print("\nDone.")


if __name__ == "__main__":
    main()
