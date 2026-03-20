import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
from src.vehicle import Vehicle
from src.pathfinding import AStar
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'base_astar')
CONGESTION = {"AB": 8}
NUM_TRIPS = 10


class DummyVehicle:
    def __init__(self, vid):
        self.id = vid


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
            speed = 60 if (s == "A" and e == "B") or (s == "B" and e == "A") else 50
            network.add_road(Road(f"{s}{e}", nodes[s], nodes[e], speed_limit_kmh=speed, capacity=10))
    return network


def reset_network(network, congestion_setup=None):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit
    if congestion_setup:
        for road_id, num_v in congestion_setup.items():
            road = network.roads[road_id]
            for i in range(num_v):
                road.add_vehicle(DummyVehicle(f"dummy_{i}"))


def run_trip(driver):
    while not driver.current_vehicle.has_reached_destination():
        driver.update(1.0)
    return driver.get_trip_summary()


def run_base_astar_trip(network, start, goal, congestion_setup):
    reset_network(network, congestion_setup)
    pathfinder = AStar(network)
    route = pathfinder.find_path(start, goal)
    if not route:
        return None
    vehicle = Vehicle(vehicle_id="base_astar", route=route)
    route[0].add_vehicle(vehicle)
    total_time = 0.0
    speed_obs = {}
    while not vehicle.has_reached_destination():
        road = vehicle.get_current_road()
        if road:
            if road.id not in speed_obs:
                speed_obs[road.id] = []
            speed_obs[road.id].append(road.current_speed * 3.6)
        vehicle.update_position(1.0)
        total_time += 1.0
    total_distance = sum(r.distance for r in route)
    all_speeds = [s for speeds in speed_obs.values() for s in speeds]
    avg_speed = sum(all_speeds) / len(all_speeds) if all_speeds else 0
    return {
        "route_taken": [r.id for r in route],
        "trip_time": total_time,
        "distance": total_distance,
        "avg_speed": avg_speed,
    }


def log_trip_data(collector, driver_id, trip_number, start, goal, route, trip_time, distance, avg_speed, avg_stress=0.0):
    collector.log_trip(
        driver_id=driver_id, trip_number=trip_number,
        start_node=start, goal_node=goal,
        route_taken=route, trip_time=trip_time,
        distance=distance, avg_speed=avg_speed, avg_stress=avg_stress
    )


# ============================================================

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

init_network = build_network()
reset_network(init_network, CONGESTION)
fig, ax = visualize_network_with_traffic(init_network, "Initial Network (AB=60km/h, 8/10 congestion)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()

# Base A*
base_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "BaseAStar"), log_interval=1)
for trip in range(1, NUM_TRIPS + 1):
    result = run_base_astar_trip(build_network(), "A", "I", CONGESTION)
    log_trip_data(base_collector, "BaseAStar", trip, "A", "I",
                  result["route_taken"], result["trip_time"], result["distance"], result["avg_speed"])

# Adaptive
network = build_network()
driver = Driver("Adaptive", network, stress_tolerance=0.0, familiarity_weight=0.1, learning_rate=0.3)
adaptive_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Adaptive"), log_interval=1)

for trip in range(1, NUM_TRIPS + 1):
    reset_network(network, CONGESTION)
    driver.current_vehicle = None
    driver.start_trip("A", "I", network)
    adaptive_collector.log_roads(trip, network.roads)
    summary = run_trip(driver)
    log_trip_data(adaptive_collector, summary["driver_id"], summary["trip_number"],
                  summary["start_node"], summary["goal_node"], summary["route_taken"],
                  summary["trip_time"], summary["distance"], summary["avg_speed"], summary["avg_stress"])

print(f"Results saved to {OUTPUT_DIR}/")