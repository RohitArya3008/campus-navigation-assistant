"""Local web interface for the VIT campus navigation search core."""

from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from campus_nav import CampusGraph, a_star, breadth_first_search, dijkstra


ROOT = Path(__file__).parent
MAP_PATH = ROOT / "campus_map.json"
PAGE_PATH = ROOT / "index.html"


class CampusHandler(BaseHTTPRequestHandler):
    graph: CampusGraph
    map_data: dict[str, Any]

    def __init__(self, *args: Any, graph: CampusGraph, map_data: dict[str, Any], **kwargs: Any):
        self.graph = graph
        self.map_data = map_data
        super().__init__(*args, **kwargs)

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(body, "application/json; charset=utf-8", status)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            try:
                self._send(PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
            except OSError as error:
                self._send_json({"error": str(error)}, 500)
            return
        if self.path == "/api/map":
            self._send_json(self.map_data)
            return
        self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/api/route":
            self._send_json({"error": "Not found"}, 404)
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 16_384:
                raise ValueError("Request body must be between 1 and 16,384 bytes")
            request = json.loads(self.rfile.read(content_length))
            start, goal = str(request["start"]), str(request["goal"])
            crowd_factor = float(request.get("crowd_factor", 1.0))
            if crowd_factor < 1:
                raise ValueError("crowd_factor must be at least 1")
            searches = (a_star, dijkstra, breadth_first_search)
            results = []
            for search in searches:
                result = search(self.graph, start, goal, crowd_factor)
                results.append({
                    "algorithm": result.algorithm if result else search.__name__,
                    "distance_m": result.distance_m if result else None,
                    "cost_m": result.cost_m if result else None,
                    "estimated_time_min": result.estimated_time_min if result else None,
                    "nodes_expanded": result.nodes_expanded if result else 0,
                    "elapsed_ms": result.elapsed_ms if result else 0,
                    "path": [
                        {
                            "id": node_id,
                            "lat": self.graph.nodes[node_id].lat,
                            "lon": self.graph.nodes[node_id].lon,
                        }
                        for node_id in result.path
                    ] if result else [],
                    "checkpoints": [
                        {"id": node_id, "name": name}
                        for node_id in (result.path if result else [])
                        for name in self.graph.landmark_names_at(node_id)
                    ],
                })
            self._send_json({
                "start": self.graph.location_name(start),
                "goal": self.graph.location_name(goal),
                "start_snap_m": self.graph.landmarks.get(start, {}).get("snap_distance_m", 0),
                "goal_snap_m": self.graph.landmarks.get(goal, {}).get("snap_distance_m", 0),
                "crowd_factor": crowd_factor,
                "results": results,
            })
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._send_json({"error": str(error)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the VIT campus navigation web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        map_data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        graph = CampusGraph.from_dict(map_data)
        if not PAGE_PATH.is_file():
            raise FileNotFoundError(PAGE_PATH)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))

    handler = partial(CampusHandler, graph=graph, map_data=map_data)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"VIT Campus Navigation Assistant running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
