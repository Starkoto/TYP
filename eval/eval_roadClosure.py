import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.visualization import visualize_network_with_traffic
from src.dataCollection import DataCollector
import matplotlib.pyplot as plt

class DummyVehicle:
    def __init__(self, vid):
        self.id = vid

def build_network():
    """
    Network with asymmetric speeds:
    
    A ----(60)---- B ----(60)---- C
    |              |              |
   (40)          (40)           (40)
    |              |              |
    D ----(50)---- E ----(50)---- F
    |              |              |
   (40)          (40)           (40)
    |              |              |
    G ----(50)---- H ----(50)---- I
    
    Best route A→I: A→B→C→CF→FI (fast top then down)
    After closing CF: must detour through BE (congested) or AD→DE
    """
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
    """Close a road by removing it from the network."""
    if road_id in network.roads:
        road = network.roads[road_id]
        start_id = road.start.id
        network.adjacency[start_id] = [r for r in network.adjacency[start_id] if r.id != road_id]
        del network.roads[road_id]

def run_all_drivers(drivers, time_step=1.0):
    """Step all drivers until everyone finishes."""
    max_steps = 5000
    step = 0
    active = set(range(len(drivers)))
    
    while active and step < max_steps:
        for i in list(active):
            finished = drivers[i].update(time_step)
            if finished:
                active.discard(i)
        step += 1

def log_trip(collector, driver):
    summary = driver.get_trip_summary()
    collector.log_trip(
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
    return summary


# ============================================================
# CONFIGURATION
# ============================================================

NUM_TRIPS_BEFORE = 5
NUM_TRIPS_AFTER = 10
ROAD_TO_CLOSE = "CF"
CONGESTION_AFTER = {"BE": 7}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'road_closure')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# CREATE BOTH DRIVERS ON THE SAME NETWORK
# ============================================================

network = build_network()

# Adaptive driver — learns from experience
adaptive = Driver(
    driver_id="Adaptive",
    network=network,
    stress_tolerance=0.0,
    familiarity_weight=0.1,
    learning_rate=0.3,
)

# Base A* driver — no personality, no learning (familiarity=0, stress=0)
# Uses AdaptivePathfinder but with weights at 0, so it behaves like base A*
# except it still accumulates memory (which has no effect since weights are 0)
base = Driver(
    driver_id="BaseAStar",
    network=network,
    stress_tolerance=0.0,
    familiarity_weight=0.0,
    learning_rate=0.0,
)

drivers = [adaptive, base]

adaptive_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Adaptive"), log_interval=1)
base_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "BaseAStar"), log_interval=1)

adaptive_times = []
base_times = []


# ============================================================
# PHASE 1: BEFORE CLOSURE
# ============================================================

print(f"{'='*60}")
print(f"PHASE 1: Normal operation ({NUM_TRIPS_BEFORE} trips)")
print(f"  Both drivers on the SAME network")
print(f"  Top row (AB, BC) = 60km/h, middle = 50km/h, vertical = 40km/h")
print(f"{'='*60}")

# Visualize initial state
fig, ax = visualize_network_with_traffic(network, "Initial Network")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()

for trip in range(1, NUM_TRIPS_BEFORE + 1):
    reset_network(network)
    
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "I", network)
    
    run_all_drivers(drivers)
    
    a_summary = log_trip(adaptive_collector, adaptive)
    b_summary = log_trip(base_collector, base)
    
    adaptive_times.append(a_summary["trip_time"])
    base_times.append(b_summary["trip_time"])
    
    a_route = "→".join(a_summary["route_taken"])
    b_route = "→".join(b_summary["route_taken"])
    
    print(f"\n  Trip {trip}:")
    print(f"    Adaptive: {a_route} | time={a_summary['trip_time']:.1f}s | speed={a_summary['avg_speed']:.1f} km/h")
    print(f"    BaseA*:   {b_route} | time={b_summary['trip_time']:.1f}s | speed={b_summary['avg_speed']:.1f} km/h")

print(f"\n  Adaptive memory before closure:")
for rid, mem in adaptive.memory.items():
    print(f"    {rid}: v={mem['avg_speed']:.2f} km/h, u={mem['usage']}")


# ============================================================
# CLOSE ROAD + ADD CONGESTION
# ============================================================

