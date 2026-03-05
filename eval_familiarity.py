import sys
sys.path.insert(0, '/mnt/project')
sys.path.insert(0, '.')  # For visualization.py in the same directory

from network import TrafficNetwork, Node, Road
from driver import Driver
from visualization import visualize_network_with_traffic
from dataCollection import DataCollector
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
            speed = 51 if (s == "A" and e == "B") or (s == "B" and e == "A") else 50
            network.add_road(Road(f"{s}{e}", nodes[s], nodes[e], speed_limit_kmh=speed, capacity=10))
    
    return network

def add_congestion(network, road_id, num_vehicles):
    """Add dummy vehicles to a road to create congestion."""
    road = network.roads[road_id]
    for i in range(num_vehicles):
        road.add_vehicle(DummyVehicle(f"dummy_{i}"))

def reset_network(network, congestion_setup=None):
    """Reset all roads and optionally re-add congestion.
    congestion_setup: dict of {road_id: num_vehicles}
    """
    for road in network.roads.values():
        road.vehicles = []
        road.current_speed = road.speed_limit
    if congestion_setup:
        for road_id, num_v in congestion_setup.items():
            add_congestion(network, road_id, num_v)

def run_trip(driver, network):
    """Run a single trip and return the route taken."""
    while not driver.current_vehicle.has_reached_destination():
        driver.update(1.0)
    return driver.get_trip_summary()

def print_memory(driver):
    """Print driver's current memory state."""
    for road_id, mem in driver.memory.items():
        print(f"    {road_id}: v={mem['avg_speed']:.2f} km/h, σ={mem['avg_stress']:.4f}, u={mem['usage']}")

def print_path_costs(driver, network, path_roads):
    """Print cost breakdown for a specific path."""
    total = 0
    for rid in path_roads:
        cost = driver.pathfinder.get_edge_cost(network.roads[rid])
        total += cost
        
        if rid in driver.memory:
            mem = driver.memory[rid]
            status = f"u={mem['usage']}"
        else:
            status = "unknown"
        print(f"    {rid} ({status}): {cost:.4f}")
    print(f"    TOTAL: {total:.4f}")
    return total


# ============================================================
# CONFIGURATION - Change these to test different scenarios
# ============================================================

CONGESTION = {"AB": 6}          # Which roads have congestion and how many vehicles
NUM_TRIPS = 10                   # How many trips to simulate
DRIVERS = [                      # List of drivers to test
    {"id": "HighFam", "stress_tolerance": 0.0, "familiarity_weight": 0.9, "learning_rate": 0.3},
    {"id": "LowFam",  "stress_tolerance": 0.0, "familiarity_weight": 0.1, "learning_rate": 0.3},
]
PATH_AB = ["AB", "BE", "EF", "FI"]   # Path through B
PATH_AD = ["AD", "DE", "EF", "FI"]   # Path through D
OUTPUT_DIR = "test_output"            # Where to save visualizations

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# ============================================================
# RUN TEST
# ============================================================

# Visualize initial network state
init_network = build_network()
reset_network(init_network, CONGESTION)
fig, ax = visualize_network_with_traffic(init_network, "Initial Network State")
plt.savefig(os.path.join(OUTPUT_DIR, "network_initial.png"), dpi=150)
plt.close()
print(f"Saved initial network visualization to {OUTPUT_DIR}/network_initial.png")

for driver_config in DRIVERS:
    network = build_network()
    
    driver = Driver(
        driver_id=driver_config["id"],
        network=network,
        stress_tolerance=driver_config["stress_tolerance"],
        familiarity_weight=driver_config["familiarity_weight"],
        learning_rate=driver_config["learning_rate"],
    )
    
    # Create data collector for this driver
    driver_output_dir = os.path.join(OUTPUT_DIR, driver_config["id"])
    collector = DataCollector(output_dir=driver_output_dir, log_interval=1)
    
    print(f"\n{'='*60}")
    print(f"DRIVER: {driver_config['id']}")
    print(f"  ω_f={driver_config['familiarity_weight']}, ω_s={driver_config['stress_tolerance']}, α={driver_config['learning_rate']}")
    print(f"{'='*60}")
    
    for trip in range(1, NUM_TRIPS + 1):
        reset_network(network, CONGESTION)
        
        driver.current_vehicle = None
        driver.start_trip("A", "I", network)
        route = [r.id for r in driver.current_vehicle.route]
        
        # Show path cost comparison before driving
        ab_total = sum(driver.pathfinder.get_edge_cost(network.roads[r]) for r in PATH_AB)
        ad_total = sum(driver.pathfinder.get_edge_cost(network.roads[r]) for r in PATH_AD)
        
        # Log road state at start of trip
        collector.log_roads(driver.trip_count, network.roads)
        
        run_trip(driver, network)
        
        # Log completed trip
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
        
        ab_mem_speed = driver.memory.get("AB", {}).get("avg_speed", "-")
        ab_usage = driver.memory.get("AB", {}).get("usage", 0)
        
        if isinstance(ab_mem_speed, float):
            print(f"\n  Trip {trip}: route={' → '.join(route)} | AB path={ab_total:.4f} | AD path={ad_total:.4f} | v̄_AB={ab_mem_speed:.2f} km/h (u={ab_usage})")
        else:
            print(f"\n  Trip {trip}: route={' → '.join(route)} | AB path={ab_total:.4f} | AD path={ad_total:.4f}")
        
        # Show detailed costs on first trip, switching trip, and last trip
        if trip == 1 or trip == NUM_TRIPS or (trip > 1 and route[0] != "AB" and 
            any(r.id == "AB" for r in Driver(driver_config["id"], network, 
                stress_tolerance=driver_config["stress_tolerance"],
                familiarity_weight=driver_config["familiarity_weight"]).pathfinder.find_path("A", "I") or [])):
            print(f"    AB path breakdown:")
            print_path_costs(driver, network, PATH_AB)
            print(f"    AD path breakdown:")
            print_path_costs(driver, network, PATH_AD)
            print(f"    Memory:")
            print_memory(driver)
    
    # Visualize final network state for this driver
    reset_network(network, CONGESTION)
    fig, ax = visualize_network_with_traffic(network, f"{driver_config['id']} (ω_f={driver_config['familiarity_weight']}) - Final State")
    plt.savefig(os.path.join(OUTPUT_DIR, f"network_{driver_config['id']}.png"), dpi=150)
    plt.close()
    print(f"\n  Saved visualization to {OUTPUT_DIR}/network_{driver_config['id']}.png")
    print(f"  Saved trip data to {driver_output_dir}/trips.csv")
    print(f"  Saved road snapshots to {driver_output_dir}/road_snapshots.csv")