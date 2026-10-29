from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).parent
OUTPUT = ROOT / "Campus_Navigation_Assistant_Final_Report.pdf"

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#123447"),
        spaceAfter=18,
    )
)
styles.add(
    ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontSize=13,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4C626C"),
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#123447"),
        spaceBefore=12,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=15,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#52666F"),
    )
)


def p(text, style="Body"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [p("&bull; " + item) for item in items]


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E4E5"))
    canvas.line(42, 34, A4[0] - 42, 34)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#60747B"))
    canvas.drawString(42, 22, "Campus Navigation Assistant using A* | AI Course Project")
    canvas.drawRightString(A4[0] - 42, 22, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=A4,
    rightMargin=42,
    leftMargin=42,
    topMargin=42,
    bottomMargin=48,
)
story = []

story += [
    Spacer(1, 0.6 * inch),
    p("FINAL PROJECT REPORT", "Subtitle"),
    p("Campus Navigation Assistant using A*", "ReportTitle"),
    p("Artificial Intelligence | Review 3", "Subtitle"),
    p("Team: Campus Navigation", "Subtitle"),
    p("AI syllabus module: Intelligent Search Techniques", "Subtitle"),
    p("Topic: Heuristic Graph Search using A*", "Subtitle"),
    Spacer(1, 0.25 * inch),
    p(
        "<b>Team members</b><br/>"
        "Rohit Arya (24BCE0819)<br/>"
        "Nayan Gattani (24BDS0117)<br/>"
        "Aditya Kumar (24BCE0205)<br/>"
        "Ashish Kumar (24BKT0059)",
        "Subtitle",
    ),
    Spacer(1, 0.35 * inch),
    p("VIT Vellore", "Subtitle"),
    p("Submitted for the Artificial Intelligence course project", "Subtitle"),
    PageBreak(),
]

story += [
    p("Abstract", "Section"),
    p(
        "This project implements a campus pedestrian navigation assistant for VIT Vellore. "
        "The campus is represented as a weighted graph extracted from OpenStreetMap (OSM), "
        "where walkway intersections are nodes and walkable segments are weighted by physical "
        "distance. A* search uses an admissible straight-line heuristic to find a minimum-cost "
        "route efficiently. Dijkstra's algorithm provides an optimal weighted-search reference, "
        "while Breadth-First Search (BFS) demonstrates the difference between minimizing graph "
        "hops and minimizing physical distance."
    ),
    p(
        "The implementation includes a Python command-line demonstration, a local web service, "
        "and a Leaflet-based browser interface. On the representative Main Gate UNI Entrance "
        "to A Block route, A* and Dijkstra return the same 1,501.9 m physical route distance, while A* "
        "expands 413 nodes compared with Dijkstra's 1,004. BFS returns a 1,570.5 m route "
        "because it optimizes the number of segments rather than their lengths."
    ),
    p(
        "The application also supports a user-selected crowd scenario. Normal, moderate, and "
        "high settings apply 1.00x, 1.25x, and 1.50x multipliers to walkway costs before "
        "re-running all three algorithms. This demonstrates dynamic cost modeling while "
        "clearly distinguishing a scenario setting from live crowd sensing."
    ),
    p("Keywords: A*, Dijkstra, BFS, heuristic search, graph search, campus navigation, OpenStreetMap"),
    p("1. Introduction and Problem Statement", "Section"),
    p(
        "Navigating a large university campus can be time-consuming, particularly when students "
        "must travel between distant academic blocks during short class-transition windows. "
        "A visually direct route is not necessarily a walkable route because campus paths, "
        "junctions, gates, and access roads constrain movement."
    ),
    p(
        "The project models campus navigation as an Artificial Intelligence search problem. "
        "Given a source landmark and a destination landmark, the system returns an estimated "
        "walking route, distance, time, and intermediate checkpoints. The problem is relevant "
        "to the AI syllabus because it applies state-space representation, graph search, "
        "heuristic design, path-cost evaluation, optimality, and empirical algorithm comparison."
    ),
    p(
        "<b>Scope and boundaries:</b> The implementation covers static pedestrian routing on "
        "the supplied OSM-derived graph. It does not claim live traffic prediction, official "
        "building-entrance accuracy, indoor navigation, accessibility-aware routing, or "
        "personalized mobility modeling."
    ),
    p("2. Objectives", "Section"),
]
story += bullets(
    [
        "Represent the VIT Vellore pedestrian network as a weighted graph.",
        "Implement A* search with an admissible Euclidean heuristic.",
        "Implement Dijkstra and BFS as comparison algorithms.",
        "Provide both command-line and browser-based demonstrations.",
        "Compare route cost, nodes expanded, and measured search time.",
        "Validate correctness through automated tests and explicit input checks.",
    ]
)
story += [PageBreak(), p("3. AI Formulation", "Section")]
formulation = [
    ["AI component", "Project representation"],
    ["States (S)", "Walkway intersections, pathway junctions, and snapped landmark nodes."],
    ["Initial state", "The graph node nearest to the selected source landmark."],
    ["Actions", "Move along an adjacent traversable walkway edge."],
    ["Transition model", "Return the neighboring node reached by traversing an edge."],
    ["Goal test", "Check whether the current node is the destination node."],
    ["Path cost g(n)", "Accumulated physical distance in metres, including endpoint snap offsets."],
    ["Heuristic h(n)", "Straight-line Euclidean distance from the node to the goal."],
    ["Evaluation f(n)", "A*: f(n) = g(n) + h(n). Dijkstra uses h(n) = 0."],
]
t = Table([[p(a, "Small") for a in row] for row in formulation], colWidths=[1.55 * inch, 4.85 * inch])
t.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123447")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D6D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F8F8")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
    )
)
story += [t]

