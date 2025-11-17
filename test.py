from network import Node, Road, TrafficNetwork
from vehicle import Vehicle

#########################################Distance calculation test#########################################
node_a = Node("A", 0, 0)
node_b = Node("B", 30, 40)

distance = node_a.euc_distance(node_b)
print(f"Distance: {distance}") #should be 50

if abs(distance - 50.0) < 0.01:
    print("Distance calc works")
else:
    print("Distance calc doesnt work")

print ('///////////////////////////')
############################################################################################################

################################################Congestion test#############################################
node_a = Node("A", 0, 0)
node_b = Node("B", 100, 0)
road = Road("R1", node_a, node_b, speed_limit=60, capacity=10)

print(f"Empty road speed: {road.current_speed}")  #should be 60

road.vehicles = [1, 2, 3, 4, 5, 6, 7, 8]
road.update_speed()

print(f"Congested road speed: {road.current_speed}")  #should be lower

if road.current_speed < 40:
    print("Congestion works")
else:
    print("Congestion doesnt work")

print ('///////////////////////////')
############################################################################################################

##############################################Capacity test#################################################
road = Road("R1", Node("A", 0, 0), Node("B", 100, 0), speed_limit=50, capacity=5) #create road with capacity 5

print(f"Empty road has space: {road.has_space()}")  #should be true

road.vehicles = [1, 2, 3, 4, 5] #fill up road and check

print(f"Full road has space: {road.has_space()}")  #should be false
print(f"Full road is at capacity: {road.is_at_capacity()}")  #should be true

if not road.has_space() and road.is_at_capacity():
    print("Capacity works")

print ('///////////////////////////')
#############################################################################################################

#######################################Vehicle movement test#################################################
road1 = Road("R1", Node("A", 0, 0), Node("B", 100, 0), speed_limit=50, capacity=10)

vehicle = Vehicle("test", route=[road1])
road1.add_vehicle(vehicle)

print(f"Start position: {vehicle.position}")  #should be 0.0

vehicle.update_position(time_step=1.0)

print(f"After 1 second: {vehicle.position}")  #should be 0.5

if abs(vehicle.position - 0.5) < 0.01:
    print("Vehicle movement works")

print ('///////////////////////////')
#############################################################################################################

#######################################Vehicle waiting test##################################################
road1 = Road("R1", Node("A", 0, 0), Node("B", 100, 0), speed_limit=50, capacity=10)
road2 = Road("R2", Node("B", 0, 0), Node("C", 100, 0), speed_limit=50, capacity=1) #capacity of 1

road2.vehicles = ["test1"] #fill next road

vehicle = Vehicle("test2", route=[road1, road2]) #car to enter r2
road1.add_vehicle(vehicle)

vehicle.position = 0.99
vehicle.update_position(time_step=0.1) #car reaches the end of r1

print(f"Vehicle waiting: {vehicle.waiting}")  #should be True
print(f"Vehicle position: {vehicle.position}")  #should be 1.0

if vehicle.waiting and vehicle.position == 1.0:
    print("Vehicle waiting works")

print ('///////////////////////////')
#############################################################################################################