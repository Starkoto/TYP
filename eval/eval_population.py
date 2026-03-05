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
    
    # Stressful roads
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
                    speed_limit_kmh=speed, capacity=5, base_stress=stress))
    
    for row in range(3):
        for col in range(4):
            s = node_ids[row][col]
            e = node_ids[row + 1][col]
            for s_id, e_id in [(s, e), (e, s)]:
                network.add_road(Road(f"{s_id}{e_id}", nodes[s_id], nodes[e_id],
                    speed_limit_kmh=40, capacity=5))
    
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


# ============================================================
# CONFIGURATION
# ============================================================

NUM_TRIPS = 30
NUM_DRIVERS = 12
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'population')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# SCENARIO 1: HOMOGENEOUS (all base A*)
# ============================================================

print(f"{'='*60}")
print(f"SCENARIO 1: HOMOGENEOUS POPULATION")
print(f"  {NUM_DRIVERS} base A* drivers, all identical")
print(f"  ω_f=0, ω_s=0, α=0")
print(f"{'='*60}")

network_homo = build_network()

homo_drivers = []
for i in range(NUM_DRIVERS):
    d = Driver(
        driver_id=f"Base_{i}",
        network=network_homo,
        stress_tolerance=0.0,
        familiarity_weight=0.0,
        learning_rate=0.0,
    )
    homo_drivers.append(d)

homo_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Homogeneous"), log_interval=1)
homo_times = []

for trip in range(1, NUM_TRIPS + 1):
    reset_network(network_homo)
    
    for d in homo_drivers:
        d.current_vehicle = None
        d.start_trip("A", "P", network_homo)
    
    homo_collector.log_roads(trip, network_homo.roads)
    run_all_drivers(homo_drivers)
    
    trip_times = []
    trip_routes = []
    for d in homo_drivers:
        summary = log_trip(homo_collector, d)
        trip_times.append(summary["trip_time"])
        trip_routes.append("→".join(summary["route_taken"]))
    
    avg_t = sum(trip_times) / len(trip_times)
    homo_times.append(avg_t)
    
    unique_routes = set(trip_routes)
    
    if trip <= 5 or trip == NUM_TRIPS or trip % 10 == 0:
        print(f"\n  Trip {trip}: avg={avg_t:.1f}s | {len(unique_routes)} unique routes")
        for r in unique_routes:
            count = trip_routes.count(r)
            print(f"    {r} ({count} drivers)")

# Visualize final state
reset_network(network_homo)
for d in homo_drivers:
    d.current_vehicle = None
    d.start_trip("A", "P", network_homo)
fig, ax = visualize_network_with_traffic(network_homo, f"Homogeneous: {NUM_DRIVERS} Base A* Drivers")
plt.savefig(os.path.join(OUTPUT_DIR, "network_homogeneous.png"), dpi=150)
plt.close()


# ============================================================
# SCENARIO 2: HETEROGENEOUS (mixed personalities)
# ============================================================

print(f"\n{'='*60}")
print(f"SCENARIO 2: HETEROGENEOUS POPULATION")
print(f"  {NUM_DRIVERS} drivers with mixed personalities")
print(f"{'='*60}")

network_hetero = build_network()

hetero_drivers = []
driver_configs = [
    # 3 Low familiarity, low stress tolerance (explorers)
    {"id": "Explorer_0",   "fam": 0.1, "stress": 0.1, "lr": 0.3},
    {"id": "Explorer_1",   "fam": 0.1, "stress": 0.1, "lr": 0.3},
    {"id": "Explorer_2",   "fam": 0.1, "stress": 0.1, "lr": 0.3},
    # 3 High familiarity, low stress tolerance (habitual)
    {"id": "Habitual_0",   "fam": 0.9, "stress": 0.1, "lr": 0.3},
    {"id": "Habitual_1",   "fam": 0.9, "stress": 0.1, "lr": 0.3},
    {"id": "Habitual_2",   "fam": 0.9, "stress": 0.1, "lr": 0.3},
    # 3 Low familiarity, high stress tolerance (stress avoiders who explore)
    {"id": "Cautious_0",   "fam": 0.1, "stress": 0.9, "lr": 0.3},
    {"id": "Cautious_1",   "fam": 0.1, "stress": 0.9, "lr": 0.3},
    {"id": "Cautious_2",   "fam": 0.1, "stress": 0.9, "lr": 0.3},
    # 3 Medium everything (balanced)
    {"id": "Balanced_0",   "fam": 0.5, "stress": 0.5, "lr": 0.3},
    {"id": "Balanced_1",   "fam": 0.5, "stress": 0.5, "lr": 0.3},
    {"id": "Balanced_2",   "fam": 0.5, "stress": 0.5, "lr": 0.3},
]

driver_type_map = {}
for cfg in driver_configs:
    d = Driver(
        driver_id=cfg["id"],
        network=network_hetero,
        stress_tolerance=cfg["stress"],
        familiarity_weight=cfg["fam"],
        learning_rate=cfg["lr"],
    )
    hetero_drivers.append(d)
    driver_type_map[d.id] = cfg["id"].rsplit("_", 1)[0]  # Explorer, Habitual, etc.

