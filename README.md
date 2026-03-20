# Adaptive Pathfinding with Learning Agents in Traffic Networks

A simulation system where autonomous driver agents learn from experience and use personalised personality parameters to make route choices in a traffic network. The system extends the A* pathfinding algorithm with a memory-based cost function that incorporates stress tolerance, familiarity preference, and learning rate.

## Requirements

- Python 3.13+
- NetworkX (for visualisation)
- Matplotlib (for rendering)

Install dependencies:

```
pip install networkx matplotlib
```

## Project Structure

```
├── src/
│   ├── network.py               # Node, Road, and TrafficNetwork classes
│   ├── pathfinding.py            # A* and AdaptivePathfinder
│   ├── driver.py                 # Driver agent with memory and personality
│   ├── vehicle.py                # Vehicle movement and waiting logic
│   ├── simulation.py             # Main simulation loop
│   ├── repeatedSimulation.py     # Repeated simulation with persistent memory
│   ├── dataCollection.py         # CSV logging for trips and road snapshots
│   ├── visualization.py          # Network visualisation with NetworkX
│   └── test.py                   # Unit tests
│
├── eval/
│   ├── eval_Astar.py                   # Baseline A* vs adaptive comparison
│   ├── eval_familiarity.py             # Familiarity weight parameter test
│   ├── eval_lr.py                      # Learning rate parameter test
│   ├── eval_stress.py                  # Stress tolerance parameter test
│   ├── eval_roadClosure.py             # Road closure response test
│   ├── eval_newRoad.py                 # New road response test (dummy traffic)
│   ├── eval_newRoad_realtraffic.py     # New road response test (real traffic)
│   ├── eval_braess.py                  # Braess's Paradox test
│   ├── eval_population.py             # Population diversity test
│   └── eval_simulation.py             # Full-scale simulation test
│
├── results/                 # Output directory for evaluation results
├── .gitignore
└── README.md
```

## Running

### Unit Tests

```
python -m unittest src.test
```

### Evaluation Scripts

All evaluation scripts are in the `eval/` directory. Each script builds its own network, runs the experiment, and saves results (CSV data and network visualisations) to a subdirectory inside `results/`.

```
python eval/eval_Astar.py
python eval/eval_familiarity.py
python eval/eval_lr.py
python eval/eval_stress.py
python eval/eval_roadClosure.py
python eval/eval_newRoad.py
python eval/eval_newRoad_realtraffic.py
python eval/eval_braess.py
python eval/eval_population.py
python eval/eval_simulation.py
```

Each script outputs:
- **trips.csv** — per-trip data (route taken, trip time, distance, average speed, average stress)
- **road_snapshots.csv** — periodic snapshots of road state (vehicle count, speed, density, stress)
- **network_*.png** — visualisations of the network at various stages of the experiment

### Custom Networks

Networks are defined in JSON files with the following format:

```json
{
  "nodes": [
    {"id": "A", "x": 0, "y": 0},
    {"id": "B", "x": 100, "y": 0}
  ],
  "roads": [
    {"id": "AB", "start": "A", "end": "B", "speed_limit": 50, "capacity": 10, "base_stress": 0.0}
  ]
}
```

Load a network with:

```python
from src.network import TrafficNetwork
network = TrafficNetwork.from_json("networks/your_network.json")
```

## How It Works

### Adaptive Cost Function

The adaptive pathfinder replaces A*'s static edge cost with a personalised cost:

```
c(r) = (distance / remembered_speed) × (1 + stress_penalty + familiarity_penalty)
```

Where:
- **Stress penalty** = remembered_stress × stress_tolerance (ω_s)
- **Familiarity penalty** = familiarity_weight (ω_f) / (usage_count + 1)

### Driver Personality Parameters

Each driver has three parameters (range 0 to 1):
- **Stress tolerance (ω_s)** — how much stress affects route choice
- **Familiarity weight (ω_f)** — preference for known roads over unknown ones
- **Learning rate (α)** — how quickly memory adjusts to new experiences

### Memory Updates

After each trip, the driver's per-road memory is updated:

```
remembered_speed ← remembered_speed + α × (observed_speed − remembered_speed)
remembered_stress ← remembered_stress + α × (observed_stress − remembered_stress)
```

Roads with no prior experience default to the speed limit and zero stress.