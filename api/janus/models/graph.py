from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import yaml

def parse_markdown_with_frontmatter(path: Path) -> dict[str, Any]:
    """Parse a markdown file that has YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {"content": content}
    
    parts = content.split("---", 2)
    if len(parts) >= 3:
        frontmatter = yaml.safe_load(parts[1]) or {}
        frontmatter["content"] = parts[2].strip()
        return frontmatter
    return {"content": content}

class DecisionGraph:
    """In-process decision graph using NetworkX."""
    
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    def load_from_directory(self, dpath: Path) -> None:
        """Load corpus markdown files into the DiGraph."""
        for p in dpath.glob("*.md"):
            data = parse_markdown_with_frontmatter(p)
            doc_id = data.get("doc_id")
            if not doc_id:
                continue
            
            # Add node
            self.graph.add_node(doc_id, **data)

        # Second pass: wire relationships
        for node_id, data in self.graph.nodes(data=True):
            related = data.get("related", [])
            for r in related:
                if self.graph.has_node(r):
                    # Direction: from precedent/related -> current node, or vice versa?
                    # The postmortem references the decision. So Decision -> Postmortem.
                    self.graph.add_edge(r, node_id)

    def get_related_outcomes(self, doc_id: str) -> list[dict[str, Any]]:
        """Given a decision document ID, get nodes that followed from it."""
        if not self.graph.has_node(doc_id):
            return []
        
        # Breadth-first search to find outcomes/postmortems/policies
        outcomes = []
        for successor in nx.bfs_tree(self.graph, doc_id):
            if successor != doc_id:
                outcomes.append(self.graph.nodes[successor])
        return outcomes
