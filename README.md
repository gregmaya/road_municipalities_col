# Overview

This repository contains an audit of Overture Maps road network data filtered to 698 selected Colombian municipalities. For each municipality, road segments from the **Overture Maps release of 2025-07-23 are clipped to three DANE-defined zone types** — cabecera municipal, centro poblado, and rural disperso — and total road length is reported by Overture road class and zone type. The goal is to characterise the road network composition across urban and rural areas of Colombian municipalities.

---

## Data sources

| Source | Description | CRS | Licence | URL |
|---|---|---|---|---|
| Overture Maps Foundation — release 2025-07-23 | Road segment geometries and classifications (`type=segment`, `subtype=road`) for Colombia mainland | EPSG:4326 | [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/) | https://overturemaps.org |
| DANE — MGN2018 Integrado con CNPV2018, nivel de Clase Censal | Municipality zone polygons (`MGN_ANM_MPIOCL`) pre-cut by DANE into cabecera, centro poblado, and rural disperso areas. Downloaded 2026-04-16. | EPSG:4686 (MAGNA-SIRGAS) | Open — DANE Colombia | https://www.dane.gov.co/files/geoportal-provisional/ |

**Note on zone classification:** The `CLAS_CCDGO` field in `MGN_ANM_MPIOCL` defines three zone types:

| `CLAS_CCDGO` | Zone type | Description |
|---|---|---|
| `1` | `cabecera` | Main urban nucleus (Cabecera Municipal) |
| `2` | `centro_poblado` | Secondary urban nucleus (Centro Poblado) |
| `3` | `rural` | Dispersed rural area |

Not all municipalities have all three zone types. In this dataset, 61 of the 698 selected municipalities have no centro poblado zone.

---

## Repo structure

```
road_municipalities_col/
├── .gitignore                        ← excludes raw data; outputs are tracked
├── README.md
├── requirements.txt                  ← pinned Python dependencies
├── data/                             ← (not tracked, except OUTPOUTS)
│   ├── municipios_sel.csv            ← 698 selected municipalities
│   ├── dane_mgn/                     ← DANE boundary data
│   │   ├── MGN2018_Integrado_CNPV2018_InstructivoUso.pdf
│   │   └── SHP_MGN2018_INTGRD_CLASECS/
│   │       ├── Diccionario_Datos_Niveles_Variables_MGN_CNPV2018Int.xlsx
│   │       └── MGN_ANM_MPIOCL.{shp,dbf,prj,...}
│   ├── overture/                     ← Overture parquet
│   │   └── roads_colombia_mainland_segments.parquet
│   └── outputs/                      ← generated results (tracked)
│       ├── overture_class_audit.csv
│       ├── overture_roads_by_class.csv
│       ├── overture_roads_clipped.gpkg
│       └── zone_areas_km2.csv
├── notebooks/
│   └── 01_exploratory_analysis.ipynb ← exploratory visualisations
└── src/
    ├── 0_download_overture.sh        ← time consuming (ran with care)
    ├── 1_audit_road_classes.py
    ├── 2_clip_and_aggregate.py
    └── 3_zone_areas.py
```

---

## Reproduction

> **Note:** Raw input data (Overture parquet, DANE shapefiles, municipality list) are not included in this repository. Follow steps 1–3 to obtain them before running the scripts.

1. **Create and activate a Python virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Download the Overture roads parquet** (optional — re-download only if needed):

   ```bash
   pip install overturemaps
   bash src/0_download_overture.sh
   ```

   The pinned release is `2025-07-23`. Edit `--release` in the script to use a different version.

3. **Download the DANE MGN2018 boundary data:**

   Obtain `MGN2018 Integrado con CNPV2018, nivel de Clase Censal` from:
   https://www.dane.gov.co/files/geoportal-provisional/

   Place the `SHP_MGN2018_INTGRD_CLASECS/` folder (including all shapefile sidecar files) under `data/dane_mgn/`.

4. **Run the audit script** (road class distribution for all Colombia mainland):

   ```bash
   python src/1_audit_road_classes.py
   ```

5. **Run the clip and aggregate script** (roads clipped to selected municipality zones):

   ```bash
   python src/2_clip_and_aggregate.py
   ```

6. **Run the zone areas script** (polygon areas per municipality zone in km²):

   ```bash
   python src/3_zone_areas.py
   ```

---

## Notebooks

### `notebooks/01_exploratory_analysis.ipynb`

Exploratory visualisations built on top of the four CSV outputs. Open with Jupyter Lab or Notebook from the repo root. All three pipeline scripts must be run first (see Reproduction steps 4–6).

| Section | Description |
|---|---|
| **1. National class audit** | Bar chart of road length (km) by class across the full Colombia mainland Overture dataset, with percentage share labels. |
| **2. Clipped roads by class** | Bar chart of road length (km) by class within the 698 selected municipalities after clipping. |
| **2.2 National vs. clipped scatter** | Scatter plot comparing national audit length to clipped length per road class. Points below the *y = x* diagonal confirm that clipped length is always a subset of national length. |
| **3. Zone-type share by road class** | Horizontal 100% stacked bar chart showing what share of each road class falls in cabecera, centro poblado, and rural zones. Classes sorted by rural share. |
| **4a. Top/bottom municipalities** | Horizontal bar chart of the five municipalities with the most and fewest total road kilometres. |
| **4b. Road class mix by departamento** | Interactive dropdown: select a departamento to see a per-municipality stacked bar chart of road class composition (percentage of total road length). |
| **5. Road density by zone type** | Box-plot distribution of road density (km of road per km² of zone area) across all 698 municipalities, broken out by zone type. |

---

## Outputs

All outputs are in `data/outputs/` and are committed to this repository.

### `overture_class_audit.csv`

Road class distribution across the full Colombia mainland Overture dataset (before filtering to selected municipalities). Used to assess class composition and decide whether any consolidation is needed.

| Column | Description |
|---|---|
| `class` | Overture road class (e.g. `residential`, `trunk`, `unclassified`) |
| `segment_count` | Number of road segments |
| `total_length_m` | Total road length in metres |
| `total_length_km` | Total road length in kilometres |
| `pct_share` | Percentage share of total road length |

### `overture_roads_by_class.csv`

Aggregated road length per municipality zone and Overture road class. This is the primary analytical output.

| Column | Description |
|---|---|
| `mpio_id` | 5-character DIVIPOLA municipality code (e.g. `05001`) |
| `municipio` | Municipality name |
| `departamento` | Department name |
| `zone_type` | DANE zone type: `cabecera`, `centro_poblado`, or `rural` |
| `class` | Overture road class |
| `total_length_m` | Total clipped road length in metres |

### `zone_areas_km2.csv`

Zone polygon areas for the 698 selected municipalities, aggregated from the DANE MGN2018 boundary data.

| Column | Description |
|---|---|
| `mpio_id` | 5-character DIVIPOLA municipality code (e.g. `05001`) |
| `municipio` | Municipality name |
| `departamento` | Department name |
| `zone_type` | DANE zone type: `cabecera`, `centro_poblado`, or `rural` |
| `area_km2` | Total polygon area in km² (EPSG:3116) |

### `overture_roads_clipped.gpkg`

Clipped road segment geometries with zone attribution. Can be opened in QGIS to visually verify that cabecera, centro poblado, and rural segments do not overlap.

| Column | Description |
|---|---|
| `id` | Overture segment ID |
| `class` | Overture road class |
| `zone_type` | DANE zone type |
| `mpio_id` | 5-character DIVIPOLA municipality code |
| `length` | Clipped segment length in metres (EPSG:3116) |
| `geometry` | Clipped linestring geometry |
