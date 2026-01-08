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

    def start_trip(self, start_node: str, goal_node: str, network):

        self.trip_count += 1

        self.current_trip_data = { # Reset trip tracking
            "start_node": start_node,
            "goal_node": goal_node,
            "roads_traveled": [],
            "total_time": 0.0,
            "total_distance": 0.0,
            "speed_observations": [],
            "stress_observations": []
        }

        # Creating vehicle
        self.current_vehicle = Vehicle(vehicle_id=f"{self.id}_trip_{self.trip_count}", start_node=start_node, goal_node=goal_node, pathfinder=self.pathfinder)

        if self.current_vehicle.route:
            first_road = self.current_vehicle.route[0]
            first_road.add_vehicle(self.current_vehicle)
            self.current_trip_data["roads_traveled"].append(first_road.id)

            

