"""Campus route search: A*, Dijkstra, and BFS using only the Python standard library."""

from __future__ import annotations

import argparse
from collections import deque
import heapq
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

WALKING_SPEED_MPS = 1.4


@dataclass(frozen=True)
class Node:
    node_id: str
    name: str
    x: float
    y: float
    lat: float | None = None
    lon: float | None = None


@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    path: tuple[str, ...]
    cost_m: float
    distance_m: float
    estimated_time_min: float
    nodes_expanded: int
    elapsed_ms: float


class CampusGraph:
    """Undirected walkway graph with locally projected coordinates in meters."""

    def __init__(
        self, nodes: dict[str, Node],
        adjacency: dict[str, list[tuple[str, float, float]]],
        landmarks: list[dict] | None = None,
    ):
        self.nodes = nodes
        self.adjacency = adjacency
        self.landmarks = {item["id"]: item for item in landmarks or []}

    @classmethod
    def from_dict(cls, data: dict) -> CampusGraph:
        nodes: dict[str, Node] = {}
        for record in data.get("nodes", []):
            node_id = str(record["id"])
            if node_id in nodes:
                raise ValueError(f"Duplicate node id: {node_id}")
            x, y = float(record["x"]), float(record["y"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"Coordinates must be finite for node {node_id}")
            lat = float(record["lat"]) if "lat" in record else None
            lon = float(record["lon"]) if "lon" in record else None
            nodes[node_id] = Node(node_id, str(record["name"]), x, y, lat, lon)

        if not nodes:
            raise ValueError("The map must contain at least one node")

        adjacency: dict[str, list[tuple[str, float, float]]] = {
            node_id: [] for node_id in nodes
        }
        for edge in data.get("edges", []):
            start, end = str(edge["from"]), str(edge["to"])
            if start not in nodes or end not in nodes:
                raise ValueError(f"Edge references an unknown node: {start} -> {end}")
            if start == end:
                raise ValueError(f"Self-loop edges are not supported: {start}")

            distance = float(edge["distance_m"])
            crowd_factor = float(edge.get("crowd_factor", 1.0))
            if not math.isfinite(distance) or distance <= 0:
                raise ValueError("Edge distance_m must be a finite positive number")
            if not math.isfinite(crowd_factor) or crowd_factor < 1:
                raise ValueError("crowd_factor must be finite and at least 1")

            straight_line = math.dist(
                (nodes[start].x, nodes[start].y), (nodes[end].x, nodes[end].y)
            )
            if distance + 1e-9 < straight_line:
                raise ValueError(
                    f"Edge {start} -> {end} is shorter than its Euclidean distance; "
                    "the A* heuristic would not be admissible"
                )

            cost = distance * crowd_factor
            adjacency[start].append((end, cost, distance))
            adjacency[end].append((start, cost, distance))

        for neighbors in adjacency.values():
            neighbors.sort(key=lambda item: item[0])

        landmarks = data.get("landmarks", [])
        landmark_ids: set[str] = set()
        for landmark in landmarks:
            landmark_id = str(landmark["id"])
            node_id = str(landmark["node_id"])
            if landmark_id in landmark_ids:
                raise ValueError(f"Duplicate landmark id: {landmark_id}")
            if node_id not in nodes:
                raise ValueError(f"Landmark {landmark_id} references unknown node: {node_id}")
            landmark["id"] = landmark_id
            landmark["node_id"] = node_id
            landmark_ids.add(landmark_id)
        return cls(nodes, adjacency, landmarks)

    @classmethod
    def from_json(cls, path: Path) -> CampusGraph:
        with path.open(encoding="utf-8") as file:
            return cls.from_dict(json.load(file))

    def heuristic(self, current: str, goal: str) -> float:
        first, second = self.nodes[current], self.nodes[goal]
        return math.dist((first.x, first.y), (second.x, second.y))

    def resolve_location(self, location_id: str) -> str:
        if location_id in self.landmarks:
            return self.landmarks[location_id]["node_id"]
        if location_id in self.nodes:
            return location_id
        raise ValueError(f"Unknown location: {location_id}")

    def location_name(self, location_id: str) -> str:
        if location_id in self.landmarks:
            landmark = self.landmarks[location_id]
            return str(landmark.get("display_name", landmark["name"]))
        if location_id in self.nodes:
            return self.nodes[location_id].name
        return location_id

    def location_snap_distance(self, location_id: str) -> float:
        if location_id in self.landmarks:
            return float(self.landmarks[location_id].get("snap_distance_m", 0))
        return 0.0

    def landmark_names_at(self, node_id: str) -> list[str]:
        return [
            str(landmark.get("display_name", landmark["name"]))
            for landmark in self.landmarks.values()
            if landmark["node_id"] == node_id
        ]

    def path_cost(self, path: tuple[str, ...]) -> float:
        total = 0.0
        for start, end in zip(path, path[1:]):
            edge_cost = next(
                (cost for neighbor, cost, _ in self.adjacency[start] if neighbor == end), None
            )
            if edge_cost is None:
                raise ValueError(f"Path contains a non-edge: {start} -> {end}")
            total += edge_cost
        return total

    def path_distance(self, path: tuple[str, ...]) -> float:
        total = 0.0
        for start, end in zip(path, path[1:]):
            distance = next(
                (length for neighbor, _, length in self.adjacency[start] if neighbor == end),
                None,
            )
            if distance is None:
                raise ValueError(f"Path contains a non-edge: {start} -> {end}")
            total += distance
        return total


def _reconstruct_path(parent: dict[str, str], start: str, goal: str) -> tuple[str, ...]:
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return tuple(path)


def _best_first_search(
    graph: CampusGraph,
    start: str,
    goal: str,
    heuristic: Callable[[str, str], float],
    algorithm: str,
    crowd_factor: float = 1.0,
) -> SearchResult | None:
    if not math.isfinite(crowd_factor) or crowd_factor < 1:
        raise ValueError("crowd_factor must be finite and at least 1")
    access_distance = graph.location_snap_distance(start) + graph.location_snap_distance(goal)
    start = graph.resolve_location(start)
    goal = graph.resolve_location(goal)

    began = time.perf_counter()
    frontier: list[tuple[float, int, str, float]] = []
    sequence = 0
    heapq.heappush(frontier, (heuristic(start, goal) * crowd_factor, sequence, start, 0.0))
    best_cost = {start: 0.0}
    parent: dict[str, str] = {}
    closed: set[str] = set()
    expanded = 0

    while frontier:
        _, _, current, cost_so_far = heapq.heappop(frontier)
        if current in closed or cost_so_far > best_cost.get(current, math.inf):
            continue
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            distance = graph.path_distance(path) + access_distance
            total_cost = cost_so_far + access_distance
            return SearchResult(
                algorithm, path, total_cost, distance,
                total_cost / WALKING_SPEED_MPS / 60, expanded,
                (time.perf_counter() - began) * 1000,
            )

        closed.add(current)
        expanded += 1
        for neighbor, edge_cost, _ in graph.adjacency[current]:
            new_cost = cost_so_far + edge_cost * crowd_factor
            if new_cost < best_cost.get(neighbor, math.inf):
                best_cost[neighbor] = new_cost
                parent[neighbor] = current
                sequence += 1
                estimate = new_cost + heuristic(neighbor, goal) * crowd_factor
                heapq.heappush(frontier, (estimate, sequence, neighbor, new_cost))

    return None


def a_star(graph: CampusGraph, start: str, goal: str, crowd_factor: float = 1.0) -> SearchResult | None:
    """Find a minimum-cost route using f(n) = g(n) + Euclidean h(n)."""
    return _best_first_search(graph, start, goal, graph.heuristic, "A*", crowd_factor)


def dijkstra(graph: CampusGraph, start: str, goal: str, crowd_factor: float = 1.0) -> SearchResult | None:
    """Find a minimum-cost route with a zero heuristic (uniform-cost search)."""
    return _best_first_search(graph, start, goal, lambda _node, _goal: 0.0, "Dijkstra", crowd_factor)


def breadth_first_search(
    graph: CampusGraph, start: str, goal: str, crowd_factor: float = 1.0
) -> SearchResult | None:
    """Find a route with the fewest edges; edge weights do not affect exploration."""
    if not math.isfinite(crowd_factor) or crowd_factor < 1:
        raise ValueError("crowd_factor must be finite and at least 1")
    access_distance = graph.location_snap_distance(start) + graph.location_snap_distance(goal)
    start = graph.resolve_location(start)
    goal = graph.resolve_location(goal)

    began = time.perf_counter()
    frontier = deque([start])
    parent: dict[str, str] = {}
    visited = {start}
    expanded = 0

    while frontier:
        current = frontier.popleft()
        if current == goal:
            path = _reconstruct_path(parent, start, goal)
            cost = graph.path_cost(path) * crowd_factor + access_distance
            return SearchResult(
                "BFS", path, cost, graph.path_distance(path) + access_distance,
                cost / WALKING_SPEED_MPS / 60, expanded,
                (time.perf_counter() - began) * 1000,
            )

        expanded += 1
        for neighbor, _, _ in graph.adjacency[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                frontier.append(neighbor)

    return None


def _format_result(
    graph: CampusGraph,
    result: SearchResult | None,
    start: str,
    goal: str,
) -> str:
    if result is None:
        return "No route found."
    route_points = [graph.location_name(start)]
    for node_id in result.path[1:-1]:
        route_points.extend(graph.landmark_names_at(node_id))
    route_points.append(graph.location_name(goal))
    route = " -> ".join(dict.fromkeys(route_points))
    return (
        f"{result.algorithm}: {route}\n"
        f"  Physical distance: {result.distance_m:.1f} m\n"
        f"  Search cost: {result.cost_m:.1f} m-equivalent\n"
        f"  Estimated walking time: {result.estimated_time_min:.1f} min "
        f"(at {WALKING_SPEED_MPS:.1f} m/s)\n"
        f"  Nodes expanded: {result.nodes_expanded}\n"
        f"  Search time: {result.elapsed_ms:.3f} ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare campus route search algorithms")
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("campus_map.json"))
    parser.add_argument("--start", default="main_gate_uni_entrance", help="Starting landmark id")
    parser.add_argument("--goal", default="a_block", help="Destination landmark id")
    parser.add_argument(
        "--crowd-factor", type=float, default=1.0,
        help="Multiply walkway costs to model crowding (1.0=normal, 1.25=moderate, 1.5=high)",
    )
    args = parser.parse_args()

    try:
        graph = CampusGraph.from_json(args.data)
        print(
            f"Campus Navigation Assistant | "
            f"{graph.location_name(args.start)} -> {graph.location_name(args.goal)}"
        )
        print(f"Nodes: {len(graph.nodes)} | Walkways: {sum(map(len, graph.adjacency.values())) // 2}\n")
        for search in (a_star, dijkstra, breadth_first_search):
            print(_format_result(
                graph, search(graph, args.start, args.goal, args.crowd_factor),
                args.start, args.goal
            ))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
