# Theoretical Framework

PyEyesWeb inherits from the rich tradition of computational movement analysis initiated by the [EyesWeb](https://casapaganini.unige.it/eyesweb_bp) project [^1][^2][^3]
and grounds on the multi-layered computational framework of qualities in movement developed in the [DANCE](http://dance.dibris.unige.it/) project [^4].

# Conceptual Model

!!! warning
    This is the result of an open filed of research.
    As such, certain aspects of the model may be provisional or subject to refinement.
    Some concepts are open to interpretation, and current limitations are actively being addressed in the ongoing work. 

![conceptual_model.png](../../assets/conceptual_model.png)

The framework describes how raw sensor data can be progressively transformed into meaningful descriptions of expressive movement qualities and is organized into four layers.  
The layers represent a conceptual model and **not a strict processing pipeline**.  

## Layers Overview

!!! example "Attention!"
    The concept of **timescale** is crucial in this framework, and each layer operates at different temporal scales.  
    As an example, a key distinction from Layers 2 and 3 is moving from instantaneous or short-window features (~0.5s)
    to longer windows (0.5-3s) or movement units (e.g., a specific sport gesture, a choreographic phase).  
    One same feature **can occur at different layers** and yield **different interpretations** depending on the timescale of analysis.

<div class="grid cards" markdown>

-   **Layer 1 – Physical Signals**  

     Raw data captured by **virtual sensors**, i.e., physical devices (motion capture, accelerometers, video, RGB-D cameras, physiological sensors, etc.) enriched with preprocessing (denoising, filtering, extraction of trajectories, silhouettes, respiration, etc.).  

    _Foundation for all higher layers._  
    
    [→ Learn more](physical_signals/index.md)

-   **Layer 2 – Low-Level Features**  

    Instantaneous or short-window (0.5s) descriptors computed from physical signals.  
    Includes: velocity, acceleration, kinetic energy, Quantity of Motion (QoM), postural contraction, balance, smoothness, etc.  
    
    _Represented as time-series._  

    [→ Learn more](low_level/index.md)

-   **Layer 3 – Mid-Level Features**  

    Operates on **movement units or longer windows**, producing structural descriptors in multidimensional spaces.  
    Examples: contraction/expansion, symmetry, directness, lightness, suddenness, fluidity, repetitiveness, coordination, cohesion.  
    
    _Introduce amodal descriptors across modalities._

    [→ Learn more](mid_level/index.md)

-   **Layer 4 – Expressive Qualities**  

    Focuses on **what an observer perceives** from movement: emotional expression, social signals, saliency, attraction/repulsion, groove, hesitation, predictability.  
    Involves **memory and context**, influencing how movement is interpreted (expectancy, contrast, sensitivity).  
    
    _Requires context and ML mappings._

    [→ Learn more](high_level/index.md)


</div>

<div class="grid cards" markdown style="justify-content: center;">

-   **Analysis Primitives**  
    Core computational tools applied across all layers.  
    Includes: statistical moments, entropy, shape descriptors (peaks, slopes), synchronization, time-frequency transforms, predictive and physical models (e.g., mass–spring).  
    
    _Provide the building blocks for extracting meaningful features._  
    
    [→ Learn more](analysis_primitives/index.md)

</div>

## References

[^1]: Camurri, A., Mazzarino, B., & Volpe, G. (2003, April). Analysis of expressive gesture: The eyesweb expressive gesture processing library. In International gesture workshop (pp. 460-467). Berlin, Heidelberg: Springer Berlin Heidelberg.
[^2]: Camurri, A., Coletta, P., Massari, A., Mazzarino, B., Peri, M., Ricchetti, M., ... & Volpe, G. (2004, March). Toward real-time multimodal processing: EyesWeb 4.0. In Proc. AISB (pp. 22-26).
[^3]: Volpe, G., Alborno, P., Camurri, A., Coletta, P., Ghisio, S., Mancini, M., ... & Sagoleo, R. (2016). Designing multimodal interactive systems using EyesWeb XMI. In CEUR Workshop Proceedings (pp. 49-56). CEUR-WS.
[^4]: Camurri, A., Volpe, G., Piana, S., Mancini, M., Niewiadomski, R., Ferrari, N., & Canepa, C. (2016, July). The dancer in the eye: towards a multi-layered computational framework of qualities in movement. In Proceedings of the 3rd International Symposium on Movement and Computing (pp. 1-7).

