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
JO_CONGESTION = {"JO": 8}
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'new_road')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# CREATE 9 DRIVERS: 3 of each type
# ============================================================

network = build_network()

drivers = []
driver_types = {}

for i in range(3):
    d = Driver(
        driver_id=f"LowFam_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.1,
        learning_rate=0.3,
    )
    drivers.append(d)
    driver_types[d.id] = "LowFam"

for i in range(3):
    d = Driver(
        driver_id=f"HighFam_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.9,
        learning_rate=0.3,
    )
    drivers.append(d)
    driver_types[d.id] = "HighFam"

for i in range(3):
    d = Driver(
        driver_id=f"BaseAStar_{i}",
        network=network,
        stress_tolerance=0.0,
        familiarity_weight=0.0,
        learning_rate=0.0,
    )
    drivers.append(d)
    driver_types[d.id] = "BaseAStar"

collectors = {}
for d in drivers:
    dtype = driver_types[d.id]
    if dtype not in collectors:
        collectors[dtype] = DataCollector(
            output_dir=os.path.join(OUTPUT_DIR, dtype), log_interval=1
        )

times = {d.id: [] for d in drivers}


# ============================================================
# PHASE 1: BEFORE NEW ROAD
# ============================================================

print(f"{'='*60}")
print(f"PHASE 1: Normal operation ({NUM_TRIPS_BEFORE} trips)")
print(f"  4x4 grid, 9 drivers (3 LowFam, 3 HighFam, 3 BaseAStar)")
print(f"  All roads capacity=5, A→P, no dummy congestion")
print(f"{'='*60}")

fig, ax = visualize_network_with_traffic(network, "Phase 1: Before New Road")
plt.savefig(os.path.join(OUTPUT_DIR, "network_before.png"), dpi=150)
plt.close()

for trip in range(1, NUM_TRIPS_BEFORE + 1):
    reset_network(network)
    
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "P", network)
    
    for dtype, col in collectors.items():
        col.log_roads(trip, network.roads)
    
    run_all_drivers(drivers)
    
    type_times = {"LowFam": [], "HighFam": [], "BaseAStar": []}
    type_routes = {"LowFam": [], "HighFam": [], "BaseAStar": []}
    
    for d in drivers:
        dtype = driver_types[d.id]
        summary = log_trip(collectors[dtype], d)
        times[d.id].append(summary["trip_time"])
        type_times[dtype].append(summary["trip_time"])
        type_routes[dtype].append("→".join(summary["route_taken"]))
    
    print(f"\n  Trip {trip}:")
    for dtype in ["LowFam", "HighFam", "BaseAStar"]:
        avg_t = sum(type_times[dtype]) / len(type_times[dtype])
        unique_routes = set(type_routes[dtype])
        routes_str = " | ".join(unique_routes)
        print(f"    {dtype:10s}: avg={avg_t:.1f}s | routes: {routes_str}")

print(f"\n  Memory before new road:")
for dtype in ["LowFam", "HighFam", "BaseAStar"]:
    d = [d for d in drivers if driver_types[d.id] == dtype][0]
    print(f"    {dtype} ({d.id}):")
    for rid, mem in d.memory.items():
        print(f"      {rid}: v={mem['avg_speed']:.2f} km/h, u={mem['usage']}")


# ============================================================
# ADD NEW ROAD JO — fast but congested
# ============================================================

print(f"\n{'='*60}")
print(f"ADDING NEW ROAD: J→O (45 km/h, capacity 10)")
print(f"  Congested with 8 dummy vehicles (8/10 density)")
print(f"  Actual speed: 45 * (1 - (0.8-0.5)) = 45 * 0.7 = {45*0.7:.1f} km/h")
print(f"  Looks fast (45 km/h limit) but actually slow ({45*0.7:.1f} km/h)")
print(f"{'='*60}")

add_road_to_network(network, "JO", "J", "O", 45, 10)
add_road_to_network(network, "OJ", "O", "J", 45, 10)

reset_network(network, JO_CONGESTION)
fig, ax = visualize_network_with_traffic(network, "Phase 2: JO Added (45km/h, 8/10 congested)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_after.png"), dpi=150)
plt.close()


# ============================================================
# PHASE 2: AFTER NEW ROAD (congested)
# ============================================================

print(f"\n{'='*60}")
print(f"PHASE 2: After new road ({NUM_TRIPS_AFTER} trips)")
print(f"  JO at 45km/h but 8/10 congested = {45*0.7:.1f} km/h actual")
print(f"  Expected behaviour:")
print(f"    BaseAStar: always takes JO (sees 55km/h, ignores congestion)")
print(f"    LowFam: tries JO, learns it's slow, switches back")
print(f"    HighFam: avoids JO (familiarity penalty too high)")
print(f"{'='*60}")

for trip in range(NUM_TRIPS_BEFORE + 1, NUM_TRIPS_BEFORE + NUM_TRIPS_AFTER + 1):
    reset_network(network, JO_CONGESTION)
    
    for d in drivers:
        d.current_vehicle = None
        d.start_trip("A", "P", network)
    
    for dtype, col in collectors.items():
        col.log_roads(trip, network.roads)
    
    run_all_drivers(drivers)
    
    type_times = {"LowFam": [], "HighFam": [], "BaseAStar": []}
    type_routes = {"LowFam": [], "HighFam": [], "BaseAStar": []}
    
    for d in drivers:
        dtype = driver_types[d.id]
        summary = log_trip(collectors[dtype], d)
        times[d.id].append(summary["trip_time"])
        type_times[dtype].append(summary["trip_time"])
        type_routes[dtype].append("→".join(summary["route_taken"]))
    
    print(f"\n  Trip {trip}:")
    for dtype in ["LowFam", "HighFam", "BaseAStar"]:
        avg_t = sum(type_times[dtype]) / len(type_times[dtype])
        unique_routes = set(type_routes[dtype])
        routes_str = " | ".join(unique_routes)
        print(f"    {dtype:10s}: avg={avg_t:.1f}s | routes: {routes_str}")

# Final memory
print(f"\n  Final memory (JO road):")
for d in drivers:
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
print(f"COMPARISON")
print(f"{'='*60}")

for dtype in ["LowFam", "HighFam", "BaseAStar"]:
    dtype_drivers = [d for d in drivers if driver_types[d.id] == dtype]
    
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

# JO usage
print(f"\n  JO usage per driver:")
for d in drivers:
    dtype = driver_types[d.id]
    jo_usage = d.memory.get("JO", {}).get("usage", 0)
    print(f"    {d.id} ({dtype}): {jo_usage} times")

print(f"\n  Saved data to {OUTPUT_DIR}/")