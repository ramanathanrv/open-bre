from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel
from pydantic import ValidationError
import json

# ---- Base Types ----

class Condition(BaseModel):
    field: str
    operator: str
    value: Union[str, int, float, bool, list]

class ActionBranch(BaseModel):
    name: str
    condition: Optional[str] = None  # e.g., "employment_type == 'SALARIED'"
    next_ruleset: Optional[str] = None
    next_subgraph: Optional[str] = None

class ActionPath(BaseModel):
    decision: Optional[str] = None
    reason: Optional[str] = None
    next_rules: Optional[List[str]] = None
    next_ruleset: Optional[str] = None
    next_subgraph: Optional[str] = None
    branches: Optional[List[ActionBranch]] = None

class Action(BaseModel):
    on_true: Optional[ActionPath] = None
    on_false: Optional[ActionPath] = None

class Rule(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: List[Condition]
    action: Action

class RuleSet(BaseModel):
    id: str
    name: str
    rules: List[Rule]

class Chain(BaseModel):
    id: str
    name: str
    rulesets: List[RuleSet]

class TerminalNode(BaseModel):
    id: str
    decision: str

# ---- Root Graph ----

class LoanBREGraph(BaseModel):
    id: str
    name: str
    chains: List[Chain]
    terminal_nodes: List[TerminalNode]

# --- Loader for JSON String ---
def load_bre_graph_from_json(json_str: str) -> LoanBREGraph:
    """
    Takes a JSON-formatted string and returns a validated LoanBREGraph object.
    """
    data = json.loads(json_str)
    return LoanBREGraph(**data)


def bre_to_d3(graph: LoanBREGraph) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert LoanBREGraph into D3.js-friendly nodes and links.
    Fixes branch paths: branches now point to the first rule of the target ruleset.
    """
    nodes = []
    links = []
    node_ids = set()

    # Build a mapping of ruleset_id -> first rule_id
    ruleset_first_rule = {}
    for chain in graph.chains:
        for ruleset in chain.rulesets:
            if ruleset.rules:
                ruleset_first_rule[ruleset.id] = ruleset.rules[0].id

    def add_node(node_id, name, group):
        if node_id not in node_ids:
            nodes.append({"id": node_id, "name": name, "group": group})
            node_ids.add(node_id)

    # Add terminal nodes
    for term in graph.terminal_nodes:
        add_node(term.id, term.decision, "Terminal")

    # Traverse all chains and rulesets
    for chain in graph.chains:
        for ruleset in chain.rulesets:
            group_name = ruleset.name
            for rule in ruleset.rules:
                add_node(rule.id, rule.name or rule.id, group_name)

                # Handle on_true path
                if rule.action.on_true:
                    # Branches
                    if rule.action.on_true.branches:
                        for branch in rule.action.on_true.branches:
                            # Resolve branch to first rule in the target ruleset
                            target_ruleset_id = branch.next_ruleset or branch.next_subgraph
                            if target_ruleset_id in ruleset_first_rule:
                                first_rule_id = ruleset_first_rule[target_ruleset_id]
                            else:
                                first_rule_id = target_ruleset_id
                            branch_node_id = f"branch_{branch.name.replace(' ', '_').lower()}"
                            add_node(branch_node_id, f"Branch: {branch.name}", "Branch")
                            links.append({
                                "source": rule.id,
                                "target": branch_node_id,
                                "label": branch.name
                            })
                            links.append({
                                "source": branch_node_id,
                                "target": first_rule_id,
                                "label": ""
                            })
                    # Direct next_rules
                    if getattr(rule.action.on_true, "next_rules", None):
                        for nxt in rule.action.on_true.next_rules:
                            links.append({
                                "source": rule.id,
                                "target": nxt,
                                "label": "pass"
                            })

                # Handle on_false path (optional)
                if getattr(rule.action.on_false, "next_rules", None):
                    for nxt in rule.action.on_false.next_rules:
                        links.append({
                            "source": rule.id,
                            "target": nxt,
                            "label": ""
                        })

    return {"nodes": nodes, "links": links}