"""Path graphs `<layer>.graph.json` (world-tech §2.5): data, deterministic writer, reader.

Coordinates in the file are grid tiles. Node ids are local to the layer; portals share ids across
layers. The writer emits one node, edge or lane per line in a fixed key order, so diffs are small
and two builds give the same bytes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

VERSION = 1
NODE_KINDS = {None, "dest", "door", "gate", "station", "portal"}
EDGE_KINDS = {"street", "road", "track", "stair", "ramp", "towpath", "quay", "bridge", "ford"}
LANE_KINDS = {"sea", "river", "towpath"}


@dataclass
class Node:
    id: str
    at: tuple[int, int]
    kind: str | None = None


@dataclass
class Edge:
    a: str
    b: str
    kind: str
    via: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Port:
    id: str
    at: int
    slot: str | None = None


@dataclass
class Lane:
    id: str
    kind: str
    points: list[tuple[int, int]]
    ports: list[Port] = field(default_factory=list)


@dataclass
class Graph:
    layer: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    lanes: list[Lane] = field(default_factory=list)

    def node(self, node_id: str) -> Node | None:
        return next((n for n in self.nodes if n.id == node_id), None)


def _j(x) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(", ", ": "))


def write_graph(g: Graph) -> str:
    lines = ["{", f'  "version": {VERSION},', f'  "layer": {_j(g.layer)},', '  "nodes": [']
    for i, n in enumerate(g.nodes):
        d = {"id": n.id, "at": list(n.at)}
        if n.kind:
            d["kind"] = n.kind
        lines.append("    " + _j(d) + ("," if i + 1 < len(g.nodes) else ""))
    lines.append("  ],")
    lines.append('  "edges": [')
    for i, e in enumerate(g.edges):
        d = {"a": e.a, "b": e.b, "kind": e.kind}
        if e.via:
            d["via"] = [list(p) for p in e.via]
        lines.append("    " + _j(d) + ("," if i + 1 < len(g.edges) else ""))
    lines.append("  ],")
    lines.append('  "lanes": [')
    for i, ln in enumerate(g.lanes):
        ports = []
        for p in ln.ports:
            pd = {"id": p.id, "at": p.at}
            if p.slot:
                pd["slot"] = p.slot
            ports.append(pd)
        d = {"id": ln.id, "kind": ln.kind, "points": [list(p) for p in ln.points], "ports": ports}
        lines.append("    " + _j(d) + ("," if i + 1 < len(g.lanes) else ""))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def read_graph(text: str) -> Graph:
    doc = json.loads(text)
    if doc.get("version") != VERSION:
        raise ValueError(f"unsupported graph version {doc.get('version')}")
    g = Graph(doc["layer"])
    for n in doc.get("nodes", []):
        g.nodes.append(Node(n["id"], tuple(n["at"]), n.get("kind")))
    for e in doc.get("edges", []):
        g.edges.append(Edge(e["a"], e["b"], e["kind"], [tuple(p) for p in e.get("via", [])]))
    for ln in doc.get("lanes", []):
        g.lanes.append(Lane(ln["id"], ln["kind"], [tuple(p) for p in ln["points"]],
                            [Port(p["id"], p["at"], p.get("slot")) for p in ln.get("ports", [])]))
    return g