print(f"  Explorers (3):  ω_f=0.1, ω_s=0.1 — try new routes freely")
print(f"  Habitual (3):   ω_f=0.9, ω_s=0.1 — stick to known routes")
print(f"  Cautious (3):   ω_f=0.1, ω_s=0.9 — avoid stressful roads")
print(f"  Balanced (3):   ω_f=0.5, ω_s=0.5 — moderate on everything")

hetero_collector = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "Heterogeneous"), log_interval=1)
hetero_times = []

for trip in range(1, NUM_TRIPS + 1):
    reset_network(network_hetero)
    
    for d in hetero_drivers:
        d.current_vehicle = None
        d.start_trip("A", "P", network_hetero)
    
    hetero_collector.log_roads(trip, network_hetero.roads)
    run_all_drivers(hetero_drivers)
    
    # Collect per-type stats
    type_times = {"Explorer": [], "Habitual": [], "Cautious": [], "Balanced": []}
    type_routes = {"Explorer": [], "Habitual": [], "Cautious": [], "Balanced": []}
    all_trip_times = []
    all_routes = []
    
    for d in hetero_drivers:
        summary = log_trip(hetero_collector, d)
        dtype = driver_type_map[d.id]
        type_times[dtype].append(summary["trip_time"])
        type_routes[dtype].append("→".join(summary["route_taken"]))
        all_trip_times.append(summary["trip_time"])
        all_routes.append("→".join(summary["route_taken"]))
    
    avg_t = sum(all_trip_times) / len(all_trip_times)
    hetero_times.append(avg_t)
    
    unique_routes = set(all_routes)
    
    if trip <= 5 or trip == NUM_TRIPS or trip % 10 == 0:
        print(f"\n  Trip {trip}: avg={avg_t:.1f}s | {len(unique_routes)} unique routes")
        for dtype in ["Explorer", "Habitual", "Cautious", "Balanced"]:
            avg_dt = sum(type_times[dtype]) / len(type_times[dtype])
            unique_dt = set(type_routes[dtype])
            print(f"    {dtype:10s}: avg={avg_dt:.1f}s | routes: {' | '.join(unique_dt)}")

# Visualize final state
reset_network(network_hetero)
for d in hetero_drivers:
    d.current_vehicle = None
    d.start_trip("A", "P", network_hetero)
fig, ax = visualize_network_with_traffic(network_hetero, f"Heterogeneous: Mixed Personalities")
plt.savefig(os.path.join(OUTPUT_DIR, "network_heterogeneous.png"), dpi=150)
plt.close()


# ============================================================
# COMPARISON
# ============================================================

print(f"\n{'='*60}")
print(f"COMPARISON")
print(f"{'='*60}")

homo_overall = sum(homo_times) / len(homo_times)
hetero_overall = sum(hetero_times) / len(hetero_times)

# Last 10 trips (settled behavior)
homo_settled = sum(homo_times[-10:]) / 10
hetero_settled = sum(hetero_times[-10:]) / 10

print(f"\n  Overall average trip time ({NUM_TRIPS} trips):")
print(f"    Homogeneous (all A*): {homo_overall:.1f}s")
print(f"    Heterogeneous (mixed): {hetero_overall:.1f}s")

print(f"\n  Settled average (last 10 trips):")
print(f"    Homogeneous: {homo_settled:.1f}s")
print(f"    Heterogeneous: {hetero_settled:.1f}s")

if hetero_settled < homo_settled:
    saved = homo_settled - hetero_settled
    pct = (saved / homo_settled) * 100
    print(f"    Mixed population is {saved:.1f}s faster ({pct:.1f}%)")
else:
    diff = hetero_settled - homo_settled
    print(f"    Homogeneous is {diff:.1f}s faster")

# Route diversity
print(f"\n  Route diversity (last trip):")
# Homo
homo_last_routes = set()
reset_network(network_homo)
for d in homo_drivers:
    d.current_vehicle = None
    d.start_trip("A", "P", network_homo)
    route = "→".join([r.id for r in d.current_vehicle.route])
    homo_last_routes.add(route)
print(f"    Homogeneous: {len(homo_last_routes)} unique routes")

hetero_last_routes = set()
reset_network(network_hetero)
for d in hetero_drivers:
    d.current_vehicle = None
    d.start_trip("A", "P", network_hetero)
    route = "→".join([r.id for r in d.current_vehicle.route])
    hetero_last_routes.add(route)
print(f"    Heterogeneous: {len(hetero_last_routes)} unique routes")

# Per-type breakdown for heterogeneous
print(f"\n  Per-type settled average (last 10 trips):")
for dtype in ["Explorer", "Habitual", "Cautious", "Balanced"]:
    dtype_drivers = [d for d in hetero_drivers if driver_type_map[d.id] == dtype]
    # Reconstruct per-type times from collector
    # Just recompute from the last run data
    dtype_times = []
    for d in dtype_drivers:
        if d.id in [dd.id for dd in hetero_drivers]:
            # Use memory usage as proxy for trip count
            pass
    # Simpler: just show their last trip routes
    routes = set()
    for d in dtype_drivers:
        route = "→".join([r.id for r in d.current_vehicle.route])
        routes.add(route)
    print(f"    {dtype:10s}: {len(routes)} unique routes — {' | '.join(routes)}")

print(f"\n  Saved data to {OUTPUT_DIR}/")