import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from src.network import TrafficNetwork


def visualize_network(network: TrafficNetwork, title: str = "Traffic Network"):
    fig, ax = plt.subplots(figsize=(10, 8))
    G = nx.DiGraph()

    # Build positions from node coordinates
    pos = {}
    for node_id, node in network.nodes.items():
        G.add_node(node_id)
        pos[node_id] = (node.x, node.y)

    # Add edges
    for road_id, road in network.roads.items():
        G.add_edge(road.start.id, road.end.id, road_id=road_id, road=road)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=600, node_color="white",
                           edgecolors="black", linewidths=2)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12, font_weight="bold")

    # Draw edges with width based on capacity
    for u, v, data in G.edges(data=True):
        road = data["road"]
        width = 1 + (road.capacity / 10)

        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], ax=ax,
                               width=width, edge_color="gray",
                               arrows=True, arrowsize=15,
                               connectionstyle="arc3,rad=0.1")

    # Edge labels with road ID and speed limit
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        road = data["road"]
        edge_labels[(u, v)] = f"{data['road_id']}\n{road.speed_limit_kmh}km/h"

    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax,
                                  font_size=7, label_pos=0.3)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    return fig, ax


def visualize_network_with_traffic(network: TrafficNetwork, title: str = "Traffic Network"):
    fig, ax = plt.subplots(figsize=(10, 8))
    G = nx.DiGraph()

    pos = {}
    for node_id, node in network.nodes.items():
        G.add_node(node_id)
        pos[node_id] = (node.x, node.y)

    for road_id, road in network.roads.items():
        G.add_edge(road.start.id, road.end.id, road_id=road_id, road=road)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=600, node_color="white",
                           edgecolors="black", linewidths=2)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=12, font_weight="bold")

    # Draw edges — thickness and dash pattern encode congestion
    for u, v, data in G.edges(data=True):
        road = data["road"]
        density = road.get_density()

        # Thickness: base width + density scaled
        width = 1.5 + density * 4

        # Dash pattern: solid when empty, increasingly dashed when congested
        # (0, ()) = solid, (5, 5) = evenly dashed, (2, 4) = short dashes
        if density <= 0.2:
            style = "solid"
        elif density <= 0.5:
            style = (0, (8, 3))  # long dashes
        elif density <= 0.8:
            style = (0, (5, 4))  # medium dashes
        else:
            style = (0, (2, 3))  # short dashes (most congested)

        # Color: light gray for empty, black for full
        gray_val = max(0.0, 0.7 - density * 0.7)
        color = (gray_val, gray_val, gray_val)

        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], ax=ax,
                               width=width, edge_color=[color],
                               arrows=True, arrowsize=15,
                               connectionstyle="arc3,rad=0.1",
                               style=style)

    # Edge labels: road ID and vehicle count / capacity
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        road = data["road"]
        edge_labels[(u, v)] = f"{data['road_id']}\n{len(road.vehicles)}/{road.capacity}"

    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax,
                                  font_size=7, label_pos=0.3)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=(0.7, 0.7, 0.7), edgecolor="black", label="Free flow (thin, solid)"),
        mpatches.Patch(facecolor=(0.35, 0.35, 0.35), edgecolor="black", label="Moderate (medium, dashed)"),
        mpatches.Patch(facecolor=(0.0, 0.0, 0.0), edgecolor="black", label="Congested (thick, short dash)"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    return fig, ax
