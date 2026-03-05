from network import Node, Road, TrafficNetwork
from pathfinding import AStar
from vehicle import Vehicle

# Create network in code (no JSON needed!)
print("Creating network...")
network = TrafficNetwork()

# Add nodes
node_a = Node("A", 0, 0)
node_b = Node("B", 100, 0)
node_c = Node("C", 200, 0)

network.add_node(node_a)
network.add_node(node_b)
network.add_node(node_c)

# Add roads
road_ab = Road("AB", node_a, node_b, speed_limit=50, capacity=10)
road_bc = Road("BC", node_b, node_c, speed_limit=50, capacity=10)

network.add_road(road_ab)
network.add_road(road_bc)

print(f"✓ Network created: {len(network.nodes)} nodes, {len(network.roads)} roads\n")

# Create pathfinder
pathfinder = AStar(network)

# Test 1: Create vehicle with A*
print("TEST 1: Creating vehicle with A*...")
car1 = Vehicle("Car1", start_node="A", goal_node="C", pathfinder=pathfinder)

print(f"✓ Vehicle created!")
print(f"  Route: {' → '.join([r.start.id for r in car1.route] + [car1.route[-1].end.id])}")
print(f"  Roads: {[r.id for r in car1.route]}")
print()

# Test 2: Old way still works!
print("TEST 2: Creating vehicle old way (with route)...")
car2 = Vehicle("Car2", route=[road_ab, road_bc])
print(f"✓ Old way still works!")
print(f"  Route: {' → '.join([r.start.id for r in car2.route] + [car2.route[-1].end.id])}")
print()

print("="*60)
print("✅ ALL TESTS PASSED!")
print("A* is successfully connected to vehicles!")
print("="*60)