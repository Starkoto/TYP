import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'stress')
NUM_TRIPS = 10
DRIVERS = [
    {"id": "StressAverse",   "stress_tolerance": 0.9, "familiarity_weight": 0.1, "learning_rate": 0.3},
    {"id": "StressTolerant", "stress_tolerance": 0.1, "familiarity_weight": 0.1, "learning_rate": 0.3},
]


def build_network():
    network = TrafficNetwork()
    nodes = {
        "A": Node("A", 0, 0),   "B": Node("B", 100, 0),   "C": Node("C", 200, 0),
        "D": Node("D", 0, 100), "E": Node("E", 100, 100), "F": Node("F", 200, 100),
        "G": Node("G", 0, 200), "H": Node("H", 100, 200), "I": Node("I", 200, 200),
    }
    for n in nodes.values():
        network.add_node(n)
    edges = [
        ("A","B"), ("B","C"), ("D","E"), ("E","F"),
        ("G","H"), ("H","I"), ("A","D"), ("D","G"),
        ("B","E"), ("E","H"), ("C","F"), ("F","I"),
    ]
    for a, b in edges:
        for s, e in [(a, b), (b, a)]:
            if (s == "A" and e == "B") or (s == "B" and e == "A"):
                speed = 60
                base_stress = 0.5
            else:
                speed = 50
                base_stress = 0.0
            network.add_road(Road(f"{s}{e}", nodes[s], nodes[e], speed_limit_kmh=speed, capacity=10, base_stress=base_stress))
    return network


def reset_network(network):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit


def run_trip(driver):
    while not driver.current_vehicle.has_reached_destination():
        driver.update(1.0)
    return driver.get_trip_summary()


def log_trip_data(collector, summary):
    collector.log_trip(
        driver_id=summary["driver_id"], trip_number=summary["trip_number"],
        start_node=summary["start_node"], goal_node=summary["goal_node"],
        route_taken=summary["route_taken"], trip_time=summary["trip_time"],
        distance=summary["distance"], avg_speed=summary["avg_speed"], avg_stress=summary["avg_stress"]
    )


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

init_network = build_network()
fig, ax = visualize_network_with_traffic(init_network, "Stress Test (AB=60km/h, base_stress=0.5)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()

for driver_config in DRIVERS:
    network = build_network()
    driver = Driver(
        driver_id=driver_config["id"], network=network,
        stress_tolerance=driver_config["stress_tolerance"],
        familiarity_weight=driver_config["familiarity_weight"],
        learning_rate=driver_config["learning_rate"],
    )
    collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, driver_config["id"]), log_interval=1)

    for trip in range(1, NUM_TRIPS + 1):
        reset_network(network)
        driver.current_vehicle = None
        driver.start_trip("A", "I", network)
        collector.log_roads(trip, network.roads)
        summary = run_trip(driver)
        log_trip_data(collector, summary)

print(f"Results saved to {OUTPUT_DIR}/")