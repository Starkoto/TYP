import csv
import os


class DataCollector:
    
    def __init__(self, output_dir: str = "simulation_data", log_interval: int = 60): # Default log_interval: 60 in simulation seconds
        self.output_dir = output_dir
        self.log_interval = log_interval
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.trips_file = os.path.join(output_dir, "trips.csv")
        self.roads_file = os.path.join(output_dir, "road_snapshots.csv")
        
        # Create files with headers
        with open(self.trips_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["driver_id", "trip_number", "start_node", "goal_node", 
                           "route_taken", "total_trip_time", "total_distance", 
                           "average_speed", "average_stress"])
        
        with open(self.roads_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "road_id", "vehicle_count", 
                           "current_speed_kmh", "density", "stress_level"])
    
    def log_trip(self, driver_id, trip_number, start_node, goal_node,
                 route_taken, trip_time, distance, avg_speed, avg_stress):
        
        with open(self.trips_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                driver_id,
                trip_number,
                start_node,
                goal_node,
                "->".join(route_taken),
                round(trip_time, 2),
                round(distance, 2),
                round(avg_speed, 2),
                round(avg_stress, 4)
            ])
    
    def log_roads(self, timestamp, roads):
        
        with open(self.roads_file, 'a', newline='') as f:
            writer = csv.writer(f)
            for road_id, road in roads.items():
                writer.writerow([
                    round(timestamp, 2),
                    road_id,
                    len(road.vehicles),
                    round(road.current_speed * 3.6, 2),  # Convert m/s to km/h
                    round(road.get_density(), 4),
                    round(road.get_stress_level(), 4)
                ])
    
    def should_log_roads(self, timestamp): # Chack whether to make a snapshot
        return timestamp % self.log_interval == 0