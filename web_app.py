"""Flask web interface for the VIT campus navigation search core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file

from campus_nav import CampusGraph, a_star, breadth_first_search, dijkstra


ROOT = Path(__file__).parent
MAP_PATH = ROOT / "campus_map.json"
PAGE_PATH = ROOT / "index.html"
MAX_REQUEST_BYTES = 16_384


def _result_payload(graph: CampusGraph, result: Any, search_name: str) -> dict[str, Any]:
    return {
        "algorithm": result.algorithm if result else search_name,
        "distance_m": result.distance_m if result else None,
        "cost_m": result.cost_m if result else None,
        "estimated_time_min": result.estimated_time_min if result else None,
        "nodes_expanded": result.nodes_expanded if result else 0,
        "elapsed_ms": result.elapsed_ms if result else 0,
        "path": [
            {
                "id": node_id,
                "lat": graph.nodes[node_id].lat,
                "lon": graph.nodes[node_id].lon,
            }
            for node_id in (result.path if result else [])
        ],
        "checkpoints": [
            {"id": node_id, "name": name}
            for node_id in (result.path if result else [])
            for name in graph.landmark_names_at(node_id)
        ],
    }


def create_app(graph: CampusGraph, map_data: dict[str, Any]) -> Flask:
    """Create the Flask application with an already validated campus graph."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES

    @app.get("/")
    @app.get("/index.html")
    def index() -> Any:
        try:
            return send_file(PAGE_PATH, mimetype="text/html")
        except OSError as error:
            return jsonify({"error": str(error)}), 500

    @app.get("/api/map")
    def map_data_endpoint() -> Any:
        return jsonify(map_data)

    @app.post("/api/route")
    def route_endpoint() -> Any:
        try:
            if request.content_length is None or not 0 < request.content_length <= MAX_REQUEST_BYTES:
                raise ValueError(f"Request body must be between 1 and {MAX_REQUEST_BYTES} bytes")

            raw_body = request.get_data(cache=False)
            payload = json.loads(raw_body)
            if not isinstance(payload, dict):
                raise TypeError("Request body must be a JSON object")

            start, goal = str(payload["start"]), str(payload["goal"])
            crowd_factor = float(payload.get("crowd_factor", 1.0))
            if crowd_factor < 1:
                raise ValueError("crowd_factor must be at least 1")

            results = []
            for search in (a_star, dijkstra, breadth_first_search):
                result = search(graph, start, goal, crowd_factor)
                results.append(_result_payload(graph, result, search.__name__))

            return jsonify({
                "start": graph.location_name(start),
                "goal": graph.location_name(goal),
                "start_snap_m": graph.landmarks.get(start, {}).get("snap_distance_m", 0),
                "goal_snap_m": graph.landmarks.get(goal, {}).get("snap_distance_m", 0),
                "crowd_factor": crowd_factor,
                "results": results,
            })
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            return jsonify({"error": str(error)}), 400

    @app.errorhandler(413)
    def request_too_large(_error: Any) -> Any:
        return jsonify({"error": f"Request body must not exceed {MAX_REQUEST_BYTES} bytes"}), 400

    @app.errorhandler(404)
    def not_found(_error: Any) -> Any:
        return jsonify({"error": "Not found"}), 404

    return app


def load_project() -> tuple[CampusGraph, dict[str, Any]]:
    try:
        map_data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        graph = CampusGraph.from_dict(map_data)
        if not PAGE_PATH.is_file():
            raise FileNotFoundError(PAGE_PATH)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(str(error)) from error
    return graph, map_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VIT campus navigation Flask app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        graph, map_data = load_project()
    except RuntimeError as error:
        parser.error(str(error))

    app = create_app(graph, map_data)
    print(f"VIT Campus Navigation Assistant running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
