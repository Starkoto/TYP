from network import Node, Road, TrafficNetwork
from driver import Driver

print("=== Test: Does Memory Affect Route Choice? ===\n")

# Create network with two paths from A to C:
#   Path 1: A -> B -> C (short)
#   Path 2: A -> D -> C (longer)

network = TrafficNetwork()

node_a = Node("A", 0, 0)
node_b = Node("B", 100, 0)    # Middle node for short path
node_c = Node("C", 200, 0)
node_d = Node("D", 100, 100)  # Middle node for long path

network.add_node(node_a)
network.add_node(node_b)
network.add_node(node_c)
network.add_node(node_d)

# Short path: A -> B -> C (200m total)
road_ab = Road("AB", node_a, node_b, speed_limit_kmh=50, capacity=10)
road_bc = Road("BC", node_b, node_c, speed_limit_kmh=50, capacity=10)

# Long path: A -> D -> C (longer due to geometry)
road_ad = Road("AD", node_a, node_d, speed_limit_kmh=50, capacity=10)
road_dc = Road("DC", node_d, node_c, speed_limit_kmh=50, capacity=10)

network.add_road(road_ab)
network.add_road(road_bc)
network.add_road(road_ad)
network.add_road(road_dc)

print("Network created:")
print(f"  Short path (A->B->C): {road_ab.distance + road_bc.distance:.0f}m")
print(f"  Long path (A->D->C): {road_ad.distance + road_dc.distance:.0f}m")

# Create a driver
driver = Driver(
    driver_id="TestDriver",
    network=network,
    stress_tolerance=0.5,
    familiarity_weight=0.5,
    learning_rate=0.3
)

# Test 1: With empty memory, driver should take short path
print("\n--- Test 1: Empty memory ---")
route = driver.pathfinder.find_path("A", "C")
path_ids = [r.id for r in route]
print(f"  Route chosen: {' -> '.join(path_ids)}")

# Test 2: Simulate bad experience on short path
print("\n--- Test 2: After bad experience on AB ---")
driver.memory["AB"] = {
    "usage": 5,
    "avg_speed": 10.0,  # Very slow (remembered as 10 km/h instead of 50)
    "avg_stress": 0.8   # Very stressful
}
driver.memory["BC"] = {
    "usage": 5,
    "avg_speed": 10.0,
    "avg_stress": 0.8
}

route = driver.pathfinder.find_path("A", "C")
path_ids = [r.id for r in route]
print(f"  Route chosen: {' -> '.join(path_ids)}")

# Show cost comparison
print("\n--- Cost comparison ---")
print("  Short path (A->B->C):")
cost_ab = driver.pathfinder.get_edge_cost(road_ab)
cost_bc = driver.pathfinder.get_edge_cost(road_bc)
print(f"    AB cost: {cost_ab:.2f}")
print(f"    BC cost: {cost_bc:.2f}")
print(f"    Total: {cost_ab + cost_bc:.2f}")

print("  Long path (A->D->C):")
cost_ad = driver.pathfinder.get_edge_cost(road_ad)
cost_dc = driver.pathfinder.get_edge_cost(road_dc)
print(f"    AD cost: {cost_ad:.2f}")
print(f"    DC cost: {cost_dc:.2f}")
print(f"    Total: {cost_ad + cost_dc:.2f}")

# Verify the test
print("\n--- Result ---")
if path_ids == ["AD", "DC"]:
    print("SUCCESS: Driver avoided bad roads based on memory!")
else:
    print("ISSUE: Driver did not change route despite bad memory")

print("\n=== Test Complete ===")