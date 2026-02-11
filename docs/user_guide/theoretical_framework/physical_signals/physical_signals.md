# Layer 1 – Physical Signals

Layer 1 is the **foundation of the conceptual model**.  
It deals with the **raw data captured by physical sensors** and their preprocessing into **virtual sensors**.

!!! note "Key Concepts"
    A **virtual sensor** is a combination of:

    - One or more **physical sensors** (e.g., MoCap, accelerometer, Kinect, respiration band).  
    - **Signal conditioning** (denoising, filtering, synchronization).  
    - **Feature-specific extraction** (e.g., 3D joint trajectories, silhouettes, barycenter).  

## Examples of Physical & Virtual Sensors

| Virtual Sensor / Signal | Description                                     | Implemented      |
|-------------------------|-------------------------------------------------|------------------|
| **Kinematic**           | 3D joint positions, trajectories, barycenter    | :material-close: |
| **Optical**             | Silhouette, RGB-D images, depth maps            | :material-close: |
| **Inertial**            | Accelerometers, gyroscopes                      | :material-close: |
| **Physiological**       | EMG, EEG, ECG, respiration                      | :material-close: |
| **Pressure or Contact** | Ground reaction force, foot weight distribution | :material-close: |
| **Acoustic**            | Breath, utterance, exhalation                   | :material-close: |

