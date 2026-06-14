import json, sys
import networkx as nx
from networkx.readwrite import json_graph
from pathlib import Path

data = json.loads(Path("graphify-out/graph.json").read_text())
G = json_graph.node_link_graph(data, edges="links")

# Tim node TaskQueueFullError
target = None
for nid, ndata in G.nodes(data=True):
    if "taskqueuefullerror" in ndata.get("label", "").lower():
        target = nid
        break

if not target:
    print("Khong tim thay TaskQueueFullError")
    sys.exit(0)

# Lay thong tin node
d = G.nodes[target]
print("=== NODE: TaskQueueFullError ===")
print("File:", d.get("source_file", ""))
print("Type:", d.get("file_type", ""))
print("Degree:", G.degree(target))
print()

# Lay cac ket noi
print("=== KET NOI ===")
for neighbor in list(G.neighbors(target))[:10]:
    edge_data = G[target][neighbor]
    if isinstance(G, nx.MultiGraph):
        edge_data = next(iter(edge_data.values()), {})
    nlabel = G.nodes[neighbor].get("label", neighbor)
    rel = edge_data.get("relation", "")
    conf = edge_data.get("confidence", "")
    src = G.nodes[neighbor].get("source_file", "")
    print(f"  --> {nlabel} [{rel}] [{conf}]")
    print(f"      File: {src}")
