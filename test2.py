from network import Node, Road, TrafficNetwork
from driver import Driver
from simulation import Simulation
from dataCollection import DataCollector

print("=== Simple Integration Test ===\n")

# Create a simple network: A -> B -> C (with return roads)
print("1. Creating network...")
network = TrafficNetwork()

node_a = Node("A", 0, 0)
node_b = Node("B", 100, 0)
node_c = Node("C", 200, 0)

network.add_node(node_a)
network.add_node(node_b)
network.add_node(node_c)

road_ab = Road("AB", node_a, node_b, speed_limit_kmh=50, capacity=10)
road_bc = Road("BC", node_b, node_c, speed_limit_kmh=50, capacity=10)
road_ba = Road("BA", node_b, node_a, speed_limit_kmh=50, capacity=10)
road_cb = Road("CB", node_c, node_b, speed_limit_kmh=50, capacity=10)

network.add_road(road_ab)
network.add_road(road_bc)
network.add_road(road_ba)
network.add_road(road_cb)

print(f"   Nodes: {list(network.nodes.keys())}")
print(f"   Roads: {list(network.roads.keys())}")

# Create one driver with fixed route A <-> C
print("\n2. Creating driver...")
driver = Driver(
    driver_id="TestDriver",
    network=network,
    stress_tolerance=0.5,
    familiarity_weight=0.5,
    learning_rate=0.3,
    fixed_route=["A", "C"]
)
print(f"   {driver}")

# Create data collector
print("\n3. Creating data collector...")
collector = DataCollector(output_dir="test_output", log_interval=10)
print(f"   Trips file: {collector.trips_file}")
print(f"   Roads file: {collector.roads_file}")

# Create simulation
print("\n4. Creating simulation...")
sim = Simulation(network, [driver], collector)

# Run for 100 seconds
print("\n5. Running simulation for 100 seconds...")
sim.run(duration=100, time_step=1.0)

# Check results
print("\n6. Checking results...")
print(f"   Driver completed {driver.trip_count} trips")
print(f"   Driver memory: {driver.memory}")

# Show CSV contents
print("\n7. CSV Contents:")
print("\n--- trips.csv ---")
with open("test_output/trips.csv", "r") as f:
    print(f.read())

print("--- road_snapshots.csv ---")
with open("test_output/road_snapshots.csv", "r") as f:
    content = f.read()
    lines = content.strip().split('\n')
    # Show header and first few lines
    for line in lines[:6]:
        print(line)
    if len(lines) > 6:
        print(f"... ({len(lines) - 1} total rows)")

print("\n=== Test Complete ===")