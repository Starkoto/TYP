import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'braess')
NUM_DRIVERS = 8
NUM_TRIPS = 15
DRIVER_PARAMS = {
    "stress_tolerance": 0.0,
    "familiarity_weight": 0.1,
    "learning_rate": 0.3,
}


def build_braess_network(include_shortcut=False):
    network = TrafficNetwork()
    nodes = {
        "A": Node("A", 100, 200),
        "S": Node("S", 0, 100),
        "T": Node("T", 200, 100),
        "B": Node("B", 100, 0),
    }
    for n in nodes.values():
        network.add_node(n)
    network.add_road(Road("AS", nodes["A"], nodes["S"], speed_limit_kmh=80, capacity=5))
    network.add_road(Road("SB", nodes["S"], nodes["B"], speed_limit_kmh=30, capacity=50))
    network.add_road(Road("AT", nodes["A"], nodes["T"], speed_limit_kmh=30, capacity=50))
    network.add_road(Road("TB", nodes["T"], nodes["B"], speed_limit_kmh=80, capacity=5))
    if include_shortcut:
        network.add_road(Road("ST", nodes["S"], nodes["T"], speed_limit_kmh=200, capacity=50))
    return network


def reset_network(network):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit


def run_simulation(network, drivers, num_trips, collector):
    for trip in range(1, num_trips + 1):
        reset_network(network)
        for driver in drivers:
            driver.current_vehicle = None
            driver.start_trip("A", "B", network)
        max_steps = 5000
        step = 0
        active = set(range(len(drivers)))
        while active and step < max_steps:
            for i in list(active):
                finished = drivers[i].update(1.0)
                if finished:
                    active.discard(i)
            step += 1
        for driver in drivers:
            summary = driver.get_trip_summary()
            collector.log_trip(
                driver_id=summary["driver_id"], trip_number=trip,
                start_node=summary["start_node"], goal_node=summary["goal_node"],
                route_taken=summary["route_taken"], trip_time=summary["trip_time"],
                distance=summary["distance"], avg_speed=summary["avg_speed"], avg_stress=summary["avg_stress"]
            )


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Phase 1: Without shortcut
network_no_shortcut = build_braess_network(include_shortcut=False)

fig, ax = visualize_network_with_traffic(network_no_shortcut, "Braess Network - No Shortcut")
plt.savefig(os.path.join(OUTPUT_DIR, "network_no_shortcut.png"), dpi=150)
plt.close()

drivers_phase1 = []
for i in range(NUM_DRIVERS):
    drivers_phase1.append(Driver(
        driver_id=f"D{i}", network=network_no_shortcut,
        stress_tolerance=DRIVER_PARAMS["stress_tolerance"],
        familiarity_weight=DRIVER_PARAMS["familiarity_weight"],
        learning_rate=DRIVER_PARAMS["learning_rate"],
    ))

collector_phase1 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "no_shortcut"), log_interval=1)
run_simulation(network_no_shortcut, drivers_phase1, NUM_TRIPS, collector_phase1)

# Phase 2: With shortcut
network_shortcut = build_braess_network(include_shortcut=True)

fig, ax = visualize_network_with_traffic(network_shortcut, "Braess Network - With Shortcut")
plt.savefig(os.path.join(OUTPUT_DIR, "network_with_shortcut.png"), dpi=150)
plt.close()

drivers_phase2 = []
for i in range(NUM_DRIVERS):
    drivers_phase2.append(Driver(
        driver_id=f"D{i}", network=network_shortcut,
        stress_tolerance=DRIVER_PARAMS["stress_tolerance"],
        familiarity_weight=DRIVER_PARAMS["familiarity_weight"],
        learning_rate=DRIVER_PARAMS["learning_rate"],
    ))

collector_phase2 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "with_shortcut"), log_interval=1)
run_simulation(network_shortcut, drivers_phase2, NUM_TRIPS, collector_phase2)

print(f"Results saved to {OUTPUT_DIR}/")