import unittest

from network import Node, Road, TrafficNetwork
from vehicle import Vehicle


class TestNetwork(unittest.TestCase):
    
    def test_node_distance(self):
        #Test that node distance calculation works.
        node_a = Node("A", 0, 0)
        node_b = Node("B", 30, 40)
        distance = node_a.euc_distance(node_b)
        
        self.assertAlmostEqual(distance, 50.0, places=2)
    
    def test_road_congestion(self):
        #Test that congestion slows down roads.
        node_a = Node("A", 0, 0)
        node_b = Node("B", 100, 0)
        road = Road("R1", node_a, node_b, speed_limit=60, capacity=10)
        
        # Empty road should be at full speed
        self.assertEqual(road.current_speed, 60.0)
        
        # Add congestion
        road.vehicles = [1, 2, 3, 4, 5, 6, 7, 8]
        road.update_speed()
        
        # Speed should decrease
        self.assertAlmostEqual(road.current_speed, 34.8, places=1)
        self.assertLess(road.current_speed, 60.0)
    
    def test_capacity_check(self):
        #Test that capacity checking works.
        node_a = Node("A", 0, 0)
        node_b = Node("B", 100, 0)
        road = Road("R1", node_a, node_b, speed_limit=50, capacity=5)
        
        # Empty road has space
        self.assertTrue(road.has_space())
        self.assertFalse(road.is_at_capacity())
        
        # Fill it up
        road.vehicles = [1, 2, 3, 4, 5]
        
        # Full road has no space
        self.assertFalse(road.has_space())
        self.assertTrue(road.is_at_capacity())


class TestVehicle(unittest.TestCase):

    def test_vehicle_creation(self):
        #Test that vehicles can be created.
        road = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                    speed_limit=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        
        self.assertEqual(vehicle.id, "Car1")
        self.assertEqual(vehicle.route_index, 0)
        self.assertEqual(vehicle.position, 0.0)
        self.assertFalse(vehicle.waiting)
    
    def test_vehicle_movement(self):
        #Test that vehicles move correctly.
        road = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                    speed_limit=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        road.add_vehicle(vehicle)
        
        # Move for 1 time unit (50 units at speed 50 = 50% of 100)
        vehicle.update_position(time_step=1.0)
        
        self.assertAlmostEqual(vehicle.position, 0.5, places=2)
    
    def test_vehicle_waiting(self):
        #Test that vehicles wait when road is full.
        road1 = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                     speed_limit=50, capacity=10)
        road2 = Road("R2", Node("B", 0, 0), Node("C", 100, 0), 
                     speed_limit=50, capacity=1)
        
        # Block road2
        road2.vehicles = ["blocking_car"]
        
        # Create vehicle
        vehicle = Vehicle("Car1", route=[road1, road2])
        road1.add_vehicle(vehicle)
        
        # Move to end of road1
        vehicle.position = 0.99
        vehicle.update_position(time_step=0.1)
        
        # Should be waiting
        self.assertTrue(vehicle.waiting)
        self.assertEqual(vehicle.position, 1.0)
        self.assertEqual(vehicle.route_index, 0)  # Still on first road
    
    def test_vehicle_completes_journey(self):
        #Test that vehicle can complete a full journey.
        road = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                    speed_limit=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        road.add_vehicle(vehicle)
        
        # Move enough to complete journey
        for _ in range(5):
            vehicle.update_position(time_step=1.0)
        
        self.assertTrue(vehicle.has_reached_destination())

    def test_different_roads_converging(self):
        # Create network: RoadA → RoadC
        #                 RoadB → RoadC
        #                 (both feeding into RoadC)
        
        road_a = Road("RoadA", Node("A", 0, 0), Node("C", 100, 0), 
                      speed_limit=50, capacity=10)
        road_b = Road("RoadB", Node("B", 0, 100), Node("C", 100, 0), 
                      speed_limit=50, capacity=10)
        road_c = Road("RoadC", Node("C", 100, 0), Node("D", 200, 0), 
                      speed_limit=50, capacity=5)
        
        # Fill road_c to 4/5 (one space left)
        road_c.vehicles = ["blocker1", "blocker2", "blocker3", "blocker4"]
        self.assertEqual(len(road_c.vehicles), 4)
        self.assertTrue(road_c.has_space())
        
        # Create Car1 from RoadA
        car1 = Vehicle("Car1", route=[road_a, road_c])
        road_a.add_vehicle(car1)
        car1.position = 1.0  # At end of RoadA
        
        # Create Car2 from RoadB
        car2 = Vehicle("Car2", route=[road_b, road_c])
        road_b.add_vehicle(car2)
        car2.position = 1.0  # At end of RoadB
        
        # Create Car3 also from RoadA
        car3 = Vehicle("Car3", route=[road_a, road_c])
        road_a.add_vehicle(car3)
        car3.position = 1.0
        
        # List order determines priority!
        vehicles = [car1, car2, car3]
        
        # Simulate updates
        for vehicle in vehicles:
            vehicle.update_position(time_step=0.1)
        
        # Only 1 vehicle should have entered (the first in the list)
        self.assertEqual(len(road_c.vehicles), 5, 
                        "RoadC should be at capacity with 5 vehicles")
        self.assertTrue(road_c.is_at_capacity())
        
        # Car1 should have entered (first in list)
        self.assertEqual(car1.route_index, 1, 
                        "Car1 (first in list) should have entered RoadC")
        self.assertFalse(car1.waiting)
        
        # Car2 and Car3 should be waiting (on their original roads)
        self.assertEqual(car2.route_index, 0, 
                        "Car2 should still be on RoadB")
        self.assertTrue(car2.waiting, "Car2 should be waiting")
        
        self.assertEqual(car3.route_index, 0, 
                        "Car3 should still be on RoadA")
        self.assertTrue(car3.waiting, "Car3 should be waiting")
        
        # Verify they're on different source roads
        self.assertIn(car2, road_b.vehicles, "Car2 should still be on RoadB")
        self.assertIn(car3, road_a.vehicles, "Car3 should still be on RoadA")


if __name__ == '__main__':
    unittest.main()