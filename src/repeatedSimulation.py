import random
from typing import List, Dict, Optional
from src.network import TrafficNetwork, Node, Road
from src.driver import Driver
from src.simulation import Simulation
from src.dataCollection import DataCollector
from src.visualization import visualize_network_with_traffic
import matplotlib.pyplot as plt


class RepeatedSimulation: #Runs multiple simulations with the same random seed.
    
    def __init__(self, network: TrafficNetwork, seed: int = 42):
        self.network = network
        self.seed = seed
        self.run_count = 0
        self.results = []  # Store results from each run
    
    def run_repeated(self, driver: Driver, num_runs: int, duration_per_run: float,
                     output_dir: str = "repeated_sim", time_step: float = 1.0):
        
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
    
    def _reset_network(self): #Clear all vehicles from roads.
        for road in self.network.roads.values():
            road.vehicles = []
            road.current_speed = road.speed_limit
    
    def _reset_driver_state(self, driver: Driver): # Reset driver state without memory
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
    
    def _print_summary(self):
        print(f"\n{'='*50}")
        print("SUMMARY")
        print(f"{'='*50}")
        
        for result in self.results:
            print(f"\nRun {result['run_number']}:")
            print(f"  Trips completed: {result['trips_completed']}")
            print(f"  Results saved to: {result['output_dir']}")
