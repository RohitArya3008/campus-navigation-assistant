"""Download a VIT Vellore OpenStreetMap extract and build the routing graph."""

from __future__ import annotations

import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path


BBOX = (79.151, 12.963, 79.170, 12.980)
MAP_URL = "https://api.openstreetmap.org/api/0.6/map"
OUTPUT_PATH = Path(__file__).with_name("campus_map.json")
WALKABLE_HIGHWAYS = {
    "footway", "path", "pedestrian", "steps", "service",
    "residential", "unclassified", "tertiary",
}
LANDMARK_NAME = re.compile(
    r"(?i)(\b[a-z]\s*block\b|mgb|mahatma gandhi|"
    r"library|auditorium|food court|food mall|gate|\bsjt\b|tt annexe|"
    r"indoor stadium|indoor sports room|annexe)"
)
EARTH_RADIUS_M = 6_371_008.8


def haversine_m(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(value))


def project(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    x = math.radians(lon - origin_lon) * EARTH_RADIUS_M * math.cos(math.radians(origin_lat))
    y = math.radians(lat - origin_lat) * EARTH_RADIUS_M
    return x, y


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "landmark"


def download_map() -> ET.Element:
    bbox = ",".join(str(value) for value in BBOX)
    url = f"{MAP_URL}?{urllib.parse.urlencode({'bbox': bbox})}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "CampusNavigationAssistant/1.0 (student project)"},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return ET.fromstring(response.read())


def build_graph(root: ET.Element) -> dict:
    raw_nodes = {
        node.attrib["id"]: {
            "lat": float(node.attrib["lat"]),
            "lon": float(node.attrib["lon"]),
            "tags": {tag.attrib["k"]: tag.attrib["v"] for tag in node.findall("tag")},
        }
        for node in root.findall("node")
    }
    origin_lat = sum(node["lat"] for node in raw_nodes.values()) / len(raw_nodes)
    origin_lon = sum(node["lon"] for node in raw_nodes.values()) / len(raw_nodes)

    edge_costs: dict[tuple[str, str], float] = {}
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        highway = tags.get("highway")
        if highway not in WALKABLE_HIGHWAYS or tags.get("access") in {"no", "private"}:
            continue
        refs = [node.attrib["ref"] for node in way.findall("nd")]
        for first_id, second_id in zip(refs, refs[1:]):
            if first_id not in raw_nodes or second_id not in raw_nodes:
                continue
            first, second = raw_nodes[first_id], raw_nodes[second_id]
            projected_first = project(first["lat"], first["lon"], origin_lat, origin_lon)
            projected_second = project(second["lat"], second["lon"], origin_lat, origin_lon)
            straight_line = haversine_m(
                (first["lat"], first["lon"]), (second["lat"], second["lon"])
            )
            projected_distance = math.dist(projected_first, projected_second)
            distance = max(straight_line, projected_distance)
            key = tuple(sorted((first_id, second_id)))
            edge_costs[key] = min(distance, edge_costs.get(key, math.inf))

    connected_ids = {node_id for edge in edge_costs for node_id in edge}
    graph_nodes = []
    for node_id in sorted(connected_ids, key=int):
        raw = raw_nodes[node_id]
        x, y = project(raw["lat"], raw["lon"], origin_lat, origin_lon)
        graph_nodes.append({
            "id": f"osm_{node_id}",
            "name": raw["tags"].get("name", f"Walkway junction {node_id}"),
            "x": x,
            "y": y,
            "lat": raw["lat"],
            "lon": raw["lon"],
        })

    edges = [
        {"from": f"osm_{first}", "to": f"osm_{second}", "distance_m": distance}
        for (first, second), distance in sorted(edge_costs.items(), key=lambda item: item[0])
    ]

    landmark_features: list[tuple[str, str, float, float, str, str]] = []
    for node_id, raw in raw_nodes.items():
        name = raw["tags"].get("name")
        is_hostel = raw["tags"].get("building") in {"dormitory", "hostel"}
        if name and (
            LANDMARK_NAME.search(name) or is_hostel
        ):
            category = "Hostel" if is_hostel else "Campus place"
            landmark_features.append(
                (name, "node", raw["lat"], raw["lon"], node_id, category)
            )

    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        name = tags.get("name")
        is_hostel = tags.get("building") in {"dormitory", "hostel"}
        if not name or not (
            LANDMARK_NAME.search(name) or is_hostel
        ):
            continue
        category = "Hostel" if is_hostel else "Campus place"
        coordinates = [
            raw_nodes[node.attrib["ref"]]
            for node in way.findall("nd")
            if node.attrib["ref"] in raw_nodes
        ]
        if coordinates:
            lat = sum(point["lat"] for point in coordinates) / len(coordinates)
            lon = sum(point["lon"] for point in coordinates) / len(coordinates)
            landmark_features.append(
                (name, "way", lat, lon, way.attrib["id"], category)
            )

    graph_coordinates = {
        node["id"]: (node["lat"], node["lon"]) for node in graph_nodes
    }
    best_features: dict[
        tuple[str, str, str], tuple[float, str, float, float, str, str, str]
    ] = {}
    for name, feature_type, lat, lon, osm_id, category in landmark_features:
        nearest_node, nearest_coordinate = min(
            graph_coordinates.items(),
            key=lambda item: haversine_m((lat, lon), item[1]),
        )
        snap_distance = haversine_m((lat, lon), nearest_coordinate)
        if snap_distance > 150:
            continue
        key = (
            name.casefold(),
            category,
            osm_id if category == "Hostel" and feature_type == "way" else "",
        )
        previous = best_features.get(key)
        if previous is not None and previous[0] <= snap_distance:
            continue
        best_features[key] = (
            snap_distance, nearest_node, lat, lon, feature_type, osm_id, name
        )

    landmarks = []
    used_ids: set[str] = set()
    for (name_key, category, _), (
        snap_distance, nearest_node, lat, lon, feature_type, osm_id, name
    ) in best_features.items():
        landmark_id = slugify(name)
        if landmark_id in used_ids:
            landmark_id = f"{landmark_id}_{slugify(category)}_{slugify(osm_id)}"
        used_ids.add(landmark_id)
        snapped_lat, snapped_lon = graph_coordinates[nearest_node]
        landmarks.append({
            "id": landmark_id,
            "name": name,
            "category": category,
            "node_id": nearest_node,
            "lat": snapped_lat,
            "lon": snapped_lon,
            "feature_lat": lat,
            "feature_lon": lon,
            "snap_distance_m": round(snap_distance, 1),
            "osm_type": feature_type,
            "osm_id": osm_id,
        })

    by_name: dict[str, list[dict]] = {}
    for landmark in landmarks:
        by_name.setdefault(landmark["name"].casefold(), []).append(landmark)
    for same_name in by_name.values():
        if len(same_name) == 1:
            same_name[0]["display_name"] = same_name[0]["name"]
            continue
        by_category: dict[str, list[dict]] = {}
        for landmark in same_name:
            by_category.setdefault(landmark["category"], []).append(landmark)
        for category, matches in by_category.items():
            if len(matches) == 1:
                matches[0]["display_name"] = (
                    f"{matches[0]['name']} · {category}"
                )
                continue
            matches.sort(key=lambda landmark: landmark["feature_lat"], reverse=True)
            directions = {
                2: ("North", "South"),
                3: ("North", "Central", "South"),
            }.get(len(matches), tuple(f"Area {index + 1}" for index in range(len(matches))))
            for landmark, direction in zip(matches, directions):
                landmark["display_name"] = (
                    f"{landmark['name']} · {category} ({direction})"
                )

    if not graph_nodes or not landmarks:
        raise ValueError("The OSM extract did not contain a connected walkway graph and landmarks")

    return {
        "map_name": "VIT Vellore campus (OpenStreetMap walking network)",
        "coordinate_units": "local equirectangular meters; edge weights are OSM geometry distances",
        "source": {
            "name": "OpenStreetMap contributors",
            "url": "https://www.openstreetmap.org/",
            "api_url": MAP_URL,
            "license": "Open Database License (ODbL)",
            "retrieved": date.today().isoformat(),
            "bbox_wgs84": list(BBOX),
            "campus_relation": "https://www.openstreetmap.org/relation/15931944",
            "note": "Landmarks snap to the nearest mapped walk-network node; snap offsets are shown in the app.",
        },
        "nodes": graph_nodes,
        "edges": edges,
        "landmarks": sorted(
            landmarks,
            key=lambda item: (
                item["category"] != "Hostel",
                item["display_name"].casefold(),
            ),
        ),
    }


def main() -> None:
    root = download_map()
    data = build_graph(root)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH.name}: {len(data['nodes'])} walkway nodes, "
        f"{len(data['edges'])} edges, {len(data['landmarks'])} landmarks"
    )
    for landmark in data["landmarks"]:
        print(f"  {landmark['id']}: {landmark['name']} (snap {landmark['snap_distance_m']:.1f} m)")


if __name__ == "__main__":
    main()