story += [
    p("4. Algorithm and Implementation", "Section"),
    p(
        "The team implemented the search core in campus_nav.py using Python's standard library. "
        "No external pathfinding library or pretrained model supplies the route. The browser "
        "interface uses Leaflet for map display, while the local web service calls the same "
        "search functions as the command-line demonstration."
    ),
    p("<b>A* pseudocode</b>"),
    p(
        "<font name='Courier'>A_STAR(graph, start, goal):<br/>"
        "1. frontier := priority queue containing (h(start), start)<br/>"
        "2. g[start] := 0; parent[start] := empty<br/>"
        "3. while frontier is not empty:<br/>"
        "&nbsp;&nbsp;&nbsp;current := remove node with minimum g + h<br/>"
        "&nbsp;&nbsp;&nbsp;if current = goal: reconstruct parent links and return route<br/>"
        "&nbsp;&nbsp;&nbsp;for each neighbor of current: update g, parent and priority if improved<br/>"
        "4. return no route if the frontier becomes empty</font>"
    ),
    p(
        "<b>Key data structures:</b> adjacency lists represent the weighted graph; a binary "
        "heap implements the frontier; dictionaries store best-known costs and parent pointers; "
        "and landmark metadata stores names, categories, and endpoint snap offsets."
    ),
    p("5. Dataset and System Architecture", "Section"),
    p(
        "The included campus_map.json contains 1,965 mapped walkway/access nodes and 2,131 "
        "walkway edges, with named campus places and hostels. Edge weights are calculated from "
        "OSM geometry using great-circle distance. Named landmarks are snapped to nearby "
        "walkway nodes; the straight-line snap offsets are reported separately in the UI."
    ),
    p(
        "The system has three cooperating layers: (1) the browser interface in index.html, "
        "which displays controls, map tiles, route layers, and comparison cards; (2) the "
        "Python web service in web_app.py, which exposes /api/map and /api/route; and (3) "
        "the shared search core in campus_nav.py, which is also used by the CLI."
    ),
    p("6. Algorithms Implemented", "Section"),
    p(
        "<b>A*:</b> A priority queue ranks frontier nodes by f(n) = g(n) + h(n). The "
        "straight-line heuristic is checked against every loaded edge so it cannot overestimate "
        "the cost of traversing that edge. This makes the heuristic admissible and consistent "
        "for the supplied graph."
    ),
    p(
        "<b>Dijkstra:</b> Uses the same weighted graph and priority-queue structure but sets "
        "h(n) to zero. It is the optimal-cost reference for the experiment."
    ),
    p(
        "<b>BFS:</b> Uses a FIFO queue and minimizes the number of graph edges. It ignores "
        "distance weights during search, so its physical route may be longer when segment "
        "lengths differ."
    ),
    p("7. Implementation Workflow", "Section"),
]
story += bullets(
    [
        "Load and validate the JSON graph, node coordinates, landmarks, and edges.",
        "Resolve human-readable landmark names to their nearest mapped graph nodes.",
        "Initialize the selected search algorithm and expand candidate nodes.",
        "Store parent pointers and reconstruct the route when the goal is reached.",
        "Add endpoint snap offsets, estimate walking time at 1.4 m/s, and present the route with its metrics.",
    ]
)
story += [
    p("8. Live Demonstration Evidence", "Section"),
    p(
        "The screenshot was captured from the running local web application for the default "
        "Main Gate UNI Entrance to A Block route under the high crowd scenario. It shows the "
        "campus map, route summary, selected crowd setting, and comparison cards for A*, "
        "Dijkstra, and BFS."
    ),
]
shot = Image(str(ROOT / "app-results-crowd.png"), width=6.9 * inch, height=4.1 * inch)
story += [shot, p("Figure 1. Live browser results: Main Gate UNI Entrance to A Block under the high crowd scenario.", "Small"), PageBreak()]

