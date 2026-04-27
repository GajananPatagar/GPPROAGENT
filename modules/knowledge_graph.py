"""
GP PRO AGENT - Knowledge Graph
Visual map of all learned knowledge and relationships.
Shows how concepts connect to each other.
"""
import json, time, threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
import tkinter as tk

class KnowledgeNode:
    def __init__(self, node_id: str, label: str,
                 node_type: str, weight: float = 1.0):
        self.id     = node_id
        self.label  = label
        self.type   = node_type
        self.weight = weight
        self.x      = 0.0
        self.y      = 0.0
        self.connections: Set[str] = set()
        self.metadata = {}

class KnowledgeEdge:
    def __init__(self, source: str, target: str,
                 relation: str, strength: float = 1.0):
        self.source   = source
        self.target   = target
        self.relation = relation
        self.strength = strength

class KnowledgeGraph:
    """
    Visual knowledge graph showing all learned concepts
    and their relationships.
    """
    def __init__(self, brain_root: str,
                 colors: dict, fonts: dict):
        self._path  = Path(brain_root) / "knowledge_graph"
        self._path.mkdir(parents=True, exist_ok=True)
        self.C      = colors
        self.F      = fonts
        self._nodes: Dict[str, KnowledgeNode] = {}
        self._edges: List[KnowledgeEdge]      = []
        self._win   = None
        self._canvas = None
        self._running = False
        self._load()
        self._add_initial_knowledge()

    def _add_initial_knowledge(self):
        """Add base knowledge nodes."""
        base_nodes = [
            # PLC domain
            ("plc_core",    "PLC",           "domain",  3.0),
            ("ladder_logic","Ladder Logic",  "concept", 2.5),
            ("studio5000",  "Studio 5000",   "tool",    2.0),
            ("tia_portal",  "TIA Portal",    "tool",    2.0),
            ("modbus",      "Modbus",        "protocol",1.8),
            ("scada",       "SCADA",         "system",  2.0),
            # Safety
            ("safety_core", "Safety",        "domain",  2.5),
            ("estop",       "E-Stop",        "device",  2.0),
            ("sil",         "SIL Levels",    "concept", 1.8),
            ("loto",        "LOTO",          "procedure",1.8),
            # Code
            ("python_core", "Python",        "language",2.5),
            ("pyautogui",   "PyAutoGUI",     "library", 1.8),
            ("modbus_lib",  "PyModbus",      "library", 1.8),
            # AI modules
            ("gp_pro",      "GP PRO AGENT",  "system",  3.5),
            ("nlp",         "NL Processing", "module",  2.0),
            ("vision",      "Vision AI",     "module",  2.0),
            ("memory_sys",  "Memory",        "module",  2.0),
        ]
        for node_id, label, ntype, weight in base_nodes:
            if node_id not in self._nodes:
                self.add_node(node_id, label, ntype, weight)

        # Base edges
        base_edges = [
            ("gp_pro",     "plc_core",    "specializes_in",  2.0),
            ("gp_pro",     "safety_core", "enforces",        2.0),
            ("gp_pro",     "python_core", "uses",            2.0),
            ("gp_pro",     "vision",      "has_module",      1.5),
            ("gp_pro",     "memory_sys",  "has_module",      1.5),
            ("gp_pro",     "nlp",         "has_module",      1.5),
            ("plc_core",   "ladder_logic","programmed_with", 2.0),
            ("plc_core",   "studio5000",  "programmed_in",   1.8),
            ("plc_core",   "tia_portal",  "programmed_in",   1.8),
            ("plc_core",   "modbus",      "communicates_via",1.5),
            ("plc_core",   "scada",       "monitored_by",    1.5),
            ("safety_core","estop",       "requires",        2.0),
            ("safety_core","sil",         "rated_by",        1.8),
            ("safety_core","loto",        "enforces",        1.8),
            ("python_core","pyautogui",   "uses",            1.5),
            ("python_core","modbus_lib",  "uses",            1.5),
        ]
        for src, tgt, rel, strength in base_edges:
            self.add_edge(src, tgt, rel, strength)

        self._save()

    def add_node(self, node_id: str, label: str,
                 node_type: str,
                 weight: float = 1.0) -> KnowledgeNode:
        node = KnowledgeNode(node_id, label, node_type, weight)
        # Auto-position using simple circular layout
        import math
        n = len(self._nodes)
        angle = (n * 2.357) % (2 * math.pi)
        radius = 200 + n * 15
        node.x = 400 + radius * math.cos(angle)
        node.y = 300 + radius * math.sin(angle)
        self._nodes[node_id] = node
        return node

    def add_edge(self, source: str, target: str,
                 relation: str,
                 strength: float = 1.0) -> KnowledgeEdge:
        edge = KnowledgeEdge(source, target, relation, strength)
        self._edges.append(edge)
        if source in self._nodes:
            self._nodes[source].connections.add(target)
        return edge

    def learn_from_query(self, query: str,
                         brain_used: str,
                         topics: List[str]):
        """Learn new connections from user queries."""
        q = query.lower()
        keywords = {
            "plc":       ("plc_core",    "concept", 1.5),
            "ladder":    ("ladder_logic","concept", 1.5),
            "safety":    ("safety_core", "concept", 1.5),
            "python":    ("python_core", "language",1.5),
            "modbus":    ("modbus",      "protocol",1.5),
            "studio":    ("studio5000",  "tool",    1.5),
            "siemens":   ("tia_portal",  "tool",    1.5),
            "estop":     ("estop",       "device",  1.5),
        }
        detected = []
        for keyword, (node_id, ntype, w) in keywords.items():
            if keyword in q:
                detected.append(node_id)
                if node_id not in self._nodes:
                    self.add_node(node_id, keyword.title(),
                                 ntype, w)
                else:
                    self._nodes[node_id].weight = min(
                        5.0, self._nodes[node_id].weight + 0.1)

        # Add edges between co-occurring concepts
        for i in range(len(detected)):
            for j in range(i+1, len(detected)):
                src, tgt = detected[i], detected[j]
                # Check if edge exists
                exists = any(
                    (e.source==src and e.target==tgt) or
                    (e.source==tgt and e.target==src)
                    for e in self._edges)
                if not exists:
                    self.add_edge(src, tgt, "related_to", 0.5)

        if detected:
            self._save()

    def open_window(self, root):
        """Open interactive knowledge graph window."""
        if self._win and self._win.winfo_exists():
            self._win.lift()
            return
        self._win = tk.Toplevel(root)
        self._win.title("GP PRO AGENT - Knowledge Graph")
        self._win.geometry("950x700")
        self._win.configure(bg=self.C["bg"])
        self._build_graph_ui()

    def _build_graph_ui(self):
        # Header
        hdr = tk.Frame(self._win, bg=self.C["panel"],
                      highlightbackground=self.C["border"],
                      highlightthickness=1)
        hdr.pack(fill="x", padx=8, pady=(8,4))
        tk.Label(hdr, text=">> KNOWLEDGE GRAPH",
                bg=self.C["panel"], fg=self.C["cyan"],
                font=self.F["head"]).pack(side="left", padx=12, pady=6)
        tk.Label(hdr,
                text=f"Nodes: {len(self._nodes)} | Edges: {len(self._edges)}",
                bg=self.C["panel"], fg=self.C["dim"],
                font=self.F["small"]).pack(side="left", padx=8)
        tk.Button(hdr, text="Force Layout",
                 bg=self.C["button"], fg=self.C["white"],
                 font=self.F["small"], relief="flat",
                 command=self._force_layout).pack(side="right", padx=8)

        # Canvas for graph
        self._canvas = tk.Canvas(
            self._win, bg=self.C["input_bg"],
            highlightthickness=0,
            scrollregion=(0, 0, 1200, 900))

        hsb = tk.Scrollbar(self._win, orient="horizontal",
                          command=self._canvas.xview)
        vsb = tk.Scrollbar(self._win, orient="vertical",
                          command=self._canvas.yview)
        self._canvas.configure(
            xscrollcommand=hsb.set,
            yscrollcommand=vsb.set)

        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self._canvas.pack(fill="both", expand=True,
                         padx=8, pady=4)

        # Mouse bindings
        self._canvas.bind("<Button-1>",    self._on_click)
        self._canvas.bind("<B1-Motion>",   self._on_drag)
        self._canvas.bind("<MouseWheel>",  self._on_scroll)
        self._drag_data = {"node": None, "x": 0, "y": 0}
        self._selected  = None

        # Info panel
        self._info_lbl = tk.Label(
            self._win, text="Click a node for details",
            bg=self.C["panel"], fg=self.C["dim"],
            font=self.F["small"])
        self._info_lbl.pack(fill="x", padx=8, pady=4)

        self._draw_graph()

    def _draw_graph(self):
        if not self._canvas:
            return
        self._canvas.delete("all")

        # Node type colors
        type_colors = {
            "domain":    "#00e5ff",
            "concept":   "#00ff88",
            "tool":      "#ff6b2b",
            "protocol":  "#bf5fff",
            "system":    "#ffaa00",
            "module":    "#ff4444",
            "language":  "#ffdd00",
            "device":    "#00ffcc",
            "procedure": "#aaaaff",
        }

        # Draw edges first
        for edge in self._edges:
            src = self._nodes.get(edge.source)
            tgt = self._nodes.get(edge.target)
            if not src or not tgt:
                continue
            alpha = min(255, int(edge.strength * 100))
            self._canvas.create_line(
                src.x, src.y, tgt.x, tgt.y,
                fill=self.C["border"],
                width=max(1, int(edge.strength)),
                dash=(4,4) if edge.strength < 1 else None,
                tags="edge")

        # Draw nodes
        for node_id, node in self._nodes.items():
            color  = type_colors.get(node.type, self.C["dim"])
            radius = max(15, min(35, node.weight * 8))

            # Node circle
            self._canvas.create_oval(
                node.x-radius, node.y-radius,
                node.x+radius, node.y+radius,
                fill=self.C["panel"],
                outline=color,
                width=2,
                tags=(f"node_{node_id}", "node"))

            # Node label
            self._canvas.create_text(
                node.x, node.y,
                text=node.label,
                fill=color,
                font=("Consolas", max(7, int(radius/3))),
                tags=(f"label_{node_id}", "label"))

            # Weight indicator
            if node.weight > 2:
                self._canvas.create_text(
                    node.x, node.y + radius + 8,
                    text=f"w={node.weight:.1f}",
                    fill=self.C["dim"],
                    font=("Consolas", 7),
                    tags="weight")

    def _on_click(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        for node_id, node in self._nodes.items():
            dist = ((x-node.x)**2 + (y-node.y)**2)**0.5
            if dist < 30:
                self._selected = node_id
                conns = list(node.connections)[:5]
                info  = (f"Node: {node.label}\n"
                        f"Type: {node.type}\n"
                        f"Weight: {node.weight:.1f}\n"
                        f"Connections: {len(node.connections)}\n"
                        f"Connected to: {', '.join(conns[:3])}")
                self._info_lbl.config(text=info,
                                     fg=self.C["cyan"])
                self._drag_data = {"node": node_id,
                                   "x": x, "y": y}
                return
        self._drag_data = {"node": None, "x": x, "y": y}

    def _on_drag(self, event):
        if not self._drag_data["node"]:
            return
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        node_id = self._drag_data["node"]
        if node_id in self._nodes:
            self._nodes[node_id].x = x
            self._nodes[node_id].y = y
        self._drag_data["x"] = x
        self._drag_data["y"] = y
        self._draw_graph()

    def _on_scroll(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self._canvas.scale("all",
            self._canvas.canvasx(event.x),
            self._canvas.canvasy(event.y),
            factor, factor)

    def _force_layout(self):
        """Apply force-directed layout."""
        import math
        for _ in range(50):
            for nid, node in self._nodes.items():
                fx = fy = 0
                # Repulsion from all nodes
                for oid, other in self._nodes.items():
                    if oid == nid:
                        continue
                    dx = node.x - other.x
                    dy = node.y - other.y
                    dist = max(1, math.sqrt(dx**2+dy**2))
                    force = 5000 / (dist**2)
                    fx += force * dx/dist
                    fy += force * dy/dist
                # Attraction to connected nodes
                for conn_id in node.connections:
                    conn = self._nodes.get(conn_id)
                    if not conn:
                        continue
                    dx = conn.x - node.x
                    dy = conn.y - node.y
                    dist = max(1, math.sqrt(dx**2+dy**2))
                    force = dist / 100
                    fx += force * dx/dist
                    fy += force * dy/dist
                # Update position
                node.x = max(50, min(1150, node.x + fx*0.1))
                node.y = max(50, min(850,  node.y + fy*0.1))
        self._draw_graph()

    def _save(self):
        try:
            data = {
                "nodes": {
                    k: {"label": v.label, "type": v.type,
                        "weight": v.weight, "x": v.x, "y": v.y}
                    for k, v in self._nodes.items()
                },
                "edges": [
                    {"source": e.source, "target": e.target,
                     "relation": e.relation, "strength": e.strength}
                    for e in self._edges
                ],
            }
            with open(self._path/"graph.json","w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[GRAPH] Save error: {e}")

    def _load(self):
        try:
            path = self._path / "graph.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                for k, v in data.get("nodes",{}).items():
                    node = KnowledgeNode(k, v["label"],
                                        v["type"], v.get("weight",1))
                    node.x = v.get("x", 400)
                    node.y = v.get("y", 300)
                    self._nodes[k] = node
                for e in data.get("edges",[]):
                    self._edges.append(KnowledgeEdge(
                        e["source"], e["target"],
                        e.get("relation","related"),
                        e.get("strength",1.0)))
                print(f"[GRAPH] Loaded {len(self._nodes)} nodes, "
                      f"{len(self._edges)} edges")
        except Exception:
            self._nodes = {}
            self._edges = []
