from typing import List

class Vehicle:
    
    def __init__(self, vehicle_id: str, route: List):
        self.id = vehicle_id
        self.route = route
        self.route_index = 0  # the road its currently on
        self.position = 0.0   # progress along road
        self.waiting = False
    
    def get_current_road(self):
        if self.route_index < len(self.route):
            return self.route[self.route_index]
        return None
    
    def update_position(self, time_step: float):

        if self.has_reached_destination():
            return
        
        road = self.get_current_road()

        if self.waiting:
            if self.route_index + 1 < len(self.route):
                next_road = self.route[self.route_index + 1]
                if next_road.has_space():
                    road.remove_vehicle(self)
                    self.position = 0.0
                    self.route_index += 1
                    next_road.add_vehicle(self)
                    self.waiting = False
            return

        speed = road.current_speed
        distance_traveled = speed * time_step
        progress = distance_traveled / road.distance
        self.position += progress

        if self.position >= 1.0:
            if self.route_index + 1 < len(self.route):
                next_road = self.route[self.route_index + 1]
                if next_road.has_space():
                    road.remove_vehicle(self)
                    self.position = 0.0
                    self.route_index += 1
                    next_road.add_vehicle(self)
                else:
                    self.position = 1.0
                    self.waiting = True
            else:
                road.remove_vehicle(self)
                self.route_index += 1

    
    def has_reached_destination(self) -> bool:
        return self.route_index >= len(self.route)
    
    def __repr__(self) -> str:
        wait_str = " [WAITING]" if self.waiting else ""
        return f"Vehicle({self.id}, road {self.route_index+1}/{len(self.route)}, pos={self.position:.2f}{wait_str})"