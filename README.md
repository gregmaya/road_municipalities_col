# Overview

This repository audits road network data for **698 selected Colombian municipalities** using two complementary sources: **Overture Maps** (single snapshot, 2025-07-23) and **OpenStreetMap via Geofabrik** (annual snapshots 2019–2024).

For each municipality and data source, road segments are clipped to three **DANE-defined zone types** — cabecera municipal, centro poblado, and rural disperso — and total road length is aggregated by road class and zone type. The OSM time series additionally enables year-over-year analysis of network growth and reclassification patterns.

The goal is to characterise road network composition across urban and rural areas of Colombian municipalities, and to track how OSM coverage has evolved over six annual snapshots.

---

## Data sources

| Source | Description | CRS | Licence | URL |
|---|---|---|---|---|
| Overture Maps Foundation — release 2025-07-23 | Road segment geometries and classifications (`type=segment`, `subtype=road`) for Colombia mainland | EPSG:4326 | [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/) | https://overturemaps.org |
| DANE — MGN2018 Integrado con CNPV2018, nivel de Clase Censal | Municipality zone polygons (`MGN_ANM_MPIOCL`) pre-cut by DANE into cabecera, centro poblado, and rural disperso areas. Downloaded 2026-04-16. | EPSG:4686 (MAGNA-SIRGAS) | Open — DANE Colombia | https://www.dane.gov.co/files/geoportal-provisional/ |
| OpenStreetMap via Geofabrik — annual snapshots 2019–2024 | Road segment shapefiles (`gis_osm_roads_free_1.shp`) for Colombia, one snapshot per year. Manually downloaded from Geofabrik. Road class field: `fclass`. | EPSG:4326 | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) | https://download.geofabrik.de/south-america/colombia.html |

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
├── data/                             ← (not tracked, except outputs)
│   ├── municipios_sel.csv            ← 698 selected municipalities
│   ├── dane_mgn/                     ← DANE boundary data
│   │   ├── MGN2018_Integrado_CNPV2018_InstructivoUso.pdf
│   │   └── SHP_MGN2018_INTGRD_CLASECS/
│   │       ├── Diccionario_Datos_Niveles_Variables_MGN_CNPV2018Int.xlsx
│   │       └── MGN_ANM_MPIOCL.{shp,dbf,prj,...}
│   ├── overture/                     ← Overture parquet
│   │   └── roads_colombia_mainland_segments.parquet
│   ├── osm/                          ← OSM annual snapshots (not tracked)
│   │   ├── osm_190101/gis_osm_roads_free_1.*
│   │   ├── osm_200101/gis_osm_roads_free_1.*
│   │   ├── osm_210101/gis_osm_roads_free_1.*
│   │   ├── osm_220101/gis_osm_roads_free_1.*
│   │   ├── osm_230101/gis_osm_roads_free_1.*
│   │   └── osm_240101/gis_osm_roads_free_1.*
│   └── outputs/                      ← generated results (tracked)
│       ├── overture_class_audit.csv
│       ├── overture_roads_by_class.csv
│       ├── overture_roads_clipped.gpkg
│       ├── osm_roads_by_class_year.csv
│       └── zone_areas_km2.csv
├── notebooks/
│   ├── 01_exploratory_analysis.ipynb ← Overture exploratory visualisations
│   └── 02_osm_yearly_analysis.ipynb  ← OSM yearly road length trends
└── src/
    ├── 0_download_overture.sh        ← time consuming (ran with care)
    ├── 1_audit_road_classes.py
    ├── 2_clip_and_aggregate.py
    ├── 3_zone_areas.py
    └── 4_osm_clip_and_aggregate.py
