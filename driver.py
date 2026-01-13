from typing import Dict, List, Optional
from vehicle import Vehicle
from pathfinding import AdaptivePathfinder

class Driver:

    def __init__(self, driver_id: str, network, stress_tolerance: float = 0.5, familiarity_weight: float = 0.5, learning_rate: float = 0.3, fixed_route: List[str] = None):

        self.id = driver_id
        self.pathfinder = AdaptivePathfinder(network, driver=self)

        # Personality paramenters
        self.stress_tolerance = stress_tolerance
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


    def update(self, time_step: float):

        if self.current_vehicle is None:
            return False
        
        if self.current_vehicle.has_reached_destination():
            return False
        
        road = self.current_vehicle.get_current_road()
        if road:
            self.current_trip_data["speed_observations"].append(road.current_speed * 3.6)  # km/h
            self.current_trip_data["stress_observations"].append(road.get_stress_level())

        old_road_index = self.current_vehicle.route_index

        self.current_vehicle.update_position(time_step)
        self.current_trip_data["total_time"] += time_step

        # Check if moved to a new road
        new_road_index = self.current_vehicle.route_index
        if new_road_index > old_road_index and new_road_index < len(self.current_vehicle.route):
            new_road = self.current_vehicle.route[new_road_index]
            self.current_trip_data["roads_traveled"].append(new_road.id)
        
        # Check if trip finished
        if self.current_vehicle.has_reached_destination():
            self.finish_trip()
            return True
        
        return False
    
    # Getting next destination for fixed route
    def get_next_destination(self, current_node: str, all_nodes: List[str]) -> str:

        # Alternate endpoints so it goes A->B->A... 
        if self.fixed_route:
            if current_node == self.fixed_route[0]:
                return self.fixed_route[1]
            else:
                return self.fixed_route[0]
        else:
            return None # If not fixed route then random handled by simulation
        
    def finish_trip(self):

        for road_id in self.current_trip_data["roads_traveled"]:
            for road in self.current_vehicle.route:
                if road.id == road_id:
                    self.current_trip_data["total_distance"] += road.distance
                    break

        for road in self.current_vehicle.route:
            road_id = road.id

            if road_id not in self.memory:
                self.memory[road_id] = {
                    "usage": 0,
                    "avg_speed": road.speed_limit * 3.6,  # Start with speed limit in km/h
                    "avg_stress": 0.0
                }

            if self.current_trip_data["speed_observations"]:
                observed_speed = sum(self.current_trip_data["speed_observations"]) / len(self.current_trip_data["speed_observations"])
            else:
                observed_speed = self.memory[road_id]["avg_speed"] # If not just use what is already stored
            
            if self.current_trip_data["stress_observations"]:
                observed_stress = sum(self.current_trip_data["stress_observations"]) / len(self.current_trip_data["stress_observations"])
            else:
                observed_stress = self.memory[road_id]["avg_stress"]
            
            # Update memory using learning rate
            mem = self.memory[road_id]
            mem["usage"] += 1
            mem["avg_speed"] = mem["avg_speed"] + self.learning_rate * (observed_speed - mem["avg_speed"])
            mem["avg_stress"] = mem["avg_stress"] + self.learning_rate * (observed_stress - mem["avg_stress"])

    def get_trip_summary(self) -> Dict:
        # Get summary of completed trip for logging
        
        avg_speed = 0.0
        avg_stress = 0.0
        
        if self.current_trip_data["speed_observations"]:
            avg_speed = sum(self.current_trip_data["speed_observations"]) / len(self.current_trip_data["speed_observations"])
        
        if self.current_trip_data["stress_observations"]:
            avg_stress = sum(self.current_trip_data["stress_observations"]) / len(self.current_trip_data["stress_observations"])
        
        return {
            "driver_id": self.id,
            "trip_number": self.trip_count,
            "start_node": self.current_trip_data["start_node"],
            "goal_node": self.current_trip_data["goal_node"],
            "route_taken": self.current_trip_data["roads_traveled"],
            "trip_time": self.current_trip_data["total_time"],
            "distance": self.current_trip_data["total_distance"],
            "avg_speed": avg_speed,
            "avg_stress": avg_stress
        }
    
    def has_active_trip(self) -> bool: # Check if on trip
        return self.current_vehicle is not None and not self.current_vehicle.has_reached_destination()
    
    def __repr__(self) -> str:
        status = "driving" if self.has_active_trip() else "idle"
        return f"Driver({self.id}, trips={self.trip_count}, status={status})"