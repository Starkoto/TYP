import random
from typing import List, Dict, Optional
from network import TrafficNetwork, Node, Road
from driver import Driver
from simulation import Simulation
from dataCollection import DataCollector
from visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt


class RepeatedSimulation:
    """
    Runs multiple simulations with the same random seed.
    Driver memory persists between runs, so you can see learning over time.
    """
    
    def __init__(self, network: TrafficNetwork, seed: int = 42):
        self.network = network
        self.seed = seed
        self.run_count = 0
        self.results = []  # Store results from each run
    
    def run_repeated(self, driver: Driver, num_runs: int, duration_per_run: float,
                     output_dir: str = "repeated_sim", time_step: float = 1.0):
        """
        Run simulation multiple times with same seed but persistent driver memory.
        
        Args:
            driver: Driver instance (memory will persist between runs)
            num_runs: How many times to repeat
            duration_per_run: How long each simulation runs
            output_dir: Where to save results
            time_step: Simulation time step
        """
        
        for run_num in range(num_runs):
            print(f"\n{'='*50}")
            print(f"RUN {run_num + 1}/{num_runs}")
            print(f"{'='*50}")
            
            # Reset random seed for reproducibility
            random.seed(self.seed)
            
            # Reset network state (clear vehicles from roads)
            self._reset_network()
            
            # Reset driver trip state but KEEP memory
            self._reset_driver_state(driver)
            
            # Create fresh data collector for this run
            run_output_dir = f"{output_dir}/run_{run_num + 1}"
            collector = DataCollector(output_dir=run_output_dir, log_interval=10)
            
            # Run simulation
            sim = Simulation(self.network, [driver], collector)
            sim.run(duration=duration_per_run, time_step=time_step)
            
            # Save visualization
            fig, ax = visualize_network_with_traffic(self.network, f"Run {run_num + 1} - Final State")
            plt.savefig(f"{run_output_dir}/network_final.png", dpi=150)
            plt.close()
            
            # Store results
            run_result = {
                "run_number": run_num + 1,
                "trips_completed": driver.trip_count,
                "memory_snapshot": dict(driver.memory),  # Copy of memory
                "output_dir": run_output_dir
            }
            self.results.append(run_result)
            
            # Print memory state
            print(f"\nDriver memory after run {run_num + 1}:")
            for road_id, mem in driver.memory.items():
                print(f"  {road_id}: speed={mem['avg_speed']:.1f} km/h, stress={mem['avg_stress']:.3f}, usage={mem['usage']}")
        
        # Summary
        self._print_summary()
    
    def _reset_network(self):
        """Clear all vehicles from roads."""
        for road in self.network.roads.values():
            road.vehicles = []
            road.current_speed = road.speed_limit
    
    def _reset_driver_state(self, driver: Driver):
        """Reset driver's trip state but keep memory."""
        driver.current_vehicle = None
        driver.trip_count = 0
        driver.current_trip_data = {
            "start_node": None,
            "goal_node": None,
            "roads_traveled": [],
            "total_time": 0.0,
            "total_distance": 0.0,
            "speed_observations": [],
            "stress_observations": []
        }
        # Note: driver.memory is NOT reset
    
    def _print_summary(self):
        """Print summary of all runs."""
        print(f"\n{'='*50}")
        print("SUMMARY")
        print(f"{'='*50}")
        
        for result in self.results:
            print(f"\nRun {result['run_number']}:")
            print(f"  Trips completed: {result['trips_completed']}")
            print(f"  Results saved to: {result['output_dir']}")


# Example usage
if __name__ == "__main__":
    # Create network with two paths
    network = TrafficNetwork()
    
    node_a = Node("A", 0, 0)
    node_b = Node("B", 100, 0)
    node_c = Node("C", 200, 0)
    node_d = Node("D", 100, 100)
    
    network.add_node(node_a)
    network.add_node(node_b)
    network.add_node(node_c)
    network.add_node(node_d)
    
    # Two paths from A to C
    road_ab = Road("AB", node_a, node_b, speed_limit_kmh=50, capacity=5)
    road_bc = Road("BC", node_b, node_c, speed_limit_kmh=50, capacity=5)
    road_ba = Road("BA", node_b, node_a, speed_limit_kmh=50, capacity=5)
    road_cb = Road("CB", node_c, node_b, speed_limit_kmh=50, capacity=5)
    road_ad = Road("AD", node_a, node_d, speed_limit_kmh=50, capacity=10)
    road_dc = Road("DC", node_d, node_c, speed_limit_kmh=50, capacity=10)
    road_da = Road("DA", node_d, node_a, speed_limit_kmh=50, capacity=10)
    road_cd = Road("CD", node_c, node_d, speed_limit_kmh=50, capacity=10)
    
    network.add_road(road_ab)
    network.add_road(road_bc)
    network.add_road(road_ba)
    network.add_road(road_cb)
    network.add_road(road_ad)
    network.add_road(road_dc)
    network.add_road(road_da)
    network.add_road(road_cd)
    
    # Create driver with fixed route A <-> C
    driver = Driver(
        driver_id="LearningDriver",
        network=network,
        stress_tolerance=0.5,
        familiarity_weight=0.5,
        learning_rate=0.3,
        fixed_route=["A", "C"]
    )
    
    # Run repeated simulations
    repeated_sim = RepeatedSimulation(network, seed=42)
    repeated_sim.run_repeated(
        driver=driver,
        num_runs=3,
        duration_per_run=100,
        output_dir="learning_test"
    )