from typing import List


class Vehicle:
    
    def __init__(self, vehicle_id: str, route: List):
        self.id = vehicle_id
        self.route = route
        self.route_index = 0  # the road its currently on
        self.position = 0.0   # progress along road
    
    def get_current_road(self):
        if self.route_index < len(self.route):
            return self.route[self.route_index]
        return None
    
    def update_position(self, time_step: float):
        # TODO: Implement movement logic
        pass
    
    def has_reached_destination(self) -> bool:
        return self.route_index >= len(self.route)
    
    def __repr__(self) -> str:
        return f"Vehicle({self.id}, road {self.route_index+1}/{len(self.route)}, pos={self.position:.2f})"