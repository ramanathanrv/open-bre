from sqlalchemy import event
from .credit_policy import CreditPolicy
from . import db
from bre_models import load_bre_graph_from_json, LoanBREGraph, bre_to_d3
import json

@event.listens_for(CreditPolicy, 'after_insert')
def after_insert_policy(mapper, connection, target):
    print(f"CreditPolicy created: {target.name} ({target.id})")

@event.listens_for(CreditPolicy, 'before_update')
def after_update_policy(mapper, connection, target):
    target.policyJSON_d3 = convert_to_d3js_format(target)
    print(f"CreditPolicy updating: {target.name} ({target.id})")

@event.listens_for(CreditPolicy, 'after_update')
def after_update_policy(mapper, connection, target):
    print(f"CreditPolicy updated: {target.name} ({target.id})")

def convert_to_d3js_from_json(policyData): 
    graph: LoanBREGraph = load_bre_graph_from_json(policyData)
    print(graph.name)
    print(graph.chains[0].id)
    d3_graph = bre_to_d3(graph)
    d3_graph_str = json.dumps(d3_graph, indent=2)
    return d3_graph_str

def convert_to_d3js_format(creditPolicy):
    graph: LoanBREGraph = load_bre_graph_from_json(creditPolicy.policyJSON)
    print(graph.name)
    print(graph.chains[0].id)
    d3_graph = bre_to_d3(graph)
    d3_graph_str = json.dumps(d3_graph, indent=2)
    return d3_graph_str
    