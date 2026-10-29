# Campus Navigation Assistant using A*

A working campus navigation project for VIT Vellore. The route-search core is implemented in Python using only the standard library; no pathfinding library is used. A Leaflet map UI calls the same Python search implementation.

## Run the demonstration

Requires Python 3.10 or newer. From this folder, run the prepared Review 2 route:

```powershell
python campus_nav.py
```

Choose a different pair of locations:

```powershell
python campus_nav.py --start main_gate_uni_entrance --goal ev_periyar_library
```

Each run compares A*, Dijkstra (uniform-cost search), and BFS, showing the route, physical distance, crowd-adjusted modeled cost, estimated walking time, nodes expanded, and measured search time. Modeled cost is expressed in km-equivalent and is not additional physical distance. Landmark IDs are listed in `campus_map.json` under `landmarks`; raw walkway-node IDs also work. Supply another JSON graph with `--data path\to\map.json`.

## Web app

Start the local server:

```powershell
python web_app.py
```

Open `http://127.0.0.1:8000`. Choose two campus landmarks, calculate routes, and select A*, Dijkstra, or BFS to see its path on the map. The app needs an internet connection for OpenStreetMap tiles and the Leaflet map library; route calculation itself runs locally in Python.

Run the automated checks:

```powershell
python -m unittest -v
```

## Map and cost model

`campus_map.json` is generated from the OpenStreetMap API for the VIT Vellore area. It currently contains 1,970 mapped walkway/access nodes, 2,137 edges, and named locations including A–H, J, P, S, and T Blocks, MGB, EV Periyar Library, Anna Auditorium, Food Court, 3A Gate, and the Main Gate. The exact counts can change when OSM is updated.

Edge weights are distances in meters computed from consecutive OpenStreetMap path coordinates using great-circle distance. The graph includes mapped footways, paths, pedestrian ways, steps, and campus access/service roads; each edge is treated as traversable in both directions. The CLI and web app accept a crowd factor (1.0 normal, 1.25 moderate, 1.5 high) that multiplies walkway costs and recalculates A*, Dijkstra, and BFS. This is a user-selected scenario, not a live crowd feed. The shown time is a rough estimate using a constant 1.4 m/s walking pace, not a live prediction.

Named buildings do not all have mapped pedestrian entrances. Each selectable landmark is snapped to its nearest mapped walk-network node; route totals include the straight-line snap offsets as approximate connectors, and the offsets are shown in the UI and each option. Treat these as estimates rather than surveyed building entrances. The OSM extract is requested by a bounding box around campus; the included `source` metadata records its bounds and retrieval date. OSM is community-maintained, not an official VIT navigation dataset.

Named OpenStreetMap buildings tagged as dormitories are listed separately under **Hostels**; other mapped landmarks and named blocks appear under **Campus places**. The menu uses the available map labels and does not infer hostel gender or add unnamed buildings. Duplicate names are disambiguated by category and, where needed, by north/south position.

Refresh the graph from OpenStreetMap when connected to the internet:

```powershell
python build_osm_map.py
```

The map tiles and data are attributed to OpenStreetMap contributors under the Open Database License (ODbL). See the map's attribution link for details.

## What each algorithm does

- **A*** keeps the best known cost from the start, `g(n)`, and prioritizes nodes by `f(n) = g(n) + h(n)`. Here `h(n)` is straight-line Euclidean distance to the goal in local projected coordinates. The map loader verifies every edge is at least as long as its projected endpoint distance; with non-negative edge lengths, this makes the heuristic admissible and consistent for this graph.
- **Dijkstra** uses the same weighted graph and priority-queue search but sets `h(n) = 0`. It is the optimal-cost reference for this experiment.
- **BFS** explores by number of graph edges, ignoring edge weights during search. Its reported route cost is measured afterward. It is not generally optimal when segment lengths differ; OSM's choice of where to split paths also affects BFS's hop count.

“Nodes expanded” counts non-goal nodes removed from the frontier and processed. Search times are measured for a single run and are sensitive to machine load; use expansions and route cost as the more interpretable comparison on this small graph.

## Review walkthrough

1. Run the default case and show all three outputs, or start `web_app.py` to compare the routes on the VIT map.
2. Open `a_star` in `campus_nav.py`. Explain the frontier priority, `g` cost, Euclidean `h`, parent map, and path reconstruction.
3. Point out that Dijkstra is A* with a zero heuristic, while BFS minimizes hops rather than distance.
4. Change `--start` and `--goal` to demonstrate a second input. Try an unknown ID to show input validation.
5. Explain the assumptions and limitations: OSM coverage and landmark snaps may be imperfect; edges are assumed undirected; crowd is modeled only through a user-selected scenario multiplier, not live sensing; closures, stairs, and accessibility are not modeled; the time is only a constant-speed estimate.

The test suite checks A* against Dijkstra, demonstrates BFS's different objective, handles start-equals-goal and unreachable cases, and verifies the heuristic safety check.
