# Layer 1 – Physical Signals

Layer 1 is the **foundation of the conceptual model**.  
It deals with the **raw data captured by physical sensors** and their preprocessing into **virtual sensors** — representations ready for higher-level analysis.

!!! note "Key Concepts"
    A **virtual sensor** is a combination of:

    - One or more **physical sensors** (e.g., MoCap, accelerometer, Kinect, respiration band).  
    - **Signal conditioning** (denoising, filtering, synchronization).  
    - **Feature-specific extraction** (e.g., 3D joint trajectories, silhouettes, barycenter).  

## Examples of Physical & Virtual Sensors

| Virtual Sensor / Signal          | Description                                                                                                    | Implemented      |
|----------------------------------|----------------------------------------------------------------------------------------------------------------|------------------|
| **Trajectories**                 | Positional data (2D/3D positions of joints and barycenter) from MoCap, video, or RGB-D sensors (e.g., Kinect). | :material-close: |
| **Bounding Space / Convex Hull** | Minimum polygon (2D) or volume (3D) surrounding a point cloud (MoCap) or a body silhouette.                    | :material-close: |
| **Accelerations**                | Measures from accelerometers and gyroscopes.                                                                   | :material-close: |
| **Physiological Sensors**        | EMG, EEG, ECG, and related physiological data.                                                                 | :material-close: |
| **Respiration**                  | Signals from dedicated respiration sensors or microphones.                                                     | :material-close: |
| **Nonverbal Vocal Utterances**   | Short vocalizations linked to movement (e.g., *kiai* in Karate, dance utterances).                             | :material-close: |
| **Floor Feet Pressure**          | Weight distribution across feet, measured with a sensitive floor.                                              | :material-close: |
