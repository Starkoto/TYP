import unittest

from network import Node, Road, TrafficNetwork
from vehicle import Vehicle
from pathfinding import AStar
from driver import Driver

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
        road = Road("R1", node_a, node_b, speed_limit_kmh=60, capacity=10)
        
        # Empty road should be at full speed 
        self.assertAlmostEqual(road.current_speed, 60.0 / 3.6, places=2)
        
        # Add congestion
        road.vehicles = [1, 2, 3, 4, 5, 6, 7, 8]
        road.update_speed()
        
        # Speed should decrease due to congestion
        self.assertLess(road.current_speed, 60.0 / 3.6)
    
    def test_capacity_check(self):
        #Test that capacity checking works.
        node_a = Node("A", 0, 0)
        node_b = Node("B", 100, 0)
        road = Road("R1", node_a, node_b, speed_limit_kmh=50, capacity=5)
        
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
                    speed_limit_kmh=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        
        self.assertEqual(vehicle.id, "Car1")
        self.assertEqual(vehicle.route_index, 0)
        self.assertEqual(vehicle.position, 0.0)
        self.assertFalse(vehicle.waiting)
    
    def test_vehicle_movement(self):
        #Test that vehicles move correctly using m/s physics.
        road = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                    speed_limit_kmh=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        road.add_vehicle(vehicle)
        
        # Move for 1 time unit. Speed 50 km/h = 13.88 m/s. 
        vehicle.update_position(time_step=1.0)
        
        expected_position = (50.0 / 3.6) / 100.0
        self.assertAlmostEqual(vehicle.position, expected_position, places=2)
    
    def test_vehicle_waiting(self):
        #Test that vehicles wait when road is full.
        road1 = Road("R1", Node("A", 0, 0), Node("B", 100, 0), 
                     speed_limit_kmh=50, capacity=10)
        road2 = Road("R2", Node("B", 0, 0), Node("C", 100, 0), 
                     speed_limit_kmh=50, capacity=1)
        
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
                    speed_limit_kmh=50, capacity=10)
        vehicle = Vehicle("Car1", route=[road])
        road.add_vehicle(vehicle)
        
        # A 100m road at 13.88 m/s takes 7.2 seconds to cross. 
        # Loop 10 times to give it plenty of time to finish.
        for _ in range(10):
            vehicle.update_position(time_step=1.0)
        
        self.assertTrue(vehicle.has_reached_destination())

    def test_different_roads_converging(self):
        # Create network: RoadA → RoadC
        #                 RoadB → RoadC
        
        road_a = Road("RoadA", Node("A", 0, 0), Node("C", 100, 0), 
                      speed_limit_kmh=50, capacity=10)
        road_b = Road("RoadB", Node("B", 0, 100), Node("C", 100, 0), 
                      speed_limit_kmh=50, capacity=10)
        road_c = Road("RoadC", Node("C", 100, 0), Node("D", 200, 0), 
                      speed_limit_kmh=50, capacity=5)
        
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

class TestPathfinding(unittest.TestCase):

    def setUp(self):
        """Set up a standard network and pathfinder for the tests."""
        self.network = TrafficNetwork()

        self.node_a = Node("A", 0, 0)
        self.node_b = Node("B", 100, 0)
        self.node_c = Node("C", 200, 0)

        self.network.add_node(self.node_a)
        self.network.add_node(self.node_b)
        self.network.add_node(self.node_c)

        self.road_ab = Road("AB", self.node_a, self.node_b, speed_limit_kmh=50, capacity=10)
        self.road_bc = Road("BC", self.node_b, self.node_c, speed_limit_kmh=50, capacity=10)

        self.network.add_road(self.road_ab)
        self.network.add_road(self.road_bc)

        self.pathfinder = AStar(self.network)

    def test_vehicle_creation_with_astar(self):
        """Test that a vehicle can successfully generate a route using A*."""
        car1 = Vehicle("Car1", start_node="A", goal_node="C", pathfinder=self.pathfinder)
        
        # Verify the route was created and contains the correct roads
        self.assertEqual(len(car1.route), 2)
        self.assertEqual(car1.route[0].id, "AB")
        self.assertEqual(car1.route[1].id, "BC")
        
        # Verify the start and end nodes match the request
        self.assertEqual(car1.route[0].start.id, "A")
        self.assertEqual(car1.route[-1].end.id, "C")

class TestDriverMemory(unittest.TestCase):

    def setUp(self):
        """Set up a standard network with a short path and a long path."""
        self.network = TrafficNetwork()

        self.node_a = Node("A", 0, 0)
        self.node_b = Node("B", 100, 0)    # Middle node for short path
        self.node_c = Node("C", 200, 0)
        self.node_d = Node("D", 100, 100)  # Middle node for long path

        self.network.add_node(self.node_a)
        self.network.add_node(self.node_b)
        self.network.add_node(self.node_c)
        self.network.add_node(self.node_d)

        # Short path: A -> B -> C
        self.road_ab = Road("AB", self.node_a, self.node_b, speed_limit_kmh=50, capacity=10)
        self.road_bc = Road("BC", self.node_b, self.node_c, speed_limit_kmh=50, capacity=10)

        # Long path: A -> D -> C (longer due to geometry)
        self.road_ad = Road("AD", self.node_a, self.node_d, speed_limit_kmh=50, capacity=10)
        self.road_dc = Road("DC", self.node_d, self.node_c, speed_limit_kmh=50, capacity=10)

        self.network.add_road(self.road_ab)
        self.network.add_road(self.road_bc)
        self.network.add_road(self.road_ad)
        self.network.add_road(self.road_dc)

        # Initialize the driver
        self.driver = Driver(
            driver_id="TestDriver",
            network=self.network,
            stress_tolerance=0.5,
            familiarity_weight=0.5,
            learning_rate=0.3
        )

    def test_empty_memory_chooses_shortest_path(self):
        """Test that with no memory, the driver defaults to the geometrically shorter path."""
        route = self.driver.pathfinder.find_path("A", "C")
        path_ids = [r.id for r in route]
        
        # Should choose the shorter, direct path
        self.assertEqual(path_ids, ["AB", "BC"])

    def test_bad_memory_changes_route(self):
        """Test that negative experiences in memory cause the driver to pick an alternative route."""
        # Simulate bad experience on the short path
        self.driver.memory["AB"] = {
            "usage": 5,
            "avg_speed": 10.0,  # Very slow (remembered as 10 km/h instead of 50)
            "avg_stress": 0.8   # Very stressful
        }
        self.driver.memory["BC"] = {
            "usage": 5,
            "avg_speed": 10.0,
            "avg_stress": 0.8
        }

        route = self.driver.pathfinder.find_path("A", "C")
        path_ids = [r.id for r in route]
        
        # Should avoid the short path and take the longer path due to bad memory
        self.assertEqual(path_ids, ["AD", "DC"])


if __name__ == '__main__':
    unittest.main()