import sys
import os
import random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.simulation import Simulation
from src.visualization import visualize_network_with_traffic
from src.dataCollection import DataCollector
import matplotlib.pyplot as plt
import csv

def build_network():
    """
    Irregular network — all roads identical: 50 km/h, capacity 5.
    No pre-designed bottlenecks. Let traffic patterns reveal them.
    
         G
        / \
       /   \
      F     B ---- A
     / \   / \     |
    E   \ /   C    |
     \   H   /     |
      \ | \ /      D
       \|  V      /
        I---J ---
    """
    network = TrafficNetwork()
    
    nodes = {
        "A": Node("A", 400, 250),
        "B": Node("B", 250, 300),
        "C": Node("C", 250, 150),
        "D": Node("D", 400, 100),
        "E": Node("E", 50, 200),
        "F": Node("F", 100, 350),
        "G": Node("G", 200, 450),
        "H": Node("H", 150, 200),
        "I": Node("I", 100, 50),
        "J": Node("J", 250, 0),
    }
    for n in nodes.values():
        network.add_node(n)
    
    # All roads: 50 km/h, capacity 5 — completely uniform
    connections = [
        ("B", "A"), ("A", "D"), ("B", "G"), ("G", "F"),
        ("B", "C"), ("B", "H"), ("F", "E"), ("F", "H"),
        ("E", "I"), ("H", "I"), ("H", "C"), ("I", "J"),
        ("C", "J"), ("D", "J"),
    ]
    
    for start, end in connections:
        network.add_road(Road(f"{start}{end}", nodes[start], nodes[end], speed_limit_kmh=50, capacity=5))
        network.add_road(Road(f"{end}{start}", nodes[end], nodes[start], speed_limit_kmh=50, capacity=5))
    
    return network

def read_trips(filepath):
    trips = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trips.append({
                "driver_id": row["driver_id"],
                "trip_number": int(row["trip_number"]),
                "start_node": row["start_node"],
                "goal_node": row["goal_node"],
                "route": row["route_taken"],
                "time": float(row["total_trip_time"]),
                "distance": float(row["total_distance"]),
                "avg_speed": float(row["average_speed"]),
                "avg_stress": float(row["average_stress"]),
            })
    return trips

def read_road_snapshots(filepath):
    snapshots = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            snapshots.append(row)
    return snapshots

def analyse_road_usage(trips):
    """Count how many times each road is used across all trips."""
    usage = {}
    for t in trips:
        for road in t["route"].split("->"):
            usage[road] = usage.get(road, 0) + 1
    return usage

def analyse_road_density(snapshots):
    """Get average density per road from snapshots."""
    densities = {}
    counts = {}
    for s in snapshots:
        rid = s["road_id"]
        d = float(s["density"])
        densities[rid] = densities.get(rid, 0) + d
        counts[rid] = counts.get(rid, 0) + 1
    return {rid: densities[rid] / counts[rid] for rid in densities}

def analyse_road_speeds(snapshots):
    """Get average speed per road from snapshots."""
    speeds = {}
    counts = {}
    for s in snapshots:
        rid = s["road_id"]
        sp = float(s["current_speed_kmh"])
        speeds[rid] = speeds.get(rid, 0) + sp
        counts[rid] = counts.get(rid, 0) + 1
    return {rid: speeds[rid] / counts[rid] for rid in speeds}


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 42
DURATION = 3000
NUM_DRIVERS = 80
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results', 'full_simulation')

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# SCENARIO 1: ALL BASE A*
# ============================================================

print(f"{'='*60}")
print(f"SCENARIO 1: ALL BASE A* ({NUM_DRIVERS} drivers)")
print(f"  All roads: 50 km/h, capacity 5 — uniform network")
print(f"  Random origins/destinations, duration={DURATION}s")
print(f"{'='*60}")

random.seed(SEED)
net1 = build_network()

drivers1 = []
for i in range(NUM_DRIVERS):
    drivers1.append(Driver(f"Base_{i}", net1, stress_tolerance=0.0, familiarity_weight=0.0, learning_rate=0.0))

col1 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllBaseAStar"), log_interval=60)
sim1 = Simulation(net1, drivers1, col1)
sim1.run(duration=DURATION, time_step=1.0)

fig, ax = visualize_network_with_traffic(net1, f"All Base A* — Final State")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_astar.png"), dpi=150)
plt.close()


# ============================================================
# SCENARIO 2: ALL ADAPTIVE (random personalities)
# ============================================================

print(f"\n{'='*60}")
print(f"SCENARIO 2: ALL ADAPTIVE ({NUM_DRIVERS} drivers, random personalities)")
print(f"  Same network, same seed for destinations")
print(f"{'='*60}")

random.seed(SEED)
net2 = build_network()

drivers2 = []
random.seed(SEED + 1)
for i in range(NUM_DRIVERS):
    drivers2.append(Driver(
        f"Adaptive_{i}", net2,
        stress_tolerance=random.uniform(0.1, 0.9),
        familiarity_weight=random.uniform(0.1, 0.9),
        learning_rate=random.uniform(0.1, 0.5),
    ))

print(f"  Sample personalities:")
for d in drivers2[:5]:
    print(f"    {d.id}: ω_f={d.familiarity_weight:.2f}, ω_s={d.stress_tolerance:.2f}, α={d.learning_rate:.2f}")

random.seed(SEED)
col2 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "AllAdaptive"), log_interval=60)
sim2 = Simulation(net2, drivers2, col2)
sim2.run(duration=DURATION, time_step=1.0)

fig, ax = visualize_network_with_traffic(net2, f"All Adaptive — Final State")
plt.savefig(os.path.join(OUTPUT_DIR, "network_all_adaptive.png"), dpi=150)
plt.close()


# ============================================================
# ANALYSIS
# ============================================================

trips1 = read_trips(os.path.join(OUTPUT_DIR, "AllBaseAStar", "trips.csv"))
trips2 = read_trips(os.path.join(OUTPUT_DIR, "AllAdaptive", "trips.csv"))
snaps1 = read_road_snapshots(os.path.join(OUTPUT_DIR, "AllBaseAStar", "road_snapshots.csv"))
snaps2 = read_road_snapshots(os.path.join(OUTPUT_DIR, "AllAdaptive", "road_snapshots.csv"))

print(f"\n{'='*60}")
print(f"GENERAL PERFORMANCE")
print(f"{'='*60}")

print(f"\n  Trips completed:")
print(f"    Base A*:  {len(trips1)}")
print(f"    Adaptive: {len(trips2)}")

avg_time1 = sum(t["time"] for t in trips1) / len(trips1) if trips1 else 0
avg_time2 = sum(t["time"] for t in trips2) / len(trips2) if trips2 else 0
print(f"\n  Average trip time:")
print(f"    Base A*:  {avg_time1:.1f}s")
print(f"    Adaptive: {avg_time2:.1f}s")
if avg_time2 < avg_time1:
    print(f"    Adaptive is {avg_time1-avg_time2:.1f}s faster ({(avg_time1-avg_time2)/avg_time1*100:.1f}%)")

routes1 = set(t["route"] for t in trips1)
routes2 = set(t["route"] for t in trips2)
print(f"\n  Unique routes:")
print(f"    Base A*:  {len(routes1)}")
print(f"    Adaptive: {len(routes2)}")


# ============================================================
# ROAD-BY-ROAD ANALYSIS
# ============================================================

print(f"\n{'='*60}")
print(f"ROAD-BY-ROAD ANALYSIS")
print(f"{'='*60}")

density1 = analyse_road_density(snaps1)
density2 = analyse_road_density(snaps2)
speed1 = analyse_road_speeds(snaps1)
speed2 = analyse_road_speeds(snaps2)
usage1 = analyse_road_usage(trips1)
usage2 = analyse_road_usage(trips2)

# All roads sorted by density (Base A*)
all_roads = sorted(density1.keys(), key=lambda r: density1[r], reverse=True)

print(f"\n  {'Road':<6} | {'--- Base A* ---':^30} | {'--- Adaptive ---':^30}")
print(f"  {'':6} | {'Density':>8} {'Speed':>10} {'Usage':>8} | {'Density':>8} {'Speed':>10} {'Usage':>8}")
print(f"  {'-'*6}-+-{'-'*30}-+-{'-'*30}")

for rid in all_roads:
    d1 = density1.get(rid, 0)
    d2 = density2.get(rid, 0)
    s1 = speed1.get(rid, 50)
    s2 = speed2.get(rid, 50)
    u1 = usage1.get(rid, 0)
    u2 = usage2.get(rid, 0)
    print(f"  {rid:<6} | {d1:>8.3f} {s1:>8.1f}km/h {u1:>7} | {d2:>8.3f} {s2:>8.1f}km/h {u2:>7}")


# ============================================================
# HOTSPOT ANALYSIS
# ============================================================

print(f"\n{'='*60}")
print(f"HOTSPOT ANALYSIS (most congested roads)")
print(f"{'='*60}")

# Top 5 most congested roads for each scenario
top5_base = sorted(density1.items(), key=lambda x: x[1], reverse=True)[:5]
top5_adaptive = sorted(density2.items(), key=lambda x: x[1], reverse=True)[:5]

print(f"\n  Top 5 congested roads (Base A*):")
for rid, d in top5_base:
    s = speed1.get(rid, 50)
    u = usage1.get(rid, 0)
    print(f"    {rid}: density={d:.3f}, avg_speed={s:.1f}km/h, used {u} times")

print(f"\n  Top 5 congested roads (Adaptive):")
for rid, d in top5_adaptive:
    s = speed2.get(rid, 50)
    u = usage2.get(rid, 0)
    print(f"    {rid}: density={d:.3f}, avg_speed={s:.1f}km/h, used {u} times")

# Congestion spread — standard deviation of density
import statistics
densities_list1 = [d for d in density1.values()]
densities_list2 = [d for d in density2.values()]
std1 = statistics.stdev(densities_list1)
std2 = statistics.stdev(densities_list2)
max1 = max(densities_list1)
max2 = max(densities_list2)
min1 = min(densities_list1)
min2 = min(densities_list2)

print(f"\n  Congestion distribution:")
print(f"    Base A*:  mean={statistics.mean(densities_list1):.3f}, std={std1:.3f}, min={min1:.3f}, max={max1:.3f}")
print(f"    Adaptive: mean={statistics.mean(densities_list2):.3f}, std={std2:.3f}, min={min2:.3f}, max={max2:.3f}")

if std2 < std1:
    print(f"    Adaptive has {((std1-std2)/std1)*100:.1f}% lower congestion variance — more evenly distributed")


# ============================================================
# UNDERUSED ROADS
# ============================================================

print(f"\n{'='*60}")
print(f"UNDERUSED ROADS (lowest density)")
print(f"{'='*60}")

bottom5_base = sorted(density1.items(), key=lambda x: x[1])[:5]
bottom5_adaptive = sorted(density2.items(), key=lambda x: x[1])[:5]

print(f"\n  Least used roads (Base A*):")
for rid, d in bottom5_base:
    u = usage1.get(rid, 0)
    print(f"    {rid}: density={d:.3f}, used {u} times")

print(f"\n  Least used roads (Adaptive):")
for rid, d in bottom5_adaptive:
    u = usage2.get(rid, 0)
    print(f"    {rid}: density={d:.3f}, used {u} times")

print(f"\n  Saved data to {OUTPUT_DIR}/")