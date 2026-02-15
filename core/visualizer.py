import graphviz
import streamlit as st
from typing import List, Dict
from data.models import DecisionCardConfig, DriverConfig

class CausalVisualizer:
    def __init__(self, drivers: List[DriverConfig], cards: List[DecisionCardConfig]):
        self.drivers = {d.id: d.label for d in drivers}
        self.cards = cards

    def render_causal_graph(self):
        dot = graphviz.Digraph(comment='Causal Model')
        dot.attr(rankdir='LR')
        
        # Nodes: Drivers (Evidence)
        with dot.subgraph(name='cluster_evidence') as c:
            c.attr(label='Evidence Layer', color='lightgrey')
            for d_id, label in self.drivers.items():
                c.node(d_id, label, shape='ellipse', style='filled', color='lightblue')

        # Nodes: Decision Cards
        with dot.subgraph(name='cluster_decision') as c:
            c.attr(label='Decision Layer', color='lightgrey')
            for card in self.cards:
                c.node(card.id, card.title, shape='box', style='filled', color='lightyellow')

        # Edges
        for card in self.cards:
            # Connect drivers to card
            if card.required_evidence and 'drivers' in card.required_evidence:
                for d_id in card.required_evidence['drivers']:
                    if d_id in self.drivers:
                        dot.edge(d_id, card.id)
            
            # Connect KPIs to card (Simple node for KPIs)
            if card.required_evidence and 'kpis' in card.required_evidence:
                for kpi in card.required_evidence['kpis']:
                    kpi_id = f"kpi_{kpi}"
                    dot.node(kpi_id, kpi, shape='diamond')
                    dot.edge(kpi_id, card.id)

        return dot
