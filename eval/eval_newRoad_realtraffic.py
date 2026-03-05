import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.visualization import visualize_network_with_traffic
from src.dataCollection import DataCollector
import matplotlib.pyplot as plt

def build_network():
    """
    4x4 grid network.
    
    A ----(40)---- B ----(40)---- C ----(40)---- D
    |              |              |              |
   (40)          (40)           (40)           (40)
    |              |              |              |
    E ----(50)---- F ----(50)---- G ----(50)---- H
    |              |              |              |
   (40)          (40)           (40)           (40)
    |              |              |              |
    I ----(50)---- J ----(50)---- K ----(50)---- L
    |              |              |              |
   (40)          (40)           (40)           (40)
    |              |              |              |
    M ----(40)---- N ----(40)---- O ----(40)---- P
    """
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

NUM_TRIPS_BEFORE = 15
NUM_TRIPS_AFTER = 20
NUM_EXTRA_ASTAR = 8             # Extra A* drivers to create congestion on JO
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'new_road_RT')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# CREATE DRIVERS
# ============================================================

network = build_network()

# Main drivers we're tracking
main_drivers = []
driver_types = {}

for i in range(3):
    d = Driver(
        driver_id=f"LowFam_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.1,
        learning_rate=0.3,
    )
    main_drivers.append(d)
    driver_types[d.id] = "LowFam"

for i in range(3):
    d = Driver(
        driver_id=f"HighFam_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.9,
        learning_rate=0.3,
    )
    main_drivers.append(d)
    driver_types[d.id] = "HighFam"

for i in range(3):
    d = Driver(
        driver_id=f"BaseAStar_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.0,
        learning_rate=0.0,
    )
    main_drivers.append(d)
    driver_types[d.id] = "BaseAStar"

# Extra A* drivers — these create congestion from different directions
# Each has a fixed origin and destination to create varied traffic patterns
extra_drivers = []
traffic_routes = [
    ("A", "P"),  # Top-left to bottom-right (same as main)
    ("A", "P"),
    ("E", "P"),  # Left-middle to bottom-right
    ("E", "P"),
    ("I", "P"),  # Left-bottom to bottom-right  
    ("I", "P"),
    ("A", "L"),  # Top-left to right-bottom
    ("A", "L"),
]
for i, (origin, dest) in enumerate(traffic_routes):
    d = Driver(
        driver_id=f"Traffic_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.0,
        learning_rate=0.0,
    )
    d.fixed_origin = origin
    d.fixed_dest = dest
    extra_drivers.append(d)
    driver_types[d.id] = "Traffic"

NUM_EXTRA_ASTAR = len(extra_drivers)

all_drivers = main_drivers + extra_drivers

collectors = {}
for dtype in ["LowFam", "HighFam", "BaseAStar", "Traffic"]:
    collectors[dtype] = DataCollector(
        output_dir=os.path.join(OUTPUT_DIR, dtype), log_interval=1
    )

times = {d.id: [] for d in all_drivers}


# ============================================================
# PHASE 1: BEFORE NEW ROAD
# ============================================================

total_drivers = len(main_drivers) + len(extra_drivers)
print(f"{'='*60}")
print(f"PHASE 1: Normal operation ({NUM_TRIPS_BEFORE} trips)")
print(f"  4x4 grid, {total_drivers} drivers total:")
print(f"    3 LowFam, 3 HighFam, 3 BaseAStar (tracked)")
print(f"    {NUM_EXTRA_ASTAR} extra A* drivers (create traffic)")
print(f"  All roads capacity=5, NO dummy congestion")
print(f"  Main drivers: A→P | Traffic from A, E, I to P and L")
print(f"{'='*60}")

fig, ax = visualize_network_with_traffic(network, f"Phase 1: Before New Road ({total_drivers} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_before.png"), dpi=150)
plt.close()

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
    
    type_times = {"LowFam": [], "HighFam": [], "BaseAStar": [], "Traffic": []}
    type_routes = {"LowFam": [], "HighFam": [], "BaseAStar": [], "Traffic": []}
    
    for d in all_drivers:
        dtype = driver_types[d.id]
        summary = log_trip(collectors[dtype], d)
        times[d.id].append(summary["trip_time"])
        type_times[dtype].append(summary["trip_time"])
        type_routes[dtype].append("→".join(summary["route_taken"]))
    
    print(f"\n  Trip {trip}:")
    for dtype in ["LowFam", "HighFam", "BaseAStar", "Traffic"]:
        avg_t = sum(type_times[dtype]) / len(type_times[dtype])
        unique_routes = set(type_routes[dtype])
        routes_str = " | ".join(unique_routes)
        print(f"    {dtype:10s}: avg={avg_t:.1f}s | routes: {routes_str}")


# ============================================================
# ADD NEW ROAD JO
# ============================================================

