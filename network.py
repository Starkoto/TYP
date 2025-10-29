import json
import math
from typing import Dict, List, Tuple, Optional

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
    
    def __init__(self, road_id: str, start_node: Node, end_node: Node, speed_limit: float, capacity: int):

        
        pass