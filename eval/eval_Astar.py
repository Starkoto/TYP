import sys
sys.path.insert(0, '/mnt/project')
sys.path.insert(0, '.')

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.visualization import visualize_network_with_traffic
from src.dataCollection import DataCollector
from src.pathfinding import AStar
import matplotlib.pyplot as plt
import os

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

def add_congestion(network, road_id, num_vehicles):
    road = network.roads[road_id]
    for i in range(num_vehicles):
        road.add_vehicle(DummyVehicle(f"dummy_{i}"))

def reset_network(network, congestion_setup=None):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit
    if congestion_setup:
        for road_id, num_v in congestion_setup.items():
            add_congestion(network, road_id, num_v)

def run_trip_adaptive(driver, network):
    """Run a trip using the adaptive driver."""
    while not driver.current_vehicle.has_reached_destination():
        driver.update(1.0)
    return driver.get_trip_summary()

def run_trip_base_astar(network, start, goal, congestion_setup):
    """Run a trip using base A* — no memory, no personality.
    Manually simulates the vehicle moving along the route."""
    reset_network(network, congestion_setup)
    
    pathfinder = AStar(network)
    route = pathfinder.find_path(start, goal)
    
    if not route:
        return None
    
    route_ids = [r.id for r in route]
    
    # Simulate driving: add vehicle to first road, step through
    from src.vehicle import Vehicle
    vehicle = Vehicle(vehicle_id="base_astar", route=route)
    route[0].add_vehicle(vehicle)
    
    total_time = 0.0
    speed_observations = {}
    
    while not vehicle.has_reached_destination():
        road = vehicle.get_current_road()
        if road:
            if road.id not in speed_observations:
                speed_observations[road.id] = []
            speed_observations[road.id].append(road.current_speed * 3.6)
        
        vehicle.update_position(1.0)
        total_time += 1.0
    
    total_distance = sum(r.distance for r in route)
    all_speeds = [s for speeds in speed_observations.values() for s in speeds]
    avg_speed = sum(all_speeds) / len(all_speeds) if all_speeds else 0
    
    return {
        "route_taken": route_ids,
        "trip_time": total_time,
        "distance": total_distance,
        "avg_speed": avg_speed,
    }


# ============================================================
# CONFIGURATION
# ============================================================

CONGESTION = {"AB": 8}
NUM_TRIPS = 10
OUTPUT_DIR = "test_base_astar"

# Adaptive driver settings
ADAPTIVE_CONFIG = {
    "id": "Adaptive",
    "stress_tolerance": 0.0,
    "familiarity_weight": 0.1,
    "learning_rate": 0.3,
}

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# RUN TEST
# ============================================================

# Visualize initial state
init_network = build_network()
reset_network(init_network, CONGESTION)
ab = init_network.roads["AB"]
print(f"AB road: speed_limit=60 km/h, {len(ab.vehicles)}/10 vehicles")
print(f"  When driver enters: 9/10 density, reduction=0.6, actual speed={60*0.6:.1f} km/h")
print(f"  Base A* sees: cost = 100 / (60/3.6) = {100/(60/3.6):.2f}s (ignores congestion)")
print(f"  AD road: speed_limit=50 km/h, empty, actual speed=50.0 km/h")
print(f"  Base A* sees: cost = 100 / (50/3.6) = {100/(50/3.6):.2f}s")
print(f"  Base A* always picks AB because 6.00 < 7.20")

fig, ax = visualize_network_with_traffic(init_network, "Initial Network (AB=60km/h, 8/10 congestion)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()

# --- Base A* ---
print(f"\n{'='*60}")
print(f"BASE A* (no memory, no personality)")
print(f"{'='*60}")

base_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "BaseAStar"), log_interval=1)
base_total_time = 0.0

