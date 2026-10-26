"""Write SOURCES.md (every downloaded file: URL, time, size, sha256) and web/data/sources.json (credits shown in the app)."""
import json
from collections import defaultdict

from common import MANIFEST, ROOT, WEB_DATA, write_json

CREDITS = {
    "nasa_feds": dict(name="NASA Fire Event Data Suite (FEDS), VEDA API", home="https://www.earthdata.nasa.gov/dashboard/",
                      what="12-hourly fire perimeters for the 2020–2021 fires. Method: Chen et al. 2022, Scientific Data, doi:10.1038/s41597-022-01343-0 (California 2012–2020); the VEDA archive extends it.",
                      licence="NASA open data (no restrictions)"),
    "nasa_firms": dict(name="NASA FIRMS VIIRS 375 m active fire archive", home="https://firms.modaps.eosdis.nasa.gov/",
                       what="Satellite fire detections from Suomi NPP and NOAA-20 (VNP14IMG / VJ114IMG).",
                       licence="NASA open data; cite NASA FIRMS"),
    "nifc_wfigs": dict(name="NIFC WFIGS Interagency Fire Perimeters", home="https://data-nifc.opendata.arcgis.com/",
                       what="Official final perimeters and GIS acres; discovery dates.", licence="US Government public domain"),
    "calfire": dict(name="CAL FIRE incident list", home="https://www.fire.ca.gov/incidents",
                    what="All CAL FIRE-listed incidents with reported acres and start dates.", licence="public information published by CAL FIRE (no formal licence stated)"),
    "terrarium": dict(name="AWS Terrain Tiles (Mapzen Terrarium)", home="https://registry.opendata.aws/terrain-tiles/",
                      what="Elevation from USGS 3DEP/NED and SRTM, resampled.", licence="Open; attribution to USGS and the listed source providers"),
    "mrlc_nlcd": dict(name="USGS/MRLC National Land Cover Database", home="https://www.mrlc.gov/",
                      what="Pre-fire land cover (NLCD 2019 for 2020–21 fires, NLCD 2021 for later fires).", licence="US Government public domain"),
    "census_tiger": dict(name="US Census TIGER/Line via TIGERweb", home="https://tigerweb.geo.census.gov/",
                         what="Roads, town points with 2020 population and housing units, state outline, county boundaries, and linear hydrography (rivers and creeks) for the Helene flood tab.", licence="US Government public domain"),
    "osm_overpass": dict(name="OpenStreetMap via Overpass API", home="https://www.openstreetmap.org/copyright",
                         what="Buildings as mapped the day before ignition (small fires only).", licence="ODbL 1.0, © OpenStreetMap contributors"),
    "open_meteo": dict(name="Open-Meteo Historical Weather API (ERA5 / ERA5-Land)", home="https://open-meteo.com/",
                       what="Hourly wind, gusts, humidity and temperature at each fire; hourly precipitation (ERA5) for Hurricane Helene, 24–29 Sep 2024; daily precipitation, ET0 and temperature (ERA5) and ERA5-Land soil moisture on a 0.5 degree grid for the California drought soil-water model.", licence="data CC BY 4.0, free API for non-commercial use; ERA5 © Copernicus/ECMWF"),
    "usgs_quakes": dict(name="USGS Earthquake Catalog (ComCat)", home="https://earthquake.usgs.gov/fdsnws/event/1/",
                        what="Ridgecrest 2019 earthquakes M2+ with time, depth and magnitude.", licence="US Government public domain"),
    "usgs_shakemap": dict(name="USGS ShakeMap", home="https://earthquake.usgs.gov/data/shakemap/",
                          what="Shaking intensity (MMI) grids for the M6.4 and M7.1.", licence="US Government public domain"),
    "usgs_qfaults": dict(name="USGS Quaternary Fault and Fold Database", home="https://www.usgs.gov/programs/earthquake-hazards/faults",
                         what="Fault lines near Ridgecrest.", licence="US Government public domain"),
    "usdm": dict(name="US Drought Monitor", home="https://droughtmonitor.unl.edu/",
                 what="Weekly drought statistics for California and its 58 counties, 2020–2023.",
                 licence="Public domain; credit: The U.S. Drought Monitor is jointly produced by the National Drought Mitigation Center at UNL, USDA and NOAA"),
    "iris_fdsn": dict(name="IRIS FDSN station web service (CI network)", home="https://service.iris.edu/fdsnws/station/1/",
                      what="Locations of Southern California Seismic Network stations (HH/HN channels) used for the what-if warning-time map.", licence="Open metadata (EarthScope/IRIS; network CI: Caltech and USGS)"),
    "usgs_oaf": dict(name="USGS Operational Aftershock Forecast product", home="https://earthquake.usgs.gov/data/oaf/",
                     what="Reasenberg-Jones parameters (a, b, p, c) and observed counts for the Ridgecrest sequence.", licence="US Government public domain"),
    "ngl_gnss": dict(name="Nevada Geodetic Laboratory GNSS time series (IGS14, tenv3)", home="https://geodesy.unr.edu/",
                     what="Daily GNSS positions near Ridgecrest, used for the ground-motion arrows. Cite: Blewitt, Hammond and Kreemer (2018), GPS Solutions.", licence="Free for use with citation"),
    "noaa_hurdat2": dict(name="NOAA National Hurricane Center HURDAT2 best track", home="https://www.nhc.noaa.gov/data/#hurdat",
                         what="Track, maximum sustained wind, central pressure, wind radii and radius of maximum wind for Hurricane Helene (AL092024).", licence="US Government public domain"),
    "noaa_nwps": dict(name="NOAA/NWS National Water Prediction Service API", home="https://water.noaa.gov/",
                      what="Official flood categories (action, minor, moderate, major stage) for the gauges on the Helene flood tab.", licence="US Government public domain"),
    "usgs_ogc": dict(name="USGS Water Data OGC API (field measurements, monitoring locations)", home="https://api.waterdata.usgs.gov/ogcapi/v0/",
                     what="Manual depth-to-water readings (parameter 72019) at California monitoring wells, 2020–2023, with each well's constructed depth and land altitude.", licence="US Government public domain"),
    "dwr_gwl": dict(name="California DWR Groundwater Level monitoring wells (GWL Recently Measured)", home="https://data.cnra.ca.gov/dataset/periodic-groundwater-level-measurements",
                    what="Well depth and perforated (screened) interval for wells that match a USGS well within 150 m.", licence="published openly by California DWR (ArcGIS service); no licence text is stated on the service, so credit DWR"),
    "nasa_grace": dict(name="NASA GRACE Drought Indicators (GRACE-DA), University of Nebraska-Lincoln / NDMC", home="https://nasagrace.unl.edu/",
                       what="Weekly groundwater percentile maps (0.125 degree) from a land model that assimilates GRACE and GRACE-FO gravity data; Matthew Rodell, Bailing Li and colleagues at NASA GSFC.", licence="Public; credit NASA GRACE data assimilation, National Drought Mitigation Center at UNL"),
    "usgs_nwis": dict(name="USGS National Water Information System", home="https://waterdata.usgs.gov/",
                      what="Daily storage of six California reservoirs since 1990 (for the 1991-2020 average by date); 15-minute gage height and discharge at eight western North Carolina gauges during Hurricane Helene; annual peak lists for record context.", licence="US Government public domain (recent data provisional)"),
    "nrcs_awdb": dict(name="USDA NRCS SNOTEL, Air and Water Database REST API", home="https://wcc.sc.egov.usda.gov/awdbRestApi/",
                      what="Daily snow water equivalent and the NRCS daily median at California SNOTEL sites.", licence="US Government public domain"),
    "noaa_mrms": dict(name="NOAA Multi-Radar/Multi-Sensor (MRMS) QPE, NOAA Open Data on AWS", home="https://registry.opendata.aws/noaa-mrms-pds/",
                      what="Hourly radar and gauge rainfall (MultiSensor QPE 1H Pass2) over western North Carolina, 25-30 September 2024.", licence="US Government public domain"),
    "usgs_landslides": dict(name="USGS Hurricane Helene Landslide Inventory (preliminary)", home="https://doi.org/10.5066/P14CHGKS",
                            what="Mapped landslide points and their impact type (road, building, river), served as an ArcGIS feature service.", licence="US Government public domain; preliminary data, subject to revision"),
}

