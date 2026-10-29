import unittest
from pathlib import Path

from campus_nav import (
    CampusGraph,
    a_star,
    breadth_first_search,
    dijkstra,
)


class CampusSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = CampusGraph.from_json(Path(__file__).with_name("campus_map.json"))
        cls.small_graph = CampusGraph.from_dict({
            "nodes": [
                {"id": "start", "name": "Start", "x": 0, "y": 0},
                {"id": "middle", "name": "Middle", "x": 5, "y": 0},
                {"id": "goal", "name": "Goal", "x": 10, "y": 0},
            ],
            "edges": [
                {"from": "start", "to": "middle", "distance_m": 5},
                {"from": "middle", "to": "goal", "distance_m": 5},
                {"from": "start", "to": "goal", "distance_m": 12},
            ],
        })
        cls.disconnected_graph = CampusGraph.from_dict({
            "nodes": [
                {"id": "start", "name": "Start", "x": 0, "y": 0},
                {"id": "goal", "name": "Goal", "x": 10, "y": 0},
            ],
            "edges": [],
        })

    def test_a_star_matches_dijkstra_on_vit_walkway_graph(self):
        astar = a_star(self.graph, "main_gate_uni_entrance", "a_block")
        uniform_cost = dijkstra(self.graph, "main_gate_uni_entrance", "a_block")

        self.assertIsNotNone(astar)
        self.assertIsNotNone(uniform_cost)
        self.assertAlmostEqual(astar.cost_m, uniform_cost.cost_m)
        self.assertEqual(astar.path[0], self.graph.resolve_location("main_gate_uni_entrance"))
        self.assertEqual(astar.path[-1], self.graph.resolve_location("a_block"))
        access_distance = (
            self.graph.location_snap_distance("main_gate_uni_entrance")
            + self.graph.location_snap_distance("a_block")
        )
        self.assertAlmostEqual(astar.cost_m, self.graph.path_cost(astar.path) + access_distance)
        self.assertAlmostEqual(
            astar.distance_m, self.graph.path_distance(astar.path) + access_distance
        )
        self.assertAlmostEqual(astar.estimated_time_min, astar.cost_m / 1.4 / 60)

    def test_bfs_minimizes_hops_not_weighted_distance(self):
        bfs = breadth_first_search(self.small_graph, "start", "goal")
        optimal = dijkstra(self.small_graph, "start", "goal")

        self.assertIsNotNone(bfs)
        self.assertIsNotNone(optimal)
        self.assertLess(len(bfs.path), len(optimal.path))
        self.assertGreater(bfs.cost_m, optimal.cost_m)

    def test_start_equal_to_goal_returns_zero_cost(self):
        for search in (a_star, dijkstra, breadth_first_search):
            with self.subTest(algorithm=search.__name__):
                result = search(self.small_graph, "start", "start")
                self.assertIsNotNone(result)
                self.assertEqual(result.path, ("start",))
                self.assertEqual(result.cost_m, 0)
                self.assertEqual(result.nodes_expanded, 0)

    def test_unreachable_goal_returns_no_route(self):
        for search in (a_star, dijkstra, breadth_first_search):
            with self.subTest(algorithm=search.__name__):
                self.assertIsNone(search(self.disconnected_graph, "start", "goal"))

    def test_unknown_location_is_reported(self):
        with self.assertRaisesRegex(ValueError, "Unknown location"):
            a_star(self.graph, "not_on_map", "a_block")

    def test_hostel_landmarks_are_categorized_and_display_names_are_unique(self):
        hostel_landmarks = [
            landmark for landmark in self.graph.landmarks.values()
            if landmark.get("category") == "Hostel"
        ]
        display_names = [
            self.graph.location_name(landmark_id)
            for landmark_id in self.graph.landmarks
        ]

        self.assertTrue(hostel_landmarks)
        self.assertEqual(len(display_names), len(set(display_names)))

    def test_rejects_edge_that_breaks_heuristic_admissibility(self):
        data = {
            "nodes": [
                {"id": "start", "name": "Start", "x": 0, "y": 0},
                {"id": "goal", "name": "Goal", "x": 10, "y": 0},
            ],
            "edges": [{"from": "start", "to": "goal", "distance_m": 9}],
        }
        with self.assertRaisesRegex(ValueError, "not be admissible"):
            CampusGraph.from_dict(data)

    def test_crowd_factor_increases_weighted_cost_without_changing_physical_distance(self):
        normal = a_star(self.small_graph, "start", "goal")
        crowded = a_star(self.small_graph, "start", "goal", crowd_factor=1.5)

        self.assertIsNotNone(normal)
        self.assertIsNotNone(crowded)
        self.assertEqual(normal.path, crowded.path)
        self.assertAlmostEqual(crowded.distance_m, normal.distance_m)
        self.assertAlmostEqual(crowded.cost_m, normal.cost_m * 1.5)


if __name__ == "__main__":
    unittest.main()
