import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'population')
NUM_TRIPS = 30
NUM_DRIVERS = 20


def build_network():
    network = TrafficNetwork()
    node_ids = [
        ["A", "B", "C", "D"],
        ["E", "F", "G", "H"],
        ["I", "J", "K", "L"],
        ["M", "N", "O", "P"],
    ]
    spacing = 100
    nodes = {}
    for row in range(4):
        for col in range(4):
            nid = node_ids[row][col]
            n = Node(nid, col * spacing, (3 - row) * spacing)
            nodes[nid] = n
            network.add_node(n)
    stress_roads = {"FG", "GF", "GK", "KG"}
    horizontal_speeds = [40, 50, 50, 40]
    for row in range(4):
        for col in range(3):
            s = node_ids[row][col]
            e = node_ids[row][col + 1]
            speed = horizontal_speeds[row]
            for s_id, e_id in [(s, e), (e, s)]:
                rid = f"{s_id}{e_id}"
                stress = 0.5 if rid in stress_roads else 0.0
                network.add_road(Road(rid, nodes[s_id], nodes[e_id],
                    speed_limit_kmh=speed, capacity=10, base_stress=stress))
    for row in range(3):
        for col in range(4):
            s = node_ids[row][col]
            e = node_ids[row + 1][col]
            for s_id, e_id in [(s, e), (e, s)]:
                network.add_road(Road(f"{s_id}{e_id}", nodes[s_id], nodes[e_id],
                    speed_limit_kmh=40, capacity=10))
    return network


def reset_network(network):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit


def run_all_drivers(drivers, time_step=1.0):
    max_steps = 10000
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


def run_scenario(network, drivers, num_trips, collector):
    for trip in range(1, num_trips + 1):
        reset_network(network)
        for d in drivers:
            d.current_vehicle = None
            d.start_trip("A", "P", network)
        collector.log_roads(trip, network.roads)
        run_all_drivers(drivers)
        for d in drivers:
            log_trip_data(collector, d)


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Scenario 1: All base A*
net1 = build_network()
drivers1 = [Driver(f"Base_{i}", net1, stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0) for i in range(NUM_DRIVERS)]
col1 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllBaseAStar"), log_interval=1)
run_scenario(net1, drivers1, NUM_TRIPS, col1)

fig, ax = visualize_network_with_traffic(net1, f"All Base A* ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_astar.png"), dpi=150)
plt.close()

# Scenario 2: All balanced adaptive
net2 = build_network()
drivers2 = [Driver(f"Balanced_{i}", net2, stress_tolerance=0.5, familiarity_weight=0.5, learning_rate=0.3) for i in range(NUM_DRIVERS)]
col2 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllBalanced"), log_interval=1)
run_scenario(net2, drivers2, NUM_TRIPS, col2)

fig, ax = visualize_network_with_traffic(net2, f"All Balanced Adaptive ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_balanced.png"), dpi=150)
plt.close()

# Scenario 3: Mixed personalities
net3 = build_network()
drivers3 = []
configs = [
    ("Explorer",  5, 0.1, 0.1, 0.3),
    ("Habitual",  5, 0.9, 0.1, 0.3),
    ("Cautious",  5, 0.1, 0.9, 0.3),
    ("Balanced",  5, 0.5, 0.5, 0.3),
]
for dtype, count, fam, stress, lr in configs:
    for i in range(count):
        drivers3.append(Driver(f"{dtype}_{i}", net3, stress_tolerance=stress, familiarity_weight=fam, learning_rate=lr))

col3 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Mixed"), log_interval=1)
run_scenario(net3, drivers3, NUM_TRIPS, col3)

fig, ax = visualize_network_with_traffic(net3, f"Mixed Personalities ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_mixed.png"), dpi=150)
plt.close()

print(f"Results saved to {OUTPUT_DIR}/")