"""Downloaders for every upstream source. All go through common.fetch (cache + manifest)."""
import csv
import io
import json

from common import fetch, fetch_json, RAW

WFIGS = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services"
VEDA = "https://openveda.cloud/api/features/collections"
FIRMS = "https://firms.modaps.eosdis.nasa.gov/data/country"
TERRARIUM = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
NLCD_WMS = "https://www.mrlc.gov/geoserver/mrlc_display/{layer}/wms"
OVERPASS = "https://overpass-api.de/api/interpreter"
METEO = "https://archive-api.open-meteo.com/v1/archive"
CALFIRE = "https://incidents.fire.ca.gov/umbraco/api/IncidentApi/List"
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/0/query"


def calfire_incidents(year):
    return fetch_json(CALFIRE, params=dict(inactive="true", year=year), source="calfire",
                      name=f"incidents_{year}")


def wfigs_query(service, where, name, fields="*", geometry=True, offset=None, extra=None):
    """Page through an ArcGIS FeatureServer query, returning GeoJSON features (EPSG:4326)."""
    feats, start = [], 0
    while True:
        p = dict(where=where, outFields=fields, returnGeometry=str(geometry).lower(), outSR=4326,
                 f="geojson", resultOffset=start, resultRecordCount=1000, orderByFields="OBJECTID")
        if offset:
            p["maxAllowableOffset"] = offset
        p.update(extra or {})
        d = fetch_json(f"{WFIGS}/{service}/FeatureServer/0/query", params=p, source="nifc_wfigs",
                       name=f"{name}_{start}")
        fs = d.get("features", [])
        feats += fs
        if len(fs) < 1000 and not d.get("properties", {}).get("exceededTransferLimit"):
            return feats
        start += len(fs)


def feds(collection, bbox, start, end, name):
    """NASA FEDS (Fire Event Data Suite) archive items from the VEDA OGC API Features endpoint."""
    feats, offset = [], 0
    while True:
        d = fetch_json(f"{VEDA}/public.{collection}/items", source="nasa_feds", name=f"{name}_{offset}",
                       params=dict(bbox=",".join(map(str, bbox)), datetime=f"{start}T00:00:00Z/{end}T23:59:59Z",
                                   limit=40, offset=offset, f="geojson"), timeout=300)
        fs = d.get("features", [])
        feats += fs
        if len(fs) < 40:
            return feats
        offset += 40


def firms_rows(sat, year, bbox, start, end):
    """VIIRS 375 m active-fire rows for a bbox and date window from the FIRMS yearly country archive."""
    big = fetch(f"{FIRMS}/{sat}/{year}/{sat}_{year}_United_States.csv", source="nasa_firms",
                name=f"{sat}_{year}_US", ext="csv", timeout=900)
    out = []
    w, s, e, n = bbox
    with big.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["latitude"]), float(r["longitude"])
            if s <= lat <= n and w <= lon <= e and start <= r["acq_date"] <= end:
                r["sat"] = sat
                out.append(r)
    return out


def terrarium_tile(z, x, y):
    return fetch(TERRARIUM.format(z=z, x=x, y=y), source="terrarium", name=f"{z}_{x}_{y}", ext="png")


def nlcd_png(layer, bbox3857, w, h, name):
    return fetch(NLCD_WMS.format(layer=layer), source="mrlc_nlcd", name=name, ext="png", params=dict(
        SERVICE="WMS", VERSION="1.1.1", REQUEST="GetMap", LAYERS=layer, STYLES="", SRS="EPSG:3857",
        BBOX=",".join(f"{v:.2f}" for v in bbox3857), WIDTH=w, HEIGHT=h, FORMAT="image/png"))


OVERPASS_MIRRORS = [OVERPASS, "https://overpass.private.coffee/api/interpreter",
                    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]


def overpass(query, name):
    last = None
    for url in OVERPASS_MIRRORS:
        try:
            return fetch_json(url, data={"data": query}, source="osm_overpass", name=name, timeout=600, retries=2)
        except RuntimeError as e:
            last = e
            print("   overpass mirror failed:", url, str(e)[:80])
    raise last


def weather(lat, lon, start, end, name):
    return fetch_json(METEO, source="open_meteo", name=name, params=dict(
        latitude=round(lat, 3), longitude=round(lon, 3), start_date=start, end_date=end, timezone="UTC",
        hourly="temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m,vapour_pressure_deficit",
        wind_speed_unit="kmh"))


def ca_boundary():
    return fetch_json(TIGER, source="census_tiger", name="ca_state", params=dict(
        where="STUSAB='CA'", outFields="NAME", outSR=4326, f="geojson", maxAllowableOffset=0.01))


TIGERWEB = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"


def tiger(service, layer, env, name, fields, geometry=True, offset=None):
    """US Census TIGERweb features intersecting a lon/lat envelope, as GeoJSON features."""
    feats, start = [], 0
    while True:
        p = dict(geometry=",".join(f"{v:.5f}" for v in env), geometryType="esriGeometryEnvelope", inSR=4326,
                 spatialRel="esriSpatialRelIntersects", outFields=fields, returnGeometry=str(geometry).lower(),
                 outSR=4326, f="geojson", resultOffset=start, resultRecordCount=5000)
        if offset:
            p["maxAllowableOffset"] = f"{offset:.6f}"
        d = fetch_json(f"{TIGERWEB}/{service}/MapServer/{layer}/query", params=p, source="census_tiger",
                       name=f"{name}_{start}", timeout=300)
        fs = d.get("features", [])
        feats += fs
        if len(fs) < 5000:
            return feats
        start += len(fs)
