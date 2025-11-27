import numpy as np

class KineticEnergy:
   

    def __init__(self, weights=1.0, labels=None):
        """
        weights: scalar mass or array of masses (one per joint)
        labels: list of joint labels (optional)
        """

        # Store weight(s)
        self.setWeight(weights)

        # Store labels (optional, validated later)
        self.labels = labels

    def setWeight(self, w):
        """Allow setting scalar weight or per-joint weights."""
        if isinstance(w, (list, tuple, np.ndarray)):
            w = np.asarray(w, dtype=float)
            if np.any(w < 0):
                raise ValueError("Mass values cannot be negative.")
            self.weights = w
        else:
            w = float(w)
            if w < 0:
                raise ValueError("Mass cannot be negative.")
            self.weights = w

    def __call__(self, velocity_vectors):
        """
        velocity_vectors:
            - single vector (3,)
            - array of shape (N,3) for multiple joints
        """

        # Convert input to array
        v = np.asarray(velocity_vectors, dtype=float)

        # Normalize to shape (N,3)
        if v.ndim == 1:
            v = v.reshape(1, -1)

        N = v.shape[0]

        # Validate or expand weights
        if np.isscalar(self.weights):
            w = np.full(N, self.weights)
        else:
            w = np.asarray(self.weights)
            if w.size != N:
                raise ValueError(f"Weight array must match number of joints ({N}).")

        # Validate labels
        if self.labels is not None:
            if len(self.labels) != N:
                raise ValueError(f"Labels must match number of joints ({N}).")

        # Compute squared velocity components
        v_squared = v ** 2
        
        # Component-wise kinetic energy: 1/2 * m_i * v^2
        Ek_components = 0.5 * w[:, None] * v_squared

        # Total KE per joint
        Ek_joint = Ek_components.sum(axis=1)

        # Total KE across all joints
        Ek_total = Ek_joint.sum()

        # Total per-axis component energy
        Ek_components_total = Ek_components.sum(axis=0)

        # Build dictionary optionally using labels
        if self.labels is None:
            joint_energy_dict = {
                i: {
                    "total": Ek_joint[i],
                    "components": Ek_components[i]
                } 
                for i in range(N)
            }
        else:
            joint_energy_dict = {
                self.labels[i]: {
                    "total": Ek_joint[i],
                    "components": Ek_components[i]
                }
                for i in range(N)
            }

        return {
            "total_energy": Ek_total,
            "component_energy": Ek_components_total,   # [Ex, Ey, Ez]
            "joints": joint_energy_dict                # dict indexed by labels or id
        }
