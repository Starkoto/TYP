import json
import math
from typing import Dict, List, Tuple, Optional

"""
UNITS USED IN THIS SIMULATION:
- Distance: meters (m)
- Speed: km/h (stored), m/s (internal calculations)
- Time: seconds (s)
- Capacity: number of vehicles
"""

class Node:

    def __init__(self, node_id: str, x: float, y: float):

        self.id = node_id
        self.x = x
        self.y = y

    def euc_distance(self, other: 'Node') -> float:

        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __repr__(self) -> str:
        return f"Node({self.id}, x={self.x}, y={self.y})"
    
class Road:
    
    def __init__(self, road_id: str, start_node: Node, end_node: Node, speed_limit_kmh: float, capacity: int, base_stress: float = 0.0):

        self.id = road_id
        self.start = start_node
        self.end = end_node
        
        self.speed_limit_kmh = speed_limit_kmh # Storing speed limit in km/h for readability
        
        # Convert to m/s for internal calculations
        # 50 km/h = 50 * 1000 / 3600 = 13.89 m/s
        self.speed_limit = speed_limit_kmh * 1000 / 3600
        
        self.capacity = capacity
        self.distance = start_node.euc_distance(end_node)  # Distance in meters
        self.vehicles = []
        self.current_speed = self.speed_limit  # Start at speed limit (m/s)
        self.base_stress = base_stress

    def get_density(self) -> float:
        return len(self.vehicles) / self.capacity
    
    def update_speed(self):
        density = self.get_density()

        if density <= 0.5:
            self.current_speed = self.speed_limit
        elif density <= 1.0:
            reduction_factor = 1.0 - (1.0 * (density - 0.5))
            self.current_speed = self.speed_limit * reduction_factor

    def get_stress_level(self):
        density = self.get_density()
        speed_ratio = self.current_speed / self.speed_limit
        
        congestion_stress = density * (1 - speed_ratio)
        
        total_stress = self.base_stress + congestion_stress
        return min(total_stress, 1.0)
    
    def has_space(self) -> bool:
        return len(self.vehicles) < self.capacity
    
    def is_at_capacity(self) -> bool:
        return len(self.vehicles) >= self.capacity

    def add_vehicle(self, vehicle):
        self.vehicles.append(vehicle)
        self.update_speed()

    def remove_vehicle(self, vehicle):
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
            self.update_speed()

    def __repr__(self) -> str:
        return f"Road({self.id}: {self.start.id}->{self.end.id}, " \
               f"speed={self.current_speed:.1f}/{self.speed_limit}, " \
               f"vehicles={len(self.vehicles)}/{self.capacity})"
    
class TrafficNetwork:
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.roads: Dict[str, Road] = {}
        self.adjacency: Dict[str, List[Road]] = {}
    
    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        if node.id not in self.adjacency:
            self.adjacency[node.id] = []
    
    def add_road(self, road: Road) -> None:
        self.roads[road.id] = road
        
        start_id = road.start.id
        if start_id not in self.adjacency:
            self.adjacency[start_id] = []
        self.adjacency[start_id].append(road)
    
    def get_neighbors(self, node_id: str) -> List[Tuple[Node, Road]]:
        neighbors = []
        for road in self.adjacency.get(node_id, []):
            neighbors.append((road.end, road))
        return neighbors
    
    def update_all_speeds(self) -> None:
        for road in self.roads.values():
            road.update_speed()
    
    @classmethod
    def from_json(cls, filepath: str) -> 'TrafficNetwork':

        with open(filepath, 'r') as f:
            data = json.load(f)
        
        network = cls()
        
        # Create nodes
        for node_data in data['nodes']:
            node = Node(
                node_id=node_data['id'],
                x=node_data['x'],
                y=node_data['y']
            )
            network.add_node(node)
        
        # Create roads
        for road_data in data['roads']:
            start_node = network.nodes[road_data['start']]
            end_node = network.nodes[road_data['end']]
            
            road = Road(
                road_id=road_data['id'],
                start_node=start_node,
                end_node=end_node,
                speed_limit_kmh=road_data['speed_limit'],
                capacity=road_data['capacity'],
                base_stress=road_data.get('base_stress', 0.0)
            )
            network.add_road(road)
        
        return network
    
    def __repr__(self) -> str:
        return f"TrafficNetwork(nodes={len(self.nodes)}, roads={len(self.roads)})"