print(f"\n{'='*60}")
print(f"ADDING NEW ROAD: J→O (45 km/h, capacity 4)")
print(f"  No dummy congestion — the {NUM_EXTRA_ASTAR} extra A* drivers")
print(f"  will create real congestion by all taking JO")
print(f"{'='*60}")

add_road_to_network(network, "JO", "J", "O", 45, 4)
add_road_to_network(network, "OJ", "O", "J", 45, 4)

reset_network(network)
fig, ax = visualize_network_with_traffic(network, f"Phase 2: JO Added (45km/h, cap=10)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_after.png"), dpi=150)
plt.close()


# ============================================================
# PHASE 2: AFTER NEW ROAD
# ============================================================

print(f"\n{'='*60}")
print(f"PHASE 2: After new road ({NUM_TRIPS_AFTER} trips)")
print(f"  JO at 45km/h — extra A* drivers will pile onto it")
print(f"  Expected behaviour:")
print(f"    Traffic A*: all take JO, congest it")
print(f"    BaseAStar:  also takes JO (sees 45km/h speed limit)")
print(f"    LowFam:     tries JO, learns it's congested, switches back")
print(f"    HighFam:    never tries JO (too unfamiliar)")
print(f"{'='*60}")

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
    
    type_times = {"LowFam": [], "HighFam": [], "BaseAStar": [], "Traffic": []}
    type_routes = {"LowFam": [], "HighFam": [], "BaseAStar": [], "Traffic": []}
    
    for d in all_drivers:
        dtype = driver_types[d.id]
        summary = log_trip(collectors[dtype], d)
        times[d.id].append(summary["trip_time"])
        type_times[dtype].append(summary["trip_time"])
        type_routes[dtype].append("→".join(summary["route_taken"]))
    
    print(f"\n  Trip {trip}:")
    for dtype in ["LowFam", "HighFam", "BaseAStar", "Traffic"]:
        avg_t = sum(type_times[dtype]) / len(type_times[dtype])
        unique_routes = set(type_routes[dtype])
        routes_str = " | ".join(unique_routes)
        print(f"    {dtype:10s}: avg={avg_t:.1f}s | routes: {routes_str}")

# Final memory
print(f"\n  Final memory (JO road):")
for d in all_drivers:
    dtype = driver_types[d.id]
    jo_mem = d.memory.get("JO", None)
    if jo_mem:
        print(f"    {d.id} ({dtype}): JO v={jo_mem['avg_speed']:.2f} km/h, u={jo_mem['usage']}")
    else:
        print(f"    {d.id} ({dtype}): JO never used")


# ============================================================
# COMPARISON
# ============================================================

print(f"\n{'='*60}")
print(f"COMPARISON (main drivers only)")
print(f"{'='*60}")

for dtype in ["LowFam", "HighFam", "BaseAStar"]:
    dtype_drivers = [d for d in main_drivers if driver_types[d.id] == dtype]
    
    before_times = []
    after_times = []
    for d in dtype_drivers:
        before_times.extend(times[d.id][:NUM_TRIPS_BEFORE])
        after_times.extend(times[d.id][NUM_TRIPS_BEFORE:])
    
    avg_before = sum(before_times) / len(before_times)
    avg_after = sum(after_times) / len(after_times)
    change = avg_after - avg_before
    pct = (change / avg_before) * 100
    
    print(f"\n  {dtype}:")
    print(f"    Before new road: {avg_before:.1f}s avg")
    print(f"    After new road:  {avg_after:.1f}s avg")
    print(f"    Change: {change:+.1f}s ({pct:+.1f}%)")

# Also show traffic drivers
traffic_before = []
traffic_after = []
for d in extra_drivers:
    traffic_before.extend(times[d.id][:NUM_TRIPS_BEFORE])
    traffic_after.extend(times[d.id][NUM_TRIPS_BEFORE:])
t_avg_before = sum(traffic_before) / len(traffic_before)
t_avg_after = sum(traffic_after) / len(traffic_after)
t_change = t_avg_after - t_avg_before
t_pct = (t_change / t_avg_before) * 100
print(f"\n  Traffic (extra A* drivers):")
print(f"    Before new road: {t_avg_before:.1f}s avg")
print(f"    After new road:  {t_avg_after:.1f}s avg")
print(f"    Change: {t_change:+.1f}s ({t_pct:+.1f}%)")

# JO usage summary
print(f"\n  JO usage per driver:")
for d in main_drivers:
    dtype = driver_types[d.id]
    jo_usage = d.memory.get("JO", {}).get("usage", 0)
    print(f"    {d.id} ({dtype}): {jo_usage} times")
print(f"    Traffic drivers: {extra_drivers[0].memory.get('JO', {}).get('usage', 0)} times each (all identical)")

print(f"\n  Saved data to {OUTPUT_DIR}/")