```

---

## Reproduction

> **Note:** Raw input data (Overture parquet, DANE shapefiles, OSM snapshots, and the municipality list) are not included in this repository. Follow steps 1–3 and 7 to obtain them before running the scripts.

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

   Obtain `MGN2018 Integrado con CNPV2018, nivel de Clase Censal` from [DANE geoportal](https://www.dane.gov.co/files/geoportal-provisional/) and place the `SHP_MGN2018_INTGRD_CLASECS/` folder (including all shapefile sidecar files) under `data/dane_mgn/`.

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

7. **Download the OSM annual snapshots** (manual step):

   Visit [Geofabrik — Colombia](https://download.geofabrik.de/south-america/colombia.html) and download the free shapefile pack for each desired snapshot date. Extract each archive and place the `gis_osm_roads_free_1.*` files into the corresponding directory:

   | Snapshot date | Target directory |
   | --- | --- |
   | 2019-01-01 | `data/osm/osm_190101/` |
   | 2020-01-01 | `data/osm/osm_200101/` |
   | 2021-01-01 | `data/osm/osm_210101/` |
   | 2022-01-01 | `data/osm/osm_220101/` |
   | 2023-01-01 | `data/osm/osm_230101/` |
   | 2024-01-01 | `data/osm/osm_240101/` |

8. **Run the OSM clip and aggregate script** (clips OSM roads to municipality zones for all years):

   ```bash
   python src/4_osm_clip_and_aggregate.py
   ```

   Expects one `data/osm/osm_YYMMDD/` subdirectory per snapshot. Processes all discovered snapshots in a single run (~15–45 min depending on hardware).

---

## Notebooks

### `notebooks/01_exploratory_analysis.ipynb`

Exploratory visualisations built on top of the Overture CSV outputs. Open with Jupyter Lab or Notebook from the repo root. Scripts 1–3 must be run first (see Reproduction steps 4–6).

| Section | Description |
|---|---|
| **1. National class audit** | Bar chart of road length (km) by class across the full Colombia mainland Overture dataset, with percentage share labels. |
| **2. Clipped roads by class** | Bar chart of road length (km) by class within the 698 selected municipalities after clipping. |
| **2.2 National vs. clipped scatter** | Scatter plot comparing national audit length to clipped length per road class. Points below the *y = x* diagonal confirm that clipped length is always a subset of national length. |
| **3. Zone-type share by road class** | Horizontal 100% stacked bar chart showing what share of each road class falls in cabecera, centro poblado, and rural zones. Classes sorted by rural share. |
| **4a. Top/bottom municipalities** | Horizontal bar chart of the five municipalities with the most and fewest total road kilometres. |
| **4b. Road class mix by departamento** | Interactive dropdown: select a departamento to see a per-municipality stacked bar chart of road class composition (percentage of total road length). |
| **5. Road density by zone type** | Box-plot distribution of road density (km of road per km² of zone area) across all 698 municipalities, broken out by zone type. |

### `notebooks/02_osm_yearly_analysis.ipynb`

Visualises how the OSM road network has evolved across the 698 selected municipalities from 2019 to 2024. Run script 4 first (see Reproduction step 8).

| Section | Description |
|---|---|
| **1. National total by year** | Bar chart of total road length (km) across all municipalities and zone types per year, with year-over-year growth table. |
| **2. Total by year × zone type** | Line charts comparing absolute length and a growth index (2019 = 100) for cabecera, centro poblado, and rural zones separately. |
| **3. fclass share by year** | Stacked 100% bar chart showing the composition of the top 10 fclass values across all zones by year. |
| **4. fclass share by zone type × year** | Same breakdown split into three subplots — one per zone type — to reveal whether composition shifts differ across urban and rural areas. |
| **5. YoY absolute change per fclass** | Grouped bar chart of year-over-year kilometre changes per fclass. Apparent shrinkage may reflect OSM reclassification rather than actual road removal. |
| **6. Growth index per fclass** | Line chart normalising each fclass to its 2019 length, making relative growth rates comparable across classes of very different sizes. |
| **7. YoY heatmap by zone type** | Annotated heatmap of km change per fclass transition, one panel per zone type. |
| **8. Track family deep-dive** | Four subsections focusing on OSM's six track grades (`track`, `track_grade1`–`track_grade5`): total track length and share of network by year; absolute and percentage grade breakdown; grade breakdown by zone type; and year-over-year change per grade isolating the 2020→2021 reclassification signal. |

---

## Outputs

All outputs are in `data/outputs/` and are committed to this repository.

### Overture Maps outputs

#### `overture_class_audit.csv`

Road class distribution across the full Colombia mainland Overture dataset (before filtering to selected municipalities). Used to assess class composition and decide whether any consolidation is needed.

| Column | Description |
|---|---|
| `class` | Overture road class (e.g. `residential`, `trunk`, `unclassified`) |
| `segment_count` | Number of road segments |
| `total_length_m` | Total road length in metres |
| `total_length_km` | Total road length in kilometres |
| `pct_share` | Percentage share of total road length |

#### `overture_roads_by_class.csv`

Aggregated road length per municipality zone and Overture road class.

| Column | Description |
|---|---|
| `mpio_id` | 5-character DIVIPOLA municipality code (e.g. `05001`) |
| `municipio` | Municipality name |
| `departamento` | Department name |
| `zone_type` | DANE zone type: `cabecera`, `centro_poblado`, or `rural` |
| `class` | Overture road class |
| `total_length_m` | Total clipped road length in metres |

#### `overture_roads_clipped.gpkg`

Clipped road segment geometries with zone attribution. Can be opened in QGIS to visually verify that cabecera, centro poblado, and rural segments do not overlap.

| Column | Description |
|---|---|
| `id` | Overture segment ID |
| `class` | Overture road class |
| `zone_type` | DANE zone type |
| `mpio_id` | 5-character DIVIPOLA municipality code |
| `length` | Clipped segment length in metres (EPSG:3116) |
| `geometry` | Clipped linestring geometry |

### Shared / boundary outputs

#### `zone_areas_km2.csv`

Zone polygon areas for the 698 selected municipalities, derived from the DANE MGN2018 boundary data. Used by both Overture and OSM analyses for road-density calculations.

| Column | Description |
|---|---|
| `mpio_id` | 5-character DIVIPOLA municipality code (e.g. `05001`) |
| `municipio` | Municipality name |
| `departamento` | Department name |
| `zone_type` | DANE zone type: `cabecera`, `centro_poblado`, or `rural` |
| `area_km2` | Total polygon area in km² (EPSG:3116) |

### OSM outputs

#### `osm_roads_by_class_year.csv`

Aggregated road length per municipality zone, OSM road class (`fclass`), and year. Primary output of `src/4_osm_clip_and_aggregate.py`. OSM's `fclass` field is more granular than Overture's `class` — notably it distinguishes six track grades (`track`, `track_grade1`–`track_grade5`) and includes `*_link` road variants.

| Column | Description |
|---|---|
| `mpio_id` | 5-character DIVIPOLA municipality code (e.g. `05001`) |
| `municipio` | Municipality name |
| `departamento` | Department name |
| `zone_type` | DANE zone type: `cabecera`, `centro_poblado`, or `rural` |
| `fclass` | OSM road class (e.g. `primary`, `residential`, `track`, `track_grade3`, `unclassified`) |
| `year` | Snapshot year (2019–2024) |
| `total_length_m` | Total clipped road length in metres |