for trip in range(1, NUM_TRIPS + 1):
    result = run_trip_base_astar(build_network(), "A", "I", CONGESTION)
    base_total_time += result["trip_time"]
    
    base_collector.log_trip(
        driver_id="BaseAStar",
        trip_number=trip,
        start_node="A",
        goal_node="I",
        route_taken=result["route_taken"],
        trip_time=result["trip_time"],
        distance=result["distance"],
        avg_speed=result["avg_speed"],
        avg_stress=0.0
    )
    
    print(f"  Trip {trip}: route={' → '.join(result['route_taken'])} | time={result['trip_time']:.1f}s | avg_speed={result['avg_speed']:.1f} km/h")

print(f"\n  Total time over {NUM_TRIPS} trips: {base_total_time:.1f}s")
print(f"  Average trip time: {base_total_time/NUM_TRIPS:.1f}s")

# --- Adaptive Driver ---
print(f"\n{'='*60}")
print(f"ADAPTIVE DRIVER (ω_f={ADAPTIVE_CONFIG['familiarity_weight']}, ω_s={ADAPTIVE_CONFIG['stress_tolerance']}, α={ADAPTIVE_CONFIG['learning_rate']})")
print(f"{'='*60}")

network = build_network()
driver = Driver(
    driver_id=ADAPTIVE_CONFIG["id"],
    network=network,
    stress_tolerance=ADAPTIVE_CONFIG["stress_tolerance"],
    familiarity_weight=ADAPTIVE_CONFIG["familiarity_weight"],
    learning_rate=ADAPTIVE_CONFIG["learning_rate"],
)

adaptive_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Adaptive"), log_interval=1)
adaptive_total_time = 0.0
switched = False

for trip in range(1, NUM_TRIPS + 1):
    reset_network(network, CONGESTION)
    
    driver.current_vehicle = None
    driver.start_trip("A", "I", network)
    route = [r.id for r in driver.current_vehicle.route]
    
    adaptive_collector.log_roads(driver.trip_count, network.roads)
    
    run_trip_adaptive(driver, network)
    
    summary = driver.get_trip_summary()
    adaptive_total_time += summary["trip_time"]
    
    adaptive_collector.log_trip(
        driver_id=summary["driver_id"],
        trip_number=summary["trip_number"],
        start_node=summary["start_node"],
        goal_node=summary["goal_node"],
        route_taken=summary["route_taken"],
        trip_time=summary["trip_time"],
        distance=summary["distance"],
        avg_speed=summary["avg_speed"],
        avg_stress=summary["avg_stress"]
    )
    
    ab_mem = driver.memory.get("AB", {}).get("avg_speed", "-")
    
    if not switched and route[0] == "AD":
        switched = True
        marker = "  *** SWITCHED ***"
    else:
        marker = ""
    
    if isinstance(ab_mem, float):
        print(f"  Trip {trip}: route={' → '.join(route)} | time={summary['trip_time']:.1f}s | avg_speed={summary['avg_speed']:.1f} km/h | v̄_AB={ab_mem:.2f}{marker}")
    else:
        print(f"  Trip {trip}: route={' → '.join(route)} | time={summary['trip_time']:.1f}s | avg_speed={summary['avg_speed']:.1f} km/h{marker}")

print(f"\n  Total time over {NUM_TRIPS} trips: {adaptive_total_time:.1f}s")
print(f"  Average trip time: {adaptive_total_time/NUM_TRIPS:.1f}s")

# --- Summary ---
print(f"\n{'='*60}")
print(f"COMPARISON")
print(f"{'='*60}")
print(f"  Base A*:  total={base_total_time:.1f}s, avg={base_total_time/NUM_TRIPS:.1f}s per trip")
print(f"  Adaptive: total={adaptive_total_time:.1f}s, avg={adaptive_total_time/NUM_TRIPS:.1f}s per trip")
time_saved = base_total_time - adaptive_total_time
pct_saved = (time_saved / base_total_time) * 100
print(f"  Time saved: {time_saved:.1f}s ({pct_saved:.1f}%)")
print(f"\n  Saved data to {OUTPUT_DIR}/")