story += [
    p("9. Experiments and Results", "Section"),
    p(
        "The experiment was run using the included campus_map.json and the command "
        "python campus_nav.py --start main_gate_uni_entrance --goal a_block. "
        "Search time is a single-run measurement and is sensitive to machine load. The table "
        "distinguishes physical distance from crowd-adjusted modeled cost; modeled cost is "
        "reported in m-equivalent and is not additional walking distance."
    ),
]
results = [
    ["Algorithm", "Physical distance", "Modeled cost", "Estimated time", "Nodes expanded"],
    ["A*", "1,501.9 m", "1,501.9 m-eq.", "17.9 min", "413"],
    ["Dijkstra", "1,501.9 m", "1,501.9 m-eq.", "17.9 min", "1,004"],
    ["BFS", "1,570.5 m", "1,570.5 m-eq.", "18.7 min", "958"],
]
rt = Table([[p(x, "Small") for x in row] for row in results], colWidths=[0.9 * inch, 1.35 * inch, 1.45 * inch, 1.2 * inch, 1.25 * inch])
rt.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123447")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D6D9")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E1F5F1")),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#F4F8F8")),
            ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#FFF4D9")),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
    )
)
story += [
    rt,
    Spacer(1, 0.12 * inch),
    p(
        "A* matches Dijkstra's optimal distance while expanding 58.9% fewer nodes "
        "(413 versus 1,004). BFS expands fewer nodes than Dijkstra in this run, but its "
        "fewest-hop objective produces a route 68.6 m longer than the optimal weighted route."
    ),
    p(
        "Under the high crowd scenario (1.50x), the same A* route has a modeled search cost "
        "of 2,238.2 m-equivalent and an estimated time of 26.6 minutes, while its measured "
        "physical distance remains 1,501.9 m. This confirms that the crowd feature changes "
        "route cost and time without misrepresenting physical map distance."
    ),
    p(
        "<b>Sample input:</b> <font name='Courier'>python campus_nav.py --start "
        "main_gate_uni_entrance --goal a_block</font><br/>"
        "<b>Sample output:</b> A* returns a 1,501.9 m route in 17.9 minutes with 413 "
        "expanded nodes. Dijkstra returns the same distance with 1,004 expanded nodes; "
        "BFS returns 1,570.5 m with 958 expanded nodes."
    ),
    PageBreak(),
    p("10. Validation and Testing", "Section"),
    p(
        "The automated test suite contains seven tests and all passed. It checks A* against "
        "Dijkstra on the VIT graph; verifies BFS's different weighted-distance behavior; "
        "handles start-equals-goal and unreachable cases; reports unknown locations; ensures "
        "hostel display names are unique; and rejects an edge that would violate heuristic "
        "admissibility."
    ),
    p("11. Discussion, Limitations and Possible Improvements", "Section"),
]
story += bullets(
    [
        "OSM is community-maintained and is not an official VIT navigation dataset.",
        "Named buildings may not have mapped pedestrian entrances; endpoint snaps are estimates.",
        "The current graph treats edges as undirected and does not model live closures.",
        "Walking time assumes a constant 1.4 m/s and is not a live prediction.",
        "Live crowd sensing, step-free accessibility, terrain difficulty, and personal mobility are not currently modeled. The crowd selector is a user-selected cost scenario.",
        "Map tiles and data are attributed to OpenStreetMap contributors under the ODbL.",
    ]
)
story += [p("12. Team Contributions and References", "Section")]
contributions = [
    ["Member", "Contribution"],
    ["Rohit Arya", "Mapped the campus coordinate graph, defined weighted edges, and implemented baseline Dijkstra/BFS comparison algorithms."],
    ["Nayan Gattani", "Implemented the A* search engine, admissible Euclidean heuristic, path output, and validation logic."],
    ["Aditya Kumar", "Integrated the local web service and browser demonstration workflow, including route API handling and presentation of results."],
    ["Ashish Kumar", "Supported testing, experimental comparison, documentation, and live demonstration preparation."],
]
ct = Table([[p(x, "Small") for x in row] for row in contributions], colWidths=[1.35 * inch, 5.05 * inch])
ct.setStyle(
    TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123447")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D6D9")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F8F8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
    )
)
story += [
    ct,
    p("13. Conclusion", "Section"),
    p(
        "The project demonstrates how informed graph search can solve a practical campus "
        "navigation problem. A* produces the same minimum-distance route as Dijkstra while "
        "using the Euclidean heuristic to reduce exploration. BFS provides a useful contrast: "
        "fewest hops do not necessarily mean shortest walking distance. The working CLI, "
        "browser application, automated tests, and live route comparison satisfy the project "
        "objectives and provide a clear basis for the final demonstration and viva voce."
    ),
    p("References", "Section"),
    p("1. Campus_Navigation_Proposal (2).pdf, submitted project proposal."),
    p("2. OpenStreetMap contributors, campus walkway data and map tiles, accessed through the project dataset."),
    p("3. Project source files: campus_nav.py, web_app.py, index.html, campus_map.json, README.md, and test_campus_nav.py."),
    p(
        "<b>Source-code and demonstration access:</b> The complete source code and test data "
        "are in the submitted project workspace. During evaluation, run "
        "<font name='Courier'>python -m unittest -v</font> for automated tests, "
        "<font name='Courier'>python campus_nav.py</font> for the CLI, or "
        "<font name='Courier'>python web_app.py</font> and open "
        "<font name='Courier'>http://127.0.0.1:8000</font> for the live demonstration."
    ),
    p(
        "<b>Generative-AI assistance disclosure:</b> Generative AI was used as an editing and "
        "documentation assistant to organize this report and presentation, improve wording, "
        "and review test evidence. The team implemented, ran, tested, and verified the AI "
        "search algorithms and remains responsible for the code, results, interpretations, "
        "and viva explanations."
    ),
]

doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(OUTPUT)
