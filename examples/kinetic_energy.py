import numpy as np
import sys
import os
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pyeyesweb.low_level.kinetic_energy import KineticEnergy
labels = ["Head", "Neck", "Spine", "Hip"]

vel = np.array([
    [0.2, 0.0, 0.1],
    [0.1, 0.1, 0.3],
    [0.4, 0.2, 0.2],
    [0.0, 0.3, 0.1]
])

masses = [5.0, 3.0, 8.0, 10.0]

ke = KineticEnergy(weights=masses, labels=labels)

result = ke(vel)

print(result["joints"]["Head"])
print(result["joints"]["Hip"])
print("Total:", result["total_energy"])
