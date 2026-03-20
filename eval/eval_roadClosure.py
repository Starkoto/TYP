import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'road_closure')
NUM_TRIPS_BEFORE = 5
NUM_TRIPS_AFTER = 10
ROAD_TO_CLOSE = "CF"
CONGESTION_AFTER = {"BE": 7}


class DummyVehicle:
    def __init__(self, vid):
        self.id = vid


def build_network():
    network = TrafficNetwork()
    nodes = {
        "A": Node("A", 0, 200), "B": Node("B", 100, 200), "C": Node("C", 200, 200),
        "D": Node("D", 0, 100), "E": Node("E", 100, 100), "F": Node("F", 200, 100),
        "G": Node("G", 0, 0),   "H": Node("H", 100, 0),   "I": Node("I", 200, 0),
    }
    for n in nodes.values():
        network.add_node(n)
    roads_config = {
        "AB": ("A","B", 60), "BA": ("B","A", 60),
        "BC": ("B","C", 60), "CB": ("C","B", 60),
        "DE": ("D","E", 50), "ED": ("E","D", 50),
        "EF": ("E","F", 50), "FE": ("F","E", 50),
        "GH": ("G","H", 50), "HG": ("H","G", 50),
        "HI": ("H","I", 50), "IH": ("I","H", 50),
        "AD": ("A","D", 40), "DA": ("D","A", 40),
        "BE": ("B","E", 40), "EB": ("E","B", 40),
        "CF": ("C","F", 40), "FC": ("F","C", 40),
        "DG": ("D","G", 40), "GD": ("G","D", 40),
        "EH": ("E","H", 40), "HE": ("H","E", 40),
        "FI": ("F","I", 40), "IF": ("I","F", 40),
    }
    for road_id, (start, end, speed) in roads_config.items():
        network.add_road(Road(road_id, nodes[start], nodes[end], speed_limit_kmh=speed, capacity=10))
    return network


def reset_network(network, congestion_setup=None):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit
    if congestion_setup:
        for road_id, num_v in congestion_setup.items():
            if road_id in network.roads:
                road = network.roads[road_id]
                for i in range(num_v):
                    road.add_vehicle(DummyVehicle(f"dummy_{i}"))


def close_road(network, road_id):
    if road_id in network.roads:
        road = network.roads[road_id]
        start_id = road.start.id
        network.adjacency[start_id] = [r for r in network.adjacency[start_id] if r.id != road_id]
        del network.roads[road_id]


def run_all_drivers(drivers, time_step=1.0):
    max_steps = 5000
    step = 0
    active = set(range(len(drivers)))
    while active and step < max_steps:
        for i in list(active):
            finished = drivers[i].update(time_step)
            if finished:
                active.discard(i)
        step += 1


def log_trip_data(collector, driver):
    summary = driver.get_trip_summary()
    collector.log_trip(
        driver_id=summary["driver_id"], trip_number=summary["trip_number"],
        start_node=summary["start_node"], goal_node=summary["goal_node"],
        route_taken=summary["route_taken"], trip_time=summary["trip_time"],
        distance=summary["distance"], avg_speed=summary["avg_speed"], avg_stress=summary["avg_stress"]
    )


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

network = build_network()

adaptive = Driver(
    driver_id="Adaptive", network=network,
    stress_tolerance=0.0, familiarity_weight=0.1, learning_rate=0.3,
)
base = Driver(
    driver_id="BaseAStar", network=network,
    stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0,
)
drivers = [adaptive, base]

adaptive_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Adaptive"), log_interval=1)
base_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "BaseAStar"), log_interval=1)

fig, ax = visualize_network_with_traffic(network, "Initial Network")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()

# Phase 1: Before closure
for trip in range(1, NUM_TRIPS_BEFORE + 1):
    reset_network(network)
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "I", network)
    run_all_drivers(drivers)
    log_trip_data(adaptive_collector, adaptive)
    log_trip_data(base_collector, base)

# Close road and add congestion
close_road(network, ROAD_TO_CLOSE)

reset_network(network, CONGESTION_AFTER)
fig, ax = visualize_network_with_traffic(network, f"After Closing {ROAD_TO_CLOSE} + BE Congestion")
plt.savefig(os.path.join(OUTPUT_DIR, "network_after_closure.png"), dpi=150)
plt.close()

# Phase 2: After closure
for trip in range(NUM_TRIPS_BEFORE + 1, NUM_TRIPS_BEFORE + NUM_TRIPS_AFTER + 1):
    reset_network(network, CONGESTION_AFTER)
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "I", network)
    run_all_drivers(drivers)
    log_trip_data(adaptive_collector, adaptive)
    log_trip_data(base_collector, base)

print(f"Results saved to {OUTPUT_DIR}/")