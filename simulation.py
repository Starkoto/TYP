import random
from typing import List, Optional
from network import TrafficNetwork
from driver import Driver
from dataCollection import DataCollector

class Simulation:

    def __init__(self, network: TrafficNetwork, drivers: List[Driver], data_collector: DataCollector):

        self.network = network
        self.drivers = drivers
        self.data_collector = data_collector
        self.time = 0.0

        self.node_ids = list(network.nodes.keys())

    def run(self, duration: float, time_step: float = 1.0):

        while self.time < duration:

            for driver in self.drivers:

                # If the driver doesnt have an active trip start one
                if not driver.has_active_trip():
                    start, goal = self.get_destination(driver)
                    if start and goal:
                        driver.start_trip(start, goal, self.network)

                trip_finished = driver.update(time_step) # driver.update return true if trip is finished

                if trip_finished:
                    summary = driver.get_trip_summary()
                    self.data_collector.log_trip(
                        driver_id=summary["driver_id"],
                        trip_number=summary["trip_number"],
                        start_node=summary["start_node"],
                        goal_node=summary["goal_node"],
                        route_taken=summary["route_taken"],
                        trip_time=summary["trip_time"],
                        distance=summary["distance"],
                        avg_speed=summary["avg_speed"],
                        avg_stress=summary["avg_stress"]
                    )

            if self.data_collector.should_log_reads(self.time):
                self.data_collector.log_reads(self.time, self.network.reads)

            self.time += time_step

        print(f"Simulation complete. Time: {self.time}")
        print(f"Total trips logged: check {self.data_collector.trips_file}")
                