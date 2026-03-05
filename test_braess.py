import sys
sys.path.insert(0, '/mnt/project')
sys.path.insert(0, '.')

from network import TrafficNetwork, Node, Road
from driver import Driver
from visualization import visualize_network_with_traffic
from dataCollection import DataCollector
import matplotlib.pyplot as plt
import os

def build_braess_network(include_shortcut=False):
    """
    Braess's Paradox network:
    
    Route 1: A -> S -> B  (fast then slow)
    Route 2: A -> T -> B  (slow then fast)
    Shortcut: S -> T      (very fast, added for paradox)
    
         A
        / \
       S   T
        \ /
         B
    """
    network = TrafficNetwork()
    
    nodes = {
        "A": Node("A", 100, 200),   # Top
        "S": Node("S", 0, 100),     # Left middle
        "T": Node("T", 200, 100),   # Right middle
        "B": Node("B", 100, 0),     # Bottom
    }
    for n in nodes.values():
        network.add_node(n)
    
    # Route 1: A -> S (fast, low capacity) -> S -> B (slow, high capacity)
    # Route 2: A -> T (slow, high capacity) -> T -> B (fast, low capacity)
    
    # A -> S: fast (80 km/h) but low capacity (5) — congests easily
    network.add_road(Road("AS", nodes["A"], nodes["S"], speed_limit_kmh=80, capacity=5))
    # S -> B: slow (30 km/h) but high capacity (50) — never congests
    network.add_road(Road("SB", nodes["S"], nodes["B"], speed_limit_kmh=30, capacity=50))
    
    # A -> T: slow (30 km/h) but high capacity (50) — never congests
    network.add_road(Road("AT", nodes["A"], nodes["T"], speed_limit_kmh=30, capacity=50))
    # T -> B: fast (80 km/h) but low capacity (5) — congests easily
    network.add_road(Road("TB", nodes["T"], nodes["B"], speed_limit_kmh=80, capacity=5))
    
    if include_shortcut:
        # S -> T: very fast (200 km/h), high capacity — the paradox trigger
        network.add_road(Road("ST", nodes["S"], nodes["T"], speed_limit_kmh=200, capacity=50))
    
    return network

def reset_network(network):
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit

def run_simulation(network, drivers, num_trips, collector):
    """Run multiple trips for all drivers simultaneously."""
    results = []
    
    for trip in range(1, num_trips + 1):
        reset_network(network)
        
        # Start all drivers
        for driver in drivers:
            driver.current_vehicle = None
            driver.start_trip("A", "B", network)
        
        # Step simulation until all drivers finish
        max_steps = 5000
        step = 0
        active = set(range(len(drivers)))
        
        while active and step < max_steps:
            for i in list(active):
                finished = drivers[i].update(1.0)
                if finished:
                    active.discard(i)
            step += 1
        
        # Collect results
        trip_times = []
        trip_routes = []
        for driver in drivers:
            summary = driver.get_trip_summary()
            trip_times.append(summary["trip_time"])
            trip_routes.append(summary["route_taken"])
            
            collector.log_trip(
                driver_id=summary["driver_id"],
                trip_number=trip,
                start_node=summary["start_node"],
                goal_node=summary["goal_node"],
                route_taken=summary["route_taken"],
                trip_time=summary["trip_time"],
                distance=summary["distance"],
                avg_speed=summary["avg_speed"],
                avg_stress=summary["avg_stress"]
            )
        
        avg_time = sum(trip_times) / len(trip_times)
        
        # Count route choices
        route_counts = {}
        for route in trip_routes:
            key = "->".join(route)
            route_counts[key] = route_counts.get(key, 0) + 1
        
        results.append({
            "trip": trip,
            "avg_time": avg_time,
            "min_time": min(trip_times),
            "max_time": max(trip_times),
            "routes": route_counts
        })
    
    return results


# ============================================================
# CONFIGURATION
# ============================================================

NUM_DRIVERS = 8
NUM_TRIPS = 15
OUTPUT_DIR = "test_braess"

# All drivers with same moderate parameters
DRIVER_PARAMS = {
    "stress_tolerance": 0.0,
    "familiarity_weight": 0.1,
    "learning_rate": 0.3,
}

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# PHASE 1: WITHOUT SHORTCUT
# ============================================================

print(f"{'='*60}")
print(f"PHASE 1: WITHOUT SHORTCUT ({NUM_DRIVERS} drivers)")
print(f"{'='*60}")
print(f"  Route 1: A->S->B (AS: 80km/h cap=5, SB: 30km/h cap=50)")
print(f"  Route 2: A->T->B (AT: 30km/h cap=50, TB: 80km/h cap=5)")

network_no_shortcut = build_braess_network(include_shortcut=False)

# Visualize
fig, ax = visualize_network_with_traffic(network_no_shortcut, "Braess Network - No Shortcut")
plt.savefig(os.path.join(OUTPUT_DIR, "network_no_shortcut.png"), dpi=150)
plt.close()

# Create drivers
drivers_phase1 = []
for i in range(NUM_DRIVERS):
    d = Driver(
        driver_id=f"D{i}",
        network=network_no_shortcut,
        stress_tolerance=DRIVER_PARAMS["stress_tolerance"],
        familiarity_weight=DRIVER_PARAMS["familiarity_weight"],
        learning_rate=DRIVER_PARAMS["learning_rate"],
    )
    drivers_phase1.append(d)

collector_phase1 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "no_shortcut"), log_interval=1)
results_phase1 = run_simulation(network_no_shortcut, drivers_phase1, NUM_TRIPS, collector_phase1)

for r in results_phase1:
    routes_str = ", ".join(f"{k}: {v}" for k, v in r["routes"].items())
    print(f"  Trip {r['trip']:2d}: avg_time={r['avg_time']:.1f}s | {routes_str}")

final_avg_no_shortcut = results_phase1[-1]["avg_time"]
print(f"\n  Final average trip time: {final_avg_no_shortcut:.1f}s")


# ============================================================
# PHASE 2: WITH SHORTCUT
# ============================================================

print(f"\n{'='*60}")
print(f"PHASE 2: WITH SHORTCUT S->T ({NUM_DRIVERS} drivers)")
print(f"{'='*60}")
print(f"  Route 1: A->S->B (same as before)")
print(f"  Route 2: A->T->B (same as before)")
print(f"  Route 3: A->S->T->B (uses shortcut: ST: 200km/h cap=50)")

network_shortcut = build_braess_network(include_shortcut=True)

# Visualize
fig, ax = visualize_network_with_traffic(network_shortcut, "Braess Network - With Shortcut")
plt.savefig(os.path.join(OUTPUT_DIR, "network_with_shortcut.png"), dpi=150)
plt.close()

# Create fresh drivers (no memory from phase 1)
drivers_phase2 = []
for i in range(NUM_DRIVERS):
    d = Driver(
        driver_id=f"D{i}",
        network=network_shortcut,
        stress_tolerance=DRIVER_PARAMS["stress_tolerance"],
        familiarity_weight=DRIVER_PARAMS["familiarity_weight"],
        learning_rate=DRIVER_PARAMS["learning_rate"],
    )
    drivers_phase2.append(d)

collector_phase2 = DataCollector(output_dir=os.path.join(OUTPUT_DIR, "with_shortcut"), log_interval=1)
results_phase2 = run_simulation(network_shortcut, drivers_phase2, NUM_TRIPS, collector_phase2)

for r in results_phase2:
    routes_str = ", ".join(f"{k}: {v}" for k, v in r["routes"].items())
    print(f"  Trip {r['trip']:2d}: avg_time={r['avg_time']:.1f}s | {routes_str}")

final_avg_shortcut = results_phase2[-1]["avg_time"]
print(f"\n  Final average trip time: {final_avg_shortcut:.1f}s")


# ============================================================
# COMPARISON
# ============================================================

print(f"\n{'='*60}")
print(f"BRAESS'S PARADOX COMPARISON")
print(f"{'='*60}")
print(f"  Without shortcut: {final_avg_no_shortcut:.1f}s average trip time")
print(f"  With shortcut:    {final_avg_shortcut:.1f}s average trip time")

if final_avg_shortcut > final_avg_no_shortcut:
    increase = final_avg_shortcut - final_avg_no_shortcut
    pct = (increase / final_avg_no_shortcut) * 100
    print(f"  PARADOX CONFIRMED: Adding the shortcut INCREASED travel time by {increase:.1f}s ({pct:.1f}%)")
else:
    decrease = final_avg_no_shortcut - final_avg_shortcut
    pct = (decrease / final_avg_no_shortcut) * 100
    print(f"  No paradox: shortcut reduced travel time by {decrease:.1f}s ({pct:.1f}%)")

print(f"\n  Saved data to {OUTPUT_DIR}/")