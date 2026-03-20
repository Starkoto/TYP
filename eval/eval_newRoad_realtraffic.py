import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'new_road_RT')
NUM_TRIPS_BEFORE = 15
NUM_TRIPS_AFTER = 20


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
    horizontal_speeds = [40, 50, 50, 40]
    for row in range(4):
        for col in range(3):
            s = node_ids[row][col]
            e = node_ids[row][col + 1]
            speed = horizontal_speeds[row]
            network.add_road(Road(f"{s}{e}", nodes[s], nodes[e], speed_limit_kmh=speed, capacity=5))
            network.add_road(Road(f"{e}{s}", nodes[e], nodes[s], speed_limit_kmh=speed, capacity=5))
    for row in range(3):
        for col in range(4):
            s = node_ids[row][col]
            e = node_ids[row + 1][col]
            network.add_road(Road(f"{s}{e}", nodes[s], nodes[e], speed_limit_kmh=40, capacity=5))
            network.add_road(Road(f"{e}{s}", nodes[e], nodes[s], speed_limit_kmh=40, capacity=5))
    return network


def reset_network(network):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit


def add_road_to_network(network, road_id, start_id, end_id, speed_kmh, capacity):
    start_node = network.nodes[start_id]
    end_node = network.nodes[end_id]
    road = Road(road_id, start_node, end_node, speed_limit_kmh=speed_kmh, capacity=capacity)
    network.add_road(road)


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


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

network = build_network()

main_drivers = []
driver_types = {}

for i in range(3):
    d = Driver(driver_id=f"LowFam_{i}", network=network, stress_tolerance=0.0, familiarity_weight=0.1, learning_rate=0.3)
    main_drivers.append(d)
    driver_types[d.id] = "LowFam"

for i in range(3):
    d = Driver(driver_id=f"HighFam_{i}", network=network, stress_tolerance=0.0, familiarity_weight=0.9, learning_rate=0.3)
    main_drivers.append(d)
    driver_types[d.id] = "HighFam"

for i in range(3):
    d = Driver(driver_id=f"BaseAStar_{i}", network=network, stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0)
    main_drivers.append(d)
    driver_types[d.id] = "BaseAStar"

extra_drivers = []
traffic_routes = [
    ("A", "P"), ("A", "P"), ("E", "P"), ("E", "P"),
    ("I", "P"), ("I", "P"), ("A", "L"), ("A", "L"),
]
for i, (origin, dest) in enumerate(traffic_routes):
    d = Driver(driver_id=f"Traffic_{i}", network=network, stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0)
    d.fixed_origin = origin
    d.fixed_dest = dest
    extra_drivers.append(d)
    driver_types[d.id] = "Traffic"

all_drivers = main_drivers + extra_drivers

collectors = {}
for dtype in ["LowFam", "HighFam", "BaseAStar", "Traffic"]:
    collectors[dtype] = DataCollector(output_dir=os.path.join(OUTPUT_DIR, dtype), log_interval=1)

fig, ax = visualize_network_with_traffic(network, f"Phase 1: Before New Road ({len(all_drivers)} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_before.png"), dpi=150)
plt.close()

# Phase 1: Before new road
for trip in range(1, NUM_TRIPS_BEFORE + 1):
    reset_network(network)
    for d in all_drivers:
        d.current_vehicle = None
        origin = getattr(d, 'fixed_origin', 'A')
        dest = getattr(d, 'fixed_dest', 'P')
        d.start_trip(origin, dest, network)
    for dtype, col in collectors.items():
        col.log_roads(trip, network.roads)
    run_all_drivers(all_drivers)
    for d in all_drivers:
        log_trip_data(collectors[driver_types[d.id]], d)

# Add new road
add_road_to_network(network, "JO", "J", "O", 45, 4)
add_road_to_network(network, "OJ", "O", "J", 45, 4)

reset_network(network)
fig, ax = visualize_network_with_traffic(network, "Phase 2: JO Added (45km/h, cap=4)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_after.png"), dpi=150)
plt.close()

# Phase 2: After new road
for trip in range(NUM_TRIPS_BEFORE + 1, NUM_TRIPS_BEFORE + NUM_TRIPS_AFTER + 1):
    reset_network(network)
    for d in all_drivers:
        d.current_vehicle = None
        origin = getattr(d, 'fixed_origin', 'A')
        dest = getattr(d, 'fixed_dest', 'P')
        d.start_trip(origin, dest, network)
    for dtype, col in collectors.items():
        col.log_roads(trip, network.roads)
    run_all_drivers(all_drivers)
    for d in all_drivers:
        log_trip_data(collectors[driver_types[d.id]], d)

print(f"Results saved to {OUTPUT_DIR}/")