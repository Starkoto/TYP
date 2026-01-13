import heapq
from typing import List, Dict, Tuple, Optional


class AStar:    
    def __init__(self, network):

        self.network = network
        
        # Find maximum speed in network for heuristic
        # (heuristic assumes best case: traveling at max speed)
        self.max_speed = max(road.speed_limit for road in network.roads.values()) if network.roads else 60
    
    def heuristic(self, node_id: str, goal_id: str) -> float:

        node = self.network.nodes[node_id]
        goal = self.network.nodes[goal_id]
        distance = node.euc_distance(goal)
        
        # Best case: straight line at maximum speed
        # This never overestimates because:
        # 1. Can't travel faster than max_speed
        # 2. Straight line is shortest distance
        return distance / self.max_speed
    
    def get_edge_cost(self, road) -> float:
        """
        Calculate cost of traveling along a road.
        For standard A*, uses: distance / speed_limit (travel time)
        
        Args:
            road: Road object
            
        Returns:
            Cost of using this road (travel time)
        """
        # Cost = distance / speed (time to traverse)
        # Using speed_limit (static cost, not affected by current traffic)
        return road.distance / road.speed_limit
    
    def find_path(self, start_id: str, goal_id: str) -> Optional[List]:
        """
        Find the shortest path from start to goal using A*.
        
        Args:
            start_id: Starting node ID
            goal_id: Goal node ID
            
        Returns:
            List of Road objects representing the path, or None if no path exists
        """
        # Check that start and goal exist
        if start_id not in self.network.nodes or goal_id not in self.network.nodes:
            return None
        
        # If start == goal, return empty path
        if start_id == goal_id:
            return []
        
        # Priority queue: (f_score, node_id)
        open_set = []
        heapq.heappush(open_set, (0, start_id))
        
        # Track where we came from: node_id -> (previous_node_id, road_used)
        came_from: Dict[str, Tuple[str, object]] = {}
        
        # g_score: cost from start to each node
        g_score: Dict[str, float] = {start_id: 0}
        
        # f_score: g + h for each node
        f_score: Dict[str, float] = {start_id: self.heuristic(start_id, goal_id)}
        
        # Nodes in open set (for quick lookup)
        open_set_hash = {start_id}
        
        while open_set:
            # Get node with lowest f_score
            current_f, current = heapq.heappop(open_set)
            open_set_hash.remove(current)
            
            # Found the goal!
            if current == goal_id:
                return self._reconstruct_path(came_from, current)
            
            # Explore neighbors
            neighbors = self.network.get_neighbors(current)
            
            for neighbor_node, road in neighbors:
                neighbor_id = neighbor_node.id
                
                # Calculate tentative g_score
                tentative_g = g_score[current] + self.get_edge_cost(road)
                
                # If this path to neighbor is better than previous
                if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
                    # Record this path
                    came_from[neighbor_id] = (current, road)
                    g_score[neighbor_id] = tentative_g
                    f = tentative_g + self.heuristic(neighbor_id, goal_id)
                    f_score[neighbor_id] = f
                    
                    # Add to open set if not already there
                    if neighbor_id not in open_set_hash:
                        heapq.heappush(open_set, (f, neighbor_id))
                        open_set_hash.add(neighbor_id)
        
        # No path found
        return None
    
    def _reconstruct_path(self, came_from: Dict[str, Tuple[str, object]], 
                          current: str) -> List:
        """
        Reconstruct the path from start to goal.
        
        Args:
            came_from: Dictionary mapping node_id -> (previous_node, road)
            current: Goal node ID
            
        Returns:
            List of Road objects from start to goal
        """
        path = []
        
        # Work backwards from goal to start
        while current in came_from:
            previous_node, road = came_from[current]
            path.append(road)
            current = previous_node
        
        # Reverse to get start -> goal
        path.reverse()
        
        return path


class AdaptivePathfinder(AStar):
    
    def __init__(self, network, driver=None):
        """
        Initialize adaptive pathfinder.
        
        Args:
            network: TrafficNetwork instance
            driver: DriverMemory instance (for learning)
        """
        super().__init__(network)
        self.driver = driver
    
    def get_edge_cost(self, road) -> float:
        
        # If there is no driver use standard A*
        if self.driver is None:
            return super().get_edge_cost(road)
        
        if road.id in self.driver.memory:
            mem = self.driver.memory[road.id]
            remembered_speed = mem["avg_speed"] / 3.6
            remembered_stress = mem["avg_stress"]
            usage = mem["usage"]
        else:
            remembered_speed = road.speed_limit
            remembered_stress = 0.0
            usage = 0

        base_time = road.distance / remembered_speed

        stress_penalty = remembered_stress * self.driver.stress_tolerance

        familiarity_penalty = self.driver.familiarity_weight / (usage + 1)

        cost = base_time * (1 + stress_penalty + familiarity_penalty)
        
        return cost