if __name__ == "__main__":
    recs = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = defaultdict(list)
    for r in recs:
        by[r["source"]].append(r)
    used = [k for k in CREDITS if k in by]
    write_json(WEB_DATA / "sources.json", [CREDITS[k] for k in used])
    lines = ["# Sources", "", "Generated by `pipeline/make_sources.py` from `data/raw/manifest.jsonl`. Every file the pipeline downloaded is listed.", ""]
    for k in used:
        c = CREDITS[k]
        lines += [f"## {c['name']}", "", f"- Home: {c['home']}", f"- Used for: {c['what']}", f"- Licence: {c['licence']}",
                  f"- Files: {len(by[k])}, {sum(r['bytes'] for r in by[k]) / 1e6:.1f} MB", "",
                  "| retrieved (UTC) | bytes | sha256 (first 16) | URL |", "|---|---:|---|---|"]
        for r in sorted(by[k], key=lambda r: r["retrieved_utc"]):
            url = r["url"] if len(r["url"]) < 300 else r["url"][:297] + "..."
            lines.append(f"| {r['retrieved_utc']} | {r['bytes']:,} | `{r['sha256'][:16]}` | {url}{' (POST)' if r['post'] else ''} |")
        lines.append("")
    (ROOT / "SOURCES.md").write_text("\n".join(lines), encoding="utf-8")
    print("sources:", {k: len(by[k]) for k in used})
