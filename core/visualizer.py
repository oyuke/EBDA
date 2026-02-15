import graphviz
import streamlit as st
from typing import List, Dict
from data.models import DecisionCardConfig, DriverConfig

class CausalVisualizer:
    def __init__(self, drivers: List[DriverConfig], cards: List[DecisionCardConfig]):
        self.drivers = {d.id: d.label for d in drivers}
        self.cards = cards

    def render_causal_graph(self, driver_scores: Dict[str, float] = None, card_scores: Dict[str, float] = None, target_card_id: str = None):
        dot = graphviz.Digraph(comment='Causal Model')
        dot.attr(rankdir='LR')
        
        # Determine scope
        cards_to_render = self.cards
        drivers_to_render = self.drivers # ID -> label
        
        if target_card_id:
            # Filter cards
            cards_to_render = [c for c in self.cards if c.id == target_card_id]
            
            # Filter drivers to only those relevant to the target card(s)
            # Gather all required drivers from selected cards
            req_d_ids = set()
            for c in cards_to_render:
                if c.required_evidence:
                    req_d_ids.update(c.required_evidence.get('drivers', []))
            
            drivers_to_render = {d_id: l for d_id, l in self.drivers.items() if d_id in req_d_ids}

        # Nodes: Drivers (Evidence)
        with dot.subgraph(name='cluster_evidence') as c:
            c.attr(label='Evidence Layer', color='lightgrey')
            for d_id, label in drivers_to_render.items():
                display_label = label
                fill_color = 'lightblue'
                
                if driver_scores and d_id in driver_scores:
                    score = driver_scores[d_id]
                    display_label += f"\n({score:.2f})"
                    # Simple heatmap (1-5 range assumption)
                    if score < 2.5: fill_color = '#ffcccc' # Redish
                    elif score < 3.5: fill_color = '#ffffcc' # Yellowish
                    else: fill_color = '#ccffcc' # Greenish
                
                c.node(d_id, display_label, shape='ellipse', style='filled', color=fill_color)

        # Nodes: Decision Cards
        with dot.subgraph(name='cluster_decision') as c:
            c.attr(label='Decision Layer', color='lightgrey')
            for card in cards_to_render:
                display_label = card.title
                fill_color = 'lightyellow'
                
                if card_scores and card.id in card_scores:
                    # Using total priority or rank? Assuming priority 0-1
                    score = card_scores[card.id]
                    display_label += f"\n(Pri: {score:.2f})"
                    if score > 0.7: fill_color = '#ff9999' # Red/High Priority
                    elif score > 0.4: fill_color = '#ffcc99' # Orange
                
                c.node(card.id, display_label, shape='box', style='filled', color=fill_color)

        # Edges
        for card in cards_to_render:
            # Connect drivers to card
            if card.required_evidence and 'drivers' in card.required_evidence:
                for d_id in card.required_evidence['drivers']:
                    if d_id in drivers_to_render:
                        edge_color = 'black'
                        edge_label = "" # No explicit coefficient in Rule-based model
                        
                        # Highlight edge if driver is low
                        if driver_scores and d_id in driver_scores:
                            if driver_scores[d_id] < 3.0: edge_color = 'red'
                            
                        dot.edge(d_id, card.id, color=edge_color, label=edge_label)
            
            # Connect KPIs to card (Simple node for KPIs)
            if card.required_evidence and 'kpis' in card.required_evidence:
                for kpi in card.required_evidence['kpis']:
                    kpi_id = f"kpi_{kpi}"
                    # User requested non-diamond shape due to width. Using 'box' (rect).
                    dot.node(kpi_id, kpi, shape='box', style='rounded,filled', fillcolor='#e6e6e6')
                    dot.edge(kpi_id, card.id)

        return dot