print(f"\n{'='*60}")
print(f"CLOSING ROAD {ROAD_TO_CLOSE} + ADDING CONGESTION ON BE (7/10)")
print(f"{'='*60}")

close_road(network, ROAD_TO_CLOSE)

# Visualize after closure
reset_network(network, CONGESTION_AFTER)
fig, ax = visualize_network_with_traffic(network, f"After Closing {ROAD_TO_CLOSE} + BE Congestion")
plt.savefig(os.path.join(OUTPUT_DIR, "network_after_closure.png"), dpi=150)
plt.close()


# ============================================================
# PHASE 2: AFTER CLOSURE
# ============================================================

print(f"\n{'='*60}")
print(f"PHASE 2: After closure ({NUM_TRIPS_AFTER} trips)")
print(f"  Road {ROAD_TO_CLOSE} removed, BE has 7/10 congestion")
print(f"{'='*60}")

for trip in range(NUM_TRIPS_BEFORE + 1, NUM_TRIPS_BEFORE + NUM_TRIPS_AFTER + 1):
    reset_network(network, CONGESTION_AFTER)
    
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "I", network)
    
    run_all_drivers(drivers)
    
    a_summary = log_trip(adaptive_collector, adaptive)
    b_summary = log_trip(base_collector, base)
    
    adaptive_times.append(a_summary["trip_time"])
    base_times.append(b_summary["trip_time"])
    
    a_route = "→".join(a_summary["route_taken"])
    b_route = "→".join(b_summary["route_taken"])
    
    marker = ""
    if len(adaptive_times) > NUM_TRIPS_BEFORE + 1:
        prev_route = None  # detect switch
    
    print(f"\n  Trip {trip}:")
    print(f"    Adaptive: {a_route} | time={a_summary['trip_time']:.1f}s | speed={a_summary['avg_speed']:.1f} km/h")
    print(f"    BaseA*:   {b_route} | time={b_summary['trip_time']:.1f}s | speed={b_summary['avg_speed']:.1f} km/h")

print(f"\n  Adaptive memory after adaptation:")
for rid, mem in adaptive.memory.items():
    print(f"    {rid}: v={mem['avg_speed']:.2f} km/h, u={mem['usage']}")


# ============================================================
# COMPARISON
# ============================================================

adaptive_avg_before = sum(adaptive_times[:NUM_TRIPS_BEFORE]) / NUM_TRIPS_BEFORE
adaptive_avg_after = sum(adaptive_times[NUM_TRIPS_BEFORE:]) / NUM_TRIPS_AFTER
base_avg_before = sum(base_times[:NUM_TRIPS_BEFORE]) / NUM_TRIPS_BEFORE
base_avg_after = sum(base_times[NUM_TRIPS_BEFORE:]) / NUM_TRIPS_AFTER

print(f"\n{'='*60}")
print(f"COMPARISON")
print(f"{'='*60}")
print(f"\n  Before closure (avg trip time):")
print(f"    Base A*:  {base_avg_before:.1f}s")
print(f"    Adaptive: {adaptive_avg_before:.1f}s")
print(f"\n  After closure (avg trip time):")
print(f"    Base A*:  {base_avg_after:.1f}s")
print(f"    Adaptive: {adaptive_avg_after:.1f}s")

if adaptive_avg_after < base_avg_after:
    saved = base_avg_after - adaptive_avg_after
    pct = (saved / base_avg_after) * 100
    print(f"\n  Adaptive is {saved:.1f}s FASTER per trip ({pct:.1f}%) after disruption")
elif adaptive_avg_after > base_avg_after:
    slower = adaptive_avg_after - base_avg_after
    print(f"\n  Adaptive is {slower:.1f}s SLOWER per trip after disruption")
else:
    print(f"\n  Both perform equally after disruption")

print(f"\n  Time increase after closure:")
print(f"    Base A*:  {base_avg_after - base_avg_before:+.1f}s ({((base_avg_after - base_avg_before) / base_avg_before) * 100:+.1f}%)")
print(f"    Adaptive: {adaptive_avg_after - adaptive_avg_before:+.1f}s ({((adaptive_avg_after - adaptive_avg_before) / adaptive_avg_before) * 100:+.1f}%)")

print(f"\n  Saved data to {OUTPUT_DIR}/")