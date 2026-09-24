"""Mathematical utility functions for signal analysis.

This module provides mathematical functions used throughout the PyEyesWeb
library for signal processing, phase analysis, and movement metrics.
"""

import numpy as np
from scipy.fft import fft, fftfreq
from pyeyesweb.utils.validators import validate_numeric

def compute_phase_locking_value(phase1, phase2):
    """Compute the Phase Locking Value (PLV) from two phase arrays.

    PLV measures the inter-trial variability of the phase difference between
    two signals. A value of 1 indicates perfect phase locking, while 0
    indicates no phase relationship.

    Parameters
    ----------
    phase1 : ndarray
        Phase values of first signal in radians.
    phase2 : ndarray
        Phase values of second signal in radians.

    Returns
    -------
    float
        Phase Locking Value between 0 and 1.

    References
    ----------
    Lachaux et al. (1999). Measuring phase synchrony in brain signals.
    """
    phase_diff = phase1 - phase2
    phase_diff_exp = np.exp(1j * phase_diff)
    plv = np.abs(np.mean(phase_diff_exp))
    return plv


def center_signals(sig):
    """Remove the mean from each signal to center the data.

    Centers signals by subtracting the mean, removing DC bias.

    Parameters
    ----------
    sig : ndarray
        Signal array of shape (n_samples, n_channels).

    Returns
    -------
    ndarray
        Centered signal with same shape as input.
    """
    return sig - np.mean(sig, axis=0, keepdims=True)

""""
def compute_sparc(
    signal, 
    rate_hz=50.0, 
    amplitude_threshold=0.05, 
    min_fc=2.0, 
    max_fc=20.0
):
    Compute SPARC (Spectral Arc Length) from a signal.

    SPARC is a dimensionless smoothness metric that quantifies movement
    smoothness independent of movement amplitude and duration. More negative
    values indicate smoother movement.

    This implementation is based on the original algorithm by Balasubramanian et al. (2015).
    SPARC values are typically negative, with values closer to 0 indicating less smooth
    (more complex) movements. For healthy reaching movements, values around -1.4 to -1.6
    are common. Pathological or very unsmooth movements may have values ranging from
    -3 to -10 or lower, depending on the degree of movement fragmentation.

    Parameters
    ----------
    signal : ndarray
        1D movement speed profile.
    rate_hz : float
        Sampling rate in Hz.
    amplitude_threshold : float, optional
        Amplitude threshold for determining the cut-off frequency fc (default: 0.05).
        Increase this value for noisier signals.
    min_fc : float, optional
        Minimum cut-off frequency in Hz (default: 2.0).
    max_fc : float, optional
        Maximum cut-off frequency in Hz (default: 20.0).

    Returns
    -------
    float
        SPARC value (negative, more negative = smoother).
        Returns NaN if signal has less than 2 samples.

    References
    ----------
    Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015).
    On the analysis of movement smoothness. Journal of NeuroEngineering and Rehabilitation,
    12(1), 1-11.
    


    # Validate sampling rate and convert signal to array
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)
    signal = np.asarray(signal)
    
    # Check signal validity
    if len(signal) < 2 or np.allclose(signal, signal[0]):
        return np.nan

    # 1. FFT and magnitude spectrum calculation
    n = len(signal)
    # Zero-padding to 1024 or next power of 2 for improved spectral resolution
    n_fft = max(1024, int(2**np.ceil(np.log2(n))))
    
    yf = np.abs(fft(signal, n=n_fft))[:n_fft // 2]
    xf = fftfreq(n_fft, 1.0 / rate_hz)[:n_fft // 2]

    # 2. Amplitude normalization relative to maximum (Scale invariance)
    max_yf = np.max(yf)
    if max_yf > 0:
        yf /= max_yf
    else:
        return np.nan

    # 3. Adaptive determination of fc (Cut-off frequency)
    # Find the last index where the amplitude is above the chosen threshold
    indices_above_thresh = np.where(yf >= amplitude_threshold)[0]
    
    if len(indices_above_thresh) > 0:
        fc_estimated = xf[indices_above_thresh[-1]]
    else:
        fc_estimated = min_fc

    # Apply min/max constraints to the cut-off frequency
    fc = max(min_fc, min(max_fc, fc_estimated))

    # 4. Select data within the [0, fc] range
    sel_idx = np.where(xf <= fc)[0]
    xf_sel = xf[sel_idx]
    yf_sel = yf[sel_idx]

    # 5. Normalized arc length calculation
    # The frequency axis is rescaled between 0 and 1 (f / fc)
    if len(xf_sel) < 2:
        return np.nan
        
    d_xf_norm = np.diff(xf_sel) / fc
    d_yf = np.diff(yf_sel)
    
    # Geometric arc length in the normalized spectrum
    arc_length = np.sum(np.sqrt(d_xf_norm**2 + d_yf**2))
    
    # The result is negative by convention (values closer to 0 = smoother)
    return -arc_length
    """


def compute_sparc(
    signal, 
    rate_hz=50.0, 
    amplitude_threshold=0.05, 
    min_fc=2.0, 
    max_fc=20.0
):
    """
    Compute SPARC (Spectral Arc Length) from a signal.

    SPARC is a dimensionless smoothness metric that quantifies movement
    smoothness independent of movement amplitude and duration. More negative
    values indicate smoother movement.

    This implementation is based on the original algorithm by Balasubramanian et al. (2015).
    SPARC values are typically negative, with values closer to 0 indicating less smooth
    (more complex) movements. For healthy reaching movements, values around -1.4 to -1.6
    are common. Pathological or very unsmooth movements may have values ranging from
    -3 to -10 or lower, depending on the degree of movement fragmentation.

    Parameters
    ----------
    signal : ndarray
        1D movement speed profile.
    rate_hz : float
        Sampling rate in Hz.
    amplitude_threshold : float, optional
        Amplitude threshold for determining the cut-off frequency fc (default: 0.05).
        Increase this value for noisier signals.
    min_fc : float, optional
        Minimum cut-off frequency in Hz (default: 2.0).
    max_fc : float, optional
        Maximum cut-off frequency in Hz (default: 20.0).

    Returns
    -------
    float
        SPARC value (negative, more negative = smoother).
        Returns NaN if signal has less than 2 samples.

    References
    ----------
    Balasubramanian, S., Melendez-Calderon, A., Roby-Brami, A., & Burdet, E. (2015).
    On the analysis of movement smoothness. Journal of NeuroEngineering and Rehabilitation,
    12(1), 1-11.
    """
    
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)
    signal = np.asarray(signal)
    
    if len(signal) < 2 or np.allclose(signal, signal[0]):
        return np.nan

    n = len(signal)
    # Zero-padding
    n_fft = max(1024, int(2**np.ceil(np.log2(n))))
    
    yf = np.abs(fft(signal, n=n_fft))[:n_fft // 2]
    xf = fftfreq(n_fft, 1.0 / rate_hz)[:n_fft // 2]

    # Normalizzazione dello spettro d'ampiezza
    max_yf = np.max(yf)
    if max_yf > 0:
        yf /= max_yf
    else:
        return np.nan

    # Calcolo fc adattativa
    indices_above_thresh = np.where(yf >= amplitude_threshold)[0]
    if len(indices_above_thresh) > 0:
        fc_estimated = xf[indices_above_thresh[-1]]
    else:
        fc_estimated = min_fc

    fc = max(min_fc, min(max_fc, fc_estimated))

    # Selezione nell'intervallo [0, fc]
    sel_idx = np.where(xf <= fc)[0]
    xf_sel = xf[sel_idx]
    yf_sel = yf[sel_idx]

    if len(xf_sel) < 2:
        return np.nan

    # -------------------------------------------------------------
    # CORREZIONE FORMULA ARTICOLO BALASUBRAMANIAN ET AL. (2015)
    # -------------------------------------------------------------
    # Asse frequenze normalizzato (da 0 a 1)
    d_xf_norm = np.diff(xf_sel) / fc
    d_yf = np.diff(yf_sel)
    
    # Derivata dY / dF_norm
    d_yf_d_xf = d_yf / d_xf_norm
    
    # Integrale discreto: sum( sqrt(1 + (dY/dF_norm)^2) * dF_norm )
    arc_length = np.sum(np.sqrt(1.0 + d_yf_d_xf**2) * d_xf_norm)
    
    return -arc_length


def compute_jerk_rms(signal, rate_hz=50.0, signal_type='velocity'):
    """Compute RMS of jerk (rate of change of acceleration) from a signal.

    Jerk is the third derivative of position or the first derivative of acceleration. Lower RMS jerk values indicate smoother movement.

    Parameters
    ----------
    signal : ndarray
        1D movement signal.
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).
    signal_type : str, optional
        Type of input signal: 'position' or 'velocity' (default: 'velocity').
        - 'position': Computes third derivative to get jerk
        - 'velocity': Computes second derivative to get jerk

    Returns
    -------
    float
        Root mean square of jerk.
        Returns NaN if signal has insufficient samples for the required derivatives.

    Notes
    -----
    Uses numpy.gradient for smooth derivative approximation with central differences
    where possible, providing better accuracy than forward differences.
    """
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)

    # Define derivative orders needed for each signal type
    derivative_orders = {
        'velocity': 2,  # if signal type is velocity we can get velocity -> acceleration -> jerk
        'position': 3   # if signal type is position we can get position -> velocity -> acceleration -> jerk
    }

    if signal_type not in derivative_orders:
        raise ValueError(f"signal_type must be 'position' or 'velocity', got '{signal_type}'")

    n_derivatives = derivative_orders[signal_type]
    min_samples = n_derivatives + 1

    if len(signal) < min_samples:
        return np.nan

    # Apply derivatives using numpy.gradient for better accuracy
    result = np.asarray(signal)
    for _ in range(n_derivatives):
        result = np.gradient(result, 1.0/rate_hz)

    return np.sqrt(np.mean(result ** 2))

def compute_ldlj(signal: np.ndarray, rate_hz: float, signal_type: str = 'velocity') -> float:
    """Calculates the Log Dimensionless Jerk (LDLJ) based on Balasubramanian (2012) 
    and Melendez-Calderon (2021).
    
    Parameters
    ----------
    signal : np.ndarray
        The 1D input signal (velocity profile or acceleration profile).
    rate_hz : float
        Sampling rate of the signal in Hz.
    signal_type : {'velocity', 'acceleration'}, optional
        The type of input signal provided. Defaults to 'velocity'.
        
    Returns
    -------
    float
        The negative log dimensionless jerk value.
    """
    if signal_type not in ['velocity', 'acceleration']:
        raise ValueError("signal_type must be either 'velocity' or 'acceleration'")
        
    dt = 1.0 / rate_hz
    n_samples = len(signal)
    duration = n_samples * dt

    # 1. Compute Jerk
    if signal_type == 'velocity':
        acceleration = np.diff(signal) / dt
        jerk = np.diff(acceleration) / dt
    else:  # acceleration
        jerk = np.diff(signal) / dt

    # 2. Compute Jerk Integral: integral(jerk^2 dt)
    # np.mean(jerk**2) gives (1/duration) * integral(jerk^2 dt)
    ms_jerk = np.mean(jerk ** 2)
    jerk_integral = ms_jerk * duration

    # Avoid math errors for perfectly flat signals
    if duration < 1e-8 or jerk_integral < 1e-12:
        return 0.0

    # 3. Compute Dimensionless Jerk based on signal type
    if signal_type == 'velocity':
        # LDLJ-V: Balasubramanian et al. (2012)
        v_max = np.max(np.abs(signal))
        if v_max < 1e-8:
            return 0.0
        
        # Formula: (duration^3 / v_max^2) * integral(jerk^2)
        dimensionless_jerk = jerk_integral * (duration ** 3) / (v_max ** 2)

    else:
        # LDLJ-A: Melendez-Calderon et al. (2021)
        # Use mean-subtracted acceleration to avoid gravity drift offsets
        mean_subtracted_acc = signal - np.mean(signal)
        a_max = np.max(np.abs(mean_subtracted_acc))
        if a_max < 1e-8:
            return 0.0
            
        # Formula: (duration / a_max^2) * integral(jerk^2)
        dimensionless_jerk = jerk_integral * duration / (a_max ** 2)

    # 4. Compute Log Dimensionless Jerk (LDLJ)
    if dimensionless_jerk < 1e-12:
        return 0.0
        
    return -np.log(dimensionless_jerk)


import numpy as np
from scipy.signal import find_peaks

def compute_sample_entropy(signal: np.ndarray, m: int = 2, r_factor: float = 0.2) -> float:
    """Calcola la Sample Entropy (SampEn) di una serie temporale 1D.
    
    Parameters
    ----------
    signal : np.ndarray
        Profilo di velocità/accelerazione.
    m : int
        Lunghezza delle sequenze da confrontare (di solito 2).
    r_factor : float
        Tolleranza espressa come frazione della deviazione standard del segnale (default 0.2).
    """
    signal = np.asarray(signal)
    N = len(signal)
    if N < 15:
        return np.nan

    std_sig = np.std(signal)
    if std_sig < 1e-8:
        return 0.0  # Segnale costante = massima regolarità

    r = r_factor * std_sig

    def _phi(m_len):
        x = np.array([signal[i:i + m_len] for i in range(N - m_len + 1)])
        # Matrice delle distanze Chebyshev (Cechov/infinity norm)
        dists = np.max(np.abs(x[:, None, :] - x[None, :, :]), axis=2)
        # Conta le coppie con distanza < r (escludendo l'auto-confronto)
        count = np.sum(dists < r) - (N - m_len + 1)
        return count

    count_m = _phi(m)
    count_m1 = _phi(m + 1)

    if count_m == 0 or count_m1 == 0:
        return np.nan

    return -np.log(count_m1 / count_m)


def compute_harmonicity_index(signal: np.ndarray, rate_hz: float = 100.0) -> float:
    """Calcola l'Harmonicity Index (H) dal profilo di velocità/accelerazione.
    
    Un valore H vicina a 1 indica un moto armonico pulito (es. sottomovimento singolo), 
    valori vicini a 0 indicano molteplici sub-inversioni/sub-picchi.
    """
    signal = np.asarray(signal)
    if len(signal) < 10:
        return np.nan

    # Calcola l'accelerazione
    acc = np.gradient(signal, 1.0 / rate_hz)
    
    # Trova le inversioni di segno dell'accelerazione (zero-crossings)
    zero_crossings = np.where(np.diff(np.signbit(acc)))[0]
    num_inflections = len(zero_crossings)

    if num_inflections == 0:
        return 1.0

    # Trova i picchi principali del segnale
    peaks, _ = find_peaks(signal)
    num_peaks = len(peaks)

    if num_peaks == 0:
        return 1.0

    # Rapporto teorico: 1 moto armonico ha 2 inversioni di accelerazione per ciclo/picco
    h_index = (2.0 * num_peaks) / float(num_inflections)
    return float(np.clip(h_index, 0.0, 1.0))


def compute_submovement_count(
    signal: np.ndarray, 
    rate_hz: float = 100.0, 
    prominence_factor: float = 0.1
) -> int:
    """Stima il numero di sottomovimenti contando i picchi di velocità significativi.
    
    Parameters
    ----------
    signal : np.ndarray
        Profilo di velocità (mm/s).
    prominence_factor : float
        Prominenza minima del picco espressa come frazione del picco massimo.
    """
    signal = np.asarray(signal)
    v_max = np.max(signal)
    
    if v_max < 1e-6:
        return 0

    min_prominence = prominence_factor * v_max
    # Distanza minima tra picchi correlata alla durata fisiologica minima di un submovement (~100ms)
    min_distance = max(1, int(0.10 * rate_hz)) 

    peaks, _ = find_peaks(signal, prominence=min_prominence, distance=min_distance)
    return len(peaks)


def compute_eyesweb_smoothness_and_fluidity(
    positions: np.ndarray, dt: float, epsilon: float = 1e-6
) -> dict:
    """Calcola la Smoothness e la Fluidity del movimento secondo il modello descritto

    nel paper "Adaptive Body Gesture Representation for Automatic
    Emotion Recognition"

    Parameters:
    -----------
    positions : np.ndarray
        Matrice delle posizioni nel tempo con forma (N, 3) o (N, 2),
        dove N è il numero di campioni temporali.
    dt : float
        Intervallo di campionamento temporale tra due frame successivi (in
        secondi).
    epsilon : float
        Valore di tolleranza per evitare divisioni per zero.

    Returns:
    --------
    dict
        Dizionario contenente:
        - 'smoothness': Coefficente di correlazione r tra log(curvatura) e
        log(velocità).
        - 'fluidity': Grado di aderenza al modello minimum jerk (0 = non
        fluido, 1 = ideale).
        - 'curvature': Serie temporale della curvatura.
        - 'speed': Serie temporale della velocità tangenziale.
    """
    positions = np.asarray(positions, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[0] < 5:
        return {
            "smoothness": np.nan,
            "fluidity": np.nan,
            "curvature": np.array([]),
            "speed": np.array([]),
        }

    # -------------------------------------------------------------------------
    # 1. Calcolo Derivate Temporali: Velocità (v), Accelerazione (a), Jerk (j)
    # -------------------------------------------------------------------------
    v_vec = np.gradient(positions, dt, axis=0)  # Velocità vettoriale v(t)
    a_vec = np.gradient(v_vec, dt, axis=0)  # Accelerazione vettoriale a(t)
    j_vec = np.gradient(a_vec, dt, axis=0)  # Jerk vettoriale j(t)

    # Velocità tangenziale v(t) = ||v_vec(t)||
    speed = np.linalg.norm(v_vec, axis=1)

    # -------------------------------------------------------------------------
    # 2. Calcolo della Curvatura \kappa(t) (Eq. 14 del PDF)
    #    \kappa = ||v \times a|| / ||v||^3  (in 3D)
    # -------------------------------------------------------------------------
    if positions.shape[1] == 3:
        cross_prod = np.cross(v_vec, a_vec)
        cross_norm = np.linalg.norm(cross_prod, axis=1)
    else:  # Se in 2D (x, y)
        cross_norm = np.abs(
            v_vec[:, 0] * a_vec[:, 1] - v_vec[:, 1] * a_vec[:, 0]
        )

    speed_cubed = speed**3
    # Maschera per evitare divisioni per zero in fasce a velocità pressoché nulla
    valid_speed_mask = speed_cubed > epsilon
    curvature = np.zeros_like(speed)
    curvature[valid_speed_mask] = (
        cross_norm[valid_speed_mask] / speed_cubed[valid_speed_mask]
    )

    # -------------------------------------------------------------------------
    # 3. Calcolo della Smoothness (Correlazione Log-Log, Eq. 15-16 del PDF)
    #    Relazione Power-Law: v(t) = C * \kappa(t)^\beta
    #    \log(v) = \log(C) + \beta * \log(\kappa)
    # -------------------------------------------------------------------------
    # Filtriamo i punti validi dove sia la velocità che la curvatura sono positive e stabili
    valid_pts = (speed > epsilon) & (curvature > epsilon)

    if np.sum(valid_pts) > 3:
        log_speed = np.log(speed[valid_pts])
        log_curvature = np.log(curvature[valid_pts])

        # Coefficente di correlazione r tra log(curvatura) e log(velocità)
        corr_matrix = np.corrcoef(log_curvature, log_speed)
        smoothness_r = corr_matrix[0, 1]
    else:
        smoothness_r = np.nan

    # -------------------------------------------------------------------------
    # 4. Calcolo della Fluidity (Minimum Jerk / Integrated Squared Jerk, Eq. 17
    # del PDF)
    #    Fluidity = 1 / (1 + \int ||jerk(t)||^2 dt)
    # -------------------------------------------------------------------------
    jerk_squared_norm = np.sum(j_vec**2, axis=1)
    integrated_jerk = np.trapz(jerk_squared_norm, dx=dt)

    # Normalizzazione per rendere la Fluidity una metrica limitata nell'intervallo (0, 1]
    fluidity = 1.0 / (1.0 + integrated_jerk)

    return {
        "smoothness": float(smoothness_r),
        "fluidity": float(fluidity),
        "curvature": curvature,
        "speed": speed,
    }



def normalize_signal(signal):
    """Normalize signal by its maximum absolute value.

    Scales the signal to the range [-1, 1] by dividing by the maximum
    absolute value.

    Parameters
    ----------
    signal : ndarray
        Input signal to normalize.

    Returns
    -------
    ndarray
        Normalized signal with same shape as input.
        Returns original signal if max absolute value is 0.
    """
    max_val = np.max(np.abs(signal))
    return signal / max_val if max_val != 0 else signal


def extract_velocity_from_position(position, rate_hz=50.0):
    """Extract velocity from position data.

    Computes velocity magnitude from position data of any dimensionality.
    For 1D position, returns absolute velocity. For multi-dimensional position,
    returns the Euclidean norm of the velocity vector.

    Parameters
    ----------
    position : ndarray
        Position data. Can be:
        - 1D array: single position coordinate
        - 2D array with shape (n_samples, n_dims): multi-dimensional positions
    rate_hz : float, optional
        Sampling rate in Hz (default: 50.0).

    Returns
    -------
    ndarray
        1D array of velocity magnitudes.

    Examples
    --------
    >>> # 1D position data
    >>> position_1d = np.array([0, 1, 2, 3, 4])
    >>> velocity = extract_velocity_from_position(position_1d, rate_hz=100)

    >>> # 2D position data (x, y coordinates)
    >>> position_2d = np.array([[0, 0], [1, 0], [1, 1], [2, 1]])
    >>> velocity = extract_velocity_from_position(position_2d, rate_hz=100)
    """
    rate_hz = validate_numeric(rate_hz, 'rate_hz', min_val=0.0001)
    dt = 1.0 / rate_hz

    position = np.asarray(position)

    # Handle 1D position
    if position.ndim == 1 or (position.ndim == 2 and position.shape[1] == 1):
        signal_1d = position.squeeze()
        return np.abs(np.gradient(signal_1d, dt))

    # Handle multi-dimensional position
    if position.ndim == 2:
        # Compute derivatives along time axis (axis=0)
        derivatives = np.gradient(position, dt, axis=0)
        # Return Euclidean norm of velocity vector
        return np.linalg.norm(derivatives, axis=1)

    raise ValueError(f"Position must be 1D or 2D array, got shape {position.shape}")