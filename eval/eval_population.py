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
    4x4 grid with varied speeds and some stress roads.
    
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
    
    FG and GK have base_stress=0.5 (stressful middle corridor)
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

def run_scenario(name, network, drivers, num_trips, collector, driver_type_map=None):
    """Run a full scenario and return per-trip averages and per-type tracking."""
    trip_avgs = []
    # Track per-type times across all trips
    type_times_all = {}  # type -> list of lists (per trip)
    stress_road_usage = {}  # driver_id -> count of FG/GK usage
    
    for d in drivers:
        stress_road_usage[d.id] = 0
    
    for trip in range(1, num_trips + 1):
        reset_network(network)
        
        for d in drivers:
            d.current_vehicle = None
            d.start_trip("A", "P", network)
        
        collector.log_roads(trip, network.roads)
        run_all_drivers(drivers)
        
        trip_times = []
        type_times = {}
        type_routes = {}
        
        for d in drivers:
            summary = log_trip(collector, d)
            trip_times.append(summary["trip_time"])
            
            dtype = driver_type_map.get(d.id, "All") if driver_type_map else "All"
            if dtype not in type_times:
                type_times[dtype] = []
                type_routes[dtype] = []
            type_times[dtype].append(summary["trip_time"])
            type_routes[dtype].append("->".join(summary["route_taken"]))
            
            # Track stress road usage
            for road_id in summary["route_taken"]:
                if road_id in ("FG", "GK"):
                    stress_road_usage[d.id] += 1
        
        # Store per-type times for this trip
        for dtype, times in type_times.items():
            if dtype not in type_times_all:
                type_times_all[dtype] = []
            type_times_all[dtype].append(sum(times) / len(times))
        
        avg_t = sum(trip_times) / len(trip_times)
        trip_avgs.append(avg_t)
        unique_routes = set()
        for routes in type_routes.values():
            unique_routes.update(routes)
        
        if trip <= 3 or trip == num_trips or trip % 10 == 0:
            print(f"\n  Trip {trip}: avg={avg_t:.1f}s | {len(unique_routes)} unique routes")
            for dtype in sorted(type_times.keys()):
                avg_dt = sum(type_times[dtype]) / len(type_times[dtype])
                unique_dt = set(type_routes[dtype])
                print(f"    {dtype:10s}: avg={avg_dt:.1f}s | routes: {' | '.join(unique_dt)}")
    
    return trip_avgs, type_times_all, stress_road_usage


# ============================================================
# CONFIGURATION
# ============================================================

NUM_TRIPS = 30
NUM_DRIVERS = 20
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'population')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

STRESS_ROADS = {"FG", "GK"}


# ============================================================
# SCENARIO 1: HOMOGENEOUS — all base A*
# ============================================================

print(f"{'='*60}")
print(f"SCENARIO 1: ALL BASE A*")
print(f"  {NUM_DRIVERS} drivers, ω_f=0, ω_s=0, α=0")
print(f"{'='*60}")

net1 = build_network()
drivers1 = []
for i in range(NUM_DRIVERS):
    drivers1.append(Driver(f"Base_{i}", net1, stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0))

col1 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllBaseAStar"), log_interval=1)
avgs1, types1, stress1 = run_scenario("All Base A*", net1, drivers1, NUM_TRIPS, col1)

fig, ax = visualize_network_with_traffic(net1, f"All Base A* ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_astar.png"), dpi=150)
plt.close()


# ============================================================
# SCENARIO 2: HOMOGENEOUS ADAPTIVE — all balanced
# ============================================================

print(f"\n{'='*60}")
print(f"SCENARIO 2: ALL BALANCED ADAPTIVE")
print(f"  {NUM_DRIVERS} drivers, ω_f=0.5, ω_s=0.5, α=0.3")
print(f"{'='*60}")

net2 = build_network()
drivers2 = []
for i in range(NUM_DRIVERS):
    drivers2.append(Driver(f"Balanced_{i}", net2, stress_tolerance=0.5, familiarity_weight=0.5, learning_rate=0.3))

col2 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllBalanced"), log_interval=1)
avgs2, types2, stress2 = run_scenario("All Balanced", net2, drivers2, NUM_TRIPS, col2)

fig, ax = visualize_network_with_traffic(net2, f"All Balanced Adaptive ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_balanced.png"), dpi=150)
plt.close()


# ============================================================
# SCENARIO 3: HETEROGENEOUS — mixed personalities
# ============================================================

print(f"\n{'='*60}")
print(f"SCENARIO 3: MIXED PERSONALITIES")
print(f"  {NUM_DRIVERS} drivers: 5 Explorer, 5 Habitual, 5 Cautious, 5 Balanced")
print(f"{'='*60}")
print(f"  Explorer (5):  ω_f=0.1, ω_s=0.1 — try new routes freely")
print(f"  Habitual (5):  ω_f=0.9, ω_s=0.1 — stick to known routes")
print(f"  Cautious (5):  ω_f=0.1, ω_s=0.9 — avoid stressful roads")
print(f"  Balanced (5):  ω_f=0.5, ω_s=0.5 — moderate on everything")

net3 = build_network()
drivers3 = []
type_map3 = {}

configs = [
    ("Explorer",  5, 0.1, 0.1, 0.3),
    ("Habitual",  5, 0.9, 0.1, 0.3),
    ("Cautious",  5, 0.1, 0.9, 0.3),
    ("Balanced",  5, 0.5, 0.5, 0.3),
]
for dtype, count, fam, stress, lr in configs:
    for i in range(count):
        did = f"{dtype}_{i}"
        d = Driver(did, net3, stress_tolerance=stress, familiarity_weight=fam, learning_rate=lr)
        drivers3.append(d)
        type_map3[did] = dtype

col3 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Mixed"), log_interval=1)
avgs3, types3, stress3 = run_scenario("Mixed", net3, drivers3, NUM_TRIPS, col3, type_map3)

fig, ax = visualize_network_with_traffic(net3, f"Mixed Personalities ({NUM_DRIVERS} drivers)")
plt.savefig(os.path.join(OUTPUT_DIR, "network_mixed.png"), dpi=150)
plt.close()


# ============================================================
# COMPARISON
# ============================================================

settled_n = 10  # Last N trips for settled average

settled1 = sum(avgs1[-settled_n:]) / settled_n
settled2 = sum(avgs2[-settled_n:]) / settled_n
settled3 = sum(avgs3[-settled_n:]) / settled_n

print(f"\n{'='*60}")
print(f"COMPARISON")
print(f"{'='*60}")

print(f"\n  Overall average trip time ({NUM_TRIPS} trips):")
print(f"    All Base A*:       {sum(avgs1)/len(avgs1):.1f}s")
print(f"    All Balanced:      {sum(avgs2)/len(avgs2):.1f}s")
print(f"    Mixed Personalities: {sum(avgs3)/len(avgs3):.1f}s")

print(f"\n  Settled average (last {settled_n} trips):")
print(f"    All Base A*:       {settled1:.1f}s")
print(f"    All Balanced:      {settled2:.1f}s")
print(f"    Mixed Personalities: {settled3:.1f}s")

if settled3 < settled2:
    print(f"\n    Diversity bonus: mixed is {settled2 - settled3:.1f}s faster than homogeneous adaptive ({((settled2-settled3)/settled2)*100:.1f}%)")
print(f"    Learning bonus: adaptive is {settled1 - settled2:.1f}s faster than base A* ({((settled1-settled2)/settled1)*100:.1f}%)")

# Route diversity
print(f"\n  Route diversity (last trip):")
for label, net, drvs in [("All Base A*", net1, drivers1), ("All Balanced", net2, drivers2), ("Mixed", net3, drivers3)]:
    reset_network(net)
    routes = set()
    for d in drvs:
        d.current_vehicle = None
        d.start_trip("A", "P", net)
        route = "->".join([r.id for r in d.current_vehicle.route])
        routes.add(route)
    print(f"    {label}: {len(routes)} unique routes")

# Stress road usage
print(f"\n  Stress road usage (FG + GK) over {NUM_TRIPS} trips:")
print(f"    All Base A*:  avg {sum(stress1.values())/len(stress1):.1f} times per driver")
print(f"    All Balanced: avg {sum(stress2.values())/len(stress2):.1f} times per driver")

# Mixed — per type
stress_by_type = {"Explorer": [], "Habitual": [], "Cautious": [], "Balanced": []}
for did, count in stress3.items():
    dtype = type_map3[did]
    stress_by_type[dtype].append(count)
print(f"    Mixed per type:")
for dtype in ["Explorer", "Habitual", "Cautious", "Balanced"]:
    avg_stress = sum(stress_by_type[dtype]) / len(stress_by_type[dtype])
    print(f"      {dtype:10s}: avg {avg_stress:.1f} times per driver")

# Per-type settled averages for mixed
print(f"\n  Per-type settled average (last {settled_n} trips, mixed population):")
for dtype in ["Explorer", "Habitual", "Cautious", "Balanced"]:
    if dtype in types3:
        settled_dt = sum(types3[dtype][-settled_n:]) / settled_n
        print(f"    {dtype:10s}: {settled_dt:.1f}s")

print(f"\n  Saved data to {OUTPUT_DIR}/")