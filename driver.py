from typing import Dict, List, Optional
from vehicle import Vehicle

class Driver:

    def __init__(self, driver_id: str, pathfinder, stress_tolerance: float = 0.5, familiarity_weight: float = 0.5, learning_rate: float = 0.3, fixed_route: List[str] = None):

        self.id = driver_id
        self.pathfinder = pathfinder

        # Personality paramenters
        self.stress_tolarence = stress_tolerance
        self.familiarity_weight = familiarity_weight
        self.learning_rate = learning_rate

        # For testing out specific routes like A to B back and forward
        self.fixed_route = fixed_route
        self.last_goal = None

        self.memory: Dict[str, Dict] = {}

        self.current_vehicle: Optional[Vehicle] = None
        self.trip_count = 0

        self.current_trip_data = {
            "start_node": None,
            "goal_node": None,
            "roads_traveled": [],
            "total_time": 0.0,
            "total_distance": 0.0,
            "speed_observations": [],
            "stress_observations": []
        }