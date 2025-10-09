"""
Signal Generation Utilities for PyEyesWeb Testing

This module provides signal generation capabilities for testing
PyEyesWeb features. It includes various signal types from simple periodic
waves to complex modulated and stochastic signals.

Author: PyEyesWeb Development Team
"""

import numpy as np
from typing import Tuple, Dict, Any, List, Optional, Callable
from scipy import signal as sp_signal
from scipy.interpolate import interp1d


class SignalGenerator:
    """
    Signal generator for testing and analysis.

    This class provides methods to generate various types of signals commonly
    used in signal processing, neuroscience, and movement analysis.
    """

    # Registry of available signal generators
    _generators: Dict[str, Callable] = {}

    def __init__(self, sampling_rate: float = 100.0):
        """
        Initialize the signal generator.

        Args:
            sampling_rate: Default sampling rate in Hz
        """
        self.sampling_rate = sampling_rate
        self._register_generators()

    def _create_time_array(self, length: int) -> np.ndarray:
        """Create time array for signal generation.

        Args:
            length: Number of samples

        Returns:
            Time array from 0 to duration
        """
        return np.linspace(0, length / self.sampling_rate, length)

    def _create_metadata(self, signal_type: str, **params) -> Dict[str, Any]:
        """Create metadata dictionary with common fields.

        Args:
            signal_type: Type of signal
            **params: Additional parameters to include

        Returns:
            Metadata dictionary with type, sampling_rate, and additional params
        """
        metadata = {
            'type': signal_type,
            'sampling_rate': self.sampling_rate
        }
        metadata.update(params)
        return metadata

    def _register_generators(self):
        """Register all available signal generators."""
        self._generators = {
            # Basic waveforms
            'sine': self.sine_wave,
            'cosine': self.cosine_wave,
            'square': self.square_wave,
            'sawtooth': self.sawtooth_wave,
            'triangle': self.triangle_wave,

            # Noise signals
            'random': self.random_signal,
            'gaussian': self.gaussian_noise,
            'pink': self.pink_noise,
            'brown': self.brownian_motion,
            'white': self.white_noise,

            # Complex signals
            'chirp': self.chirp_signal,
            'chirp_exp': self.exponential_chirp,
            'chirp_hyperbolic': self.hyperbolic_chirp,
            'multisine': self.multi_sine,
            'complex': self.complex_signal,

            # Modulated signals
            'am': self.amplitude_modulated,
            'fm': self.frequency_modulated,
            'pm': self.phase_modulated,
            'pwm': self.pulse_width_modulated,

            # Transient signals
            'impulse': self.impulse_train,
            'step': self.step_function,
            'ramp': self.ramp_function,
            'exponential': self.exponential_decay,
            'damped_sine': self.damped_sine,

            # Biological/Movement signals
            'ecg': self.ecg_like,
            'emg': self.emg_like,
            'tremor': self.tremor_signal,
            'gait': self.gait_pattern,
            'breathing': self.breathing_pattern,

            # Special signals
            'lorenz': self.lorenz_attractor,
            'chaos': self.logistic_map,
            'fractal': self.fractal_noise,
            'burst': self.burst_signal,
            'spike_train': self.spike_train,

            # Combined signals
            'noisy_sine': self.noisy_sine,
            'drift_sine': self.sine_with_drift,
            'intermittent': self.intermittent_signal,
            'switched': self.switched_signal,
        }

    def generate(self, signal_type: str, length: int = 1000, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Generate a signal based on type and parameters.

        Args:
            signal_type: Type of signal to generate
            length: Number of samples
            **kwargs: Additional parameters specific to each signal type

        Returns:
            Tuple of (time_array, signal_array, metadata_dict)
        """
        if signal_type not in self._generators:
            available = ', '.join(sorted(self._generators.keys()))
            raise ValueError(f"Unknown signal type: '{signal_type}'. Available types: {available}")

        # Override sampling rate if provided
        if 'sampling_rate' in kwargs:
            self.sampling_rate = kwargs['sampling_rate']

        return self._generators[signal_type](length, **kwargs)

    @property
    def available_signals(self) -> List[str]:
        """Get list of available signal types."""
        return sorted(list(self._generators.keys()))

    @property
    def signal_info(self) -> Dict[str, Dict[str, str]]:
        """Get detailed information about all signal types.

        Returns
        -------
        dict
            Dictionary mapping signal names to their metadata including
            description and category.
        """
        return {
            # Basic Waveforms
            'sine': {'description': 'Sine wave', 'category': 'Basic Waveforms'},
            'cosine': {'description': 'Cosine wave', 'category': 'Basic Waveforms'},
            'square': {'description': 'Square wave', 'category': 'Basic Waveforms'},
            'sawtooth': {'description': 'Sawtooth wave', 'category': 'Basic Waveforms'},
            'triangle': {'description': 'Triangle wave', 'category': 'Basic Waveforms'},

            # Noise Signals
            'random': {'description': 'Random uniform noise', 'category': 'Noise Signals'},
            'gaussian': {'description': 'Gaussian noise', 'category': 'Noise Signals'},
            'white': {'description': 'White noise', 'category': 'Noise Signals'},
            'pink': {'description': 'Pink (1/f) noise', 'category': 'Noise Signals'},
            'brown': {'description': 'Brownian motion (random walk)', 'category': 'Noise Signals'},

            # Chirp Signals
            'chirp': {'description': 'Linear chirp signal', 'category': 'Chirp Signals'},
            'chirp_exp': {'description': 'Exponential chirp signal', 'category': 'Chirp Signals'},
            'chirp_hyperbolic': {'description': 'Hyperbolic chirp signal', 'category': 'Chirp Signals'},

            # Modulated
            'am': {'description': 'Amplitude modulated signal', 'category': 'Modulated'},
            'fm': {'description': 'Frequency modulated signal', 'category': 'Modulated'},
            'pm': {'description': 'Phase modulated signal', 'category': 'Modulated'},
            'pwm': {'description': 'Pulse width modulated signal', 'category': 'Modulated'},

            # Transient
            'impulse': {'description': 'Impulse train', 'category': 'Transient'},
            'step': {'description': 'Step function', 'category': 'Transient'},
            'ramp': {'description': 'Ramp function', 'category': 'Transient'},
            'exponential': {'description': 'Exponential decay', 'category': 'Transient'},
            'damped_sine': {'description': 'Damped sine wave', 'category': 'Transient'},

            # Biological
            'ecg': {'description': 'ECG-like biological signal', 'category': 'Biological'},
            'emg': {'description': 'EMG-like muscle activity signal', 'category': 'Biological'},
            'tremor': {'description': 'Tremor signal (slow + fast oscillation)', 'category': 'Biological'},
            'gait': {'description': 'Gait pattern signal', 'category': 'Biological'},
            'breathing': {'description': 'Breathing pattern signal', 'category': 'Biological'},

            # Complex
            'complex': {'description': 'Complex multi-frequency signal', 'category': 'Complex'},
            'multisine': {'description': 'Multiple sine waves combined', 'category': 'Complex'},
            'noisy_sine': {'description': 'Sine wave with noise', 'category': 'Complex'},
            'drift_sine': {'description': 'Sine wave with linear drift', 'category': 'Complex'},
            'intermittent': {'description': 'Intermittent signal', 'category': 'Complex'},
            'switched': {'description': 'Frequency-switching signal', 'category': 'Complex'},

            # Chaotic
            'lorenz': {'description': 'Lorenz attractor (chaotic)', 'category': 'Chaotic'},
            'chaos': {'description': 'Logistic map (chaotic)', 'category': 'Chaotic'},
            'fractal': {'description': 'Fractal noise (fBm)', 'category': 'Chaotic'},
            'burst': {'description': 'Burst signal', 'category': 'Chaotic'},
            'spike_train': {'description': 'Neural spike train', 'category': 'Chaotic'},
        }

    def get_signals_by_category(self) -> Dict[str, List[str]]:
        """Get signals organized by category.

        Returns
        -------
        dict
            Dictionary mapping category names to lists of signal types.
        """
        categories = {}
        for signal_name, info in self.signal_info.items():
            category = info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(signal_name)
        return categories

    # ========================================================================
    # Basic Waveforms
    # ========================================================================

    def sine_wave(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                  phase: float = 0.0, dc_offset: float = 0.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a sine wave."""
        t = self._create_time_array(length)
        signal = amplitude * np.sin(2 * np.pi * freq * t + phase) + dc_offset
        metadata = self._create_metadata(
            'sine',
            frequency=freq,
            amplitude=amplitude,
            phase=phase,
            dc_offset=dc_offset
        )
        return t, signal, metadata

    def cosine_wave(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                    phase: float = 0.0, dc_offset: float = 0.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a cosine wave."""
        t = self._create_time_array(length)
        signal = amplitude * np.cos(2 * np.pi * freq * t + phase) + dc_offset
        metadata = {
            'type': 'cosine',
            'frequency': freq,
            'amplitude': amplitude,
            'phase': phase,
            'dc_offset': dc_offset,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def square_wave(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                   duty_cycle: float = 0.5, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a square wave."""
        t = self._create_time_array(length)
        signal = amplitude * sp_signal.square(2 * np.pi * freq * t, duty=duty_cycle)
        metadata = {
            'type': 'square',
            'frequency': freq,
            'amplitude': amplitude,
            'duty_cycle': duty_cycle,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def sawtooth_wave(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                     width: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a sawtooth wave."""
        t = self._create_time_array(length)
        signal = amplitude * sp_signal.sawtooth(2 * np.pi * freq * t, width=width)
        metadata = {
            'type': 'sawtooth',
            'frequency': freq,
            'amplitude': amplitude,
            'width': width,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def triangle_wave(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                     **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a triangle wave."""
        t = self._create_time_array(length)
        signal = amplitude * sp_signal.sawtooth(2 * np.pi * freq * t, width=0.5)
        metadata = {
            'type': 'triangle',
            'frequency': freq,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Noise Signals
    # ========================================================================

    def random_signal(self, length: int, seed: Optional[int] = None,
                     min_val: float = -1.0, max_val: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate random uniform noise."""
        if seed is not None:
            np.random.seed(seed)
        t = self._create_time_array(length)
        signal = np.random.uniform(min_val, max_val, length)
        metadata = {
            'type': 'random',
            'distribution': 'uniform',
            'range': [min_val, max_val],
            'seed': seed,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def gaussian_noise(self, length: int, mean: float = 0.0, std: float = 1.0,
                      seed: Optional[int] = None, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate Gaussian (white) noise."""
        if seed is not None:
            np.random.seed(seed)
        t = self._create_time_array(length)
        signal = np.random.normal(mean, std, length)
        metadata = {
            'type': 'gaussian',
            'mean': mean,
            'std': std,
            'seed': seed,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def white_noise(self, length: int, power: float = 1.0, seed: Optional[int] = None,
                   **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate white noise with specified power."""
        if seed is not None:
            np.random.seed(seed)
        t = self._create_time_array(length)
        signal = np.random.normal(0, np.sqrt(power), length)
        metadata = {
            'type': 'white_noise',
            'power': power,
            'seed': seed,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def pink_noise(self, length: int, amplitude: float = 1.0, seed: Optional[int] = None,
                  **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate pink (1/f) noise."""
        if seed is not None:
            np.random.seed(seed)

        # Generate white noise
        white = np.random.randn(length)

        # Apply 1/f filter in frequency domain
        fft = np.fft.rfft(white)
        freqs = np.fft.rfftfreq(length)
        freqs[0] = 1  # Avoid division by zero
        fft = fft / np.sqrt(freqs)
        signal = np.fft.irfft(fft, length)

        # Normalize
        signal = amplitude * signal / np.std(signal)

        t = self._create_time_array(length)
        metadata = {
            'type': 'pink_noise',
            'amplitude': amplitude,
            'seed': seed,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def brownian_motion(self, length: int, std: float = 0.1, seed: Optional[int] = None,
                       **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate Brownian motion (random walk)."""
        if seed is not None:
            np.random.seed(seed)
        t = self._create_time_array(length)
        steps = np.random.normal(0, std, length)
        signal = np.cumsum(steps)
        metadata = {
            'type': 'brownian_motion',
            'step_std': std,
            'seed': seed,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Complex Signals
    # ========================================================================

    def chirp_signal(self, length: int, freq_start: float = 1.0, freq_end: float = 10.0,
                    amplitude: float = 1.0, method: str = 'linear',
                    **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a chirp signal (linear frequency sweep)."""
        t = self._create_time_array(length)
        signal = amplitude * sp_signal.chirp(t, freq_start, t[-1], freq_end, method=method)
        metadata = {
            'type': 'chirp',
            'freq_start': freq_start,
            'freq_end': freq_end,
            'method': method,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def exponential_chirp(self, length: int, freq_start: float = 1.0, freq_end: float = 10.0,
                         amplitude: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an exponential chirp signal."""
        return self.chirp_signal(length, freq_start, freq_end, amplitude, method='exponential')

    def hyperbolic_chirp(self, length: int, freq_start: float = 1.0, freq_end: float = 10.0,
                        amplitude: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a hyperbolic chirp signal."""
        return self.chirp_signal(length, freq_start, freq_end, amplitude, method='hyperbolic')

    def multi_sine(self, length: int, frequencies: List[float] = None,
                  amplitudes: List[float] = None, phases: List[float] = None,
                  **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate multiple sine waves combined."""
        if frequencies is None:
            frequencies = [1.0, 3.0, 5.0]
        if amplitudes is None:
            amplitudes = [1.0] * len(frequencies)
        if phases is None:
            phases = [0.0] * len(frequencies)

        t = self._create_time_array(length)
        signal = np.zeros(length)

        for freq, amp, phase in zip(frequencies, amplitudes, phases):
            signal += amp * np.sin(2 * np.pi * freq * t + phase)

        metadata = {
            'type': 'multi_sine',
            'frequencies': frequencies,
            'amplitudes': amplitudes,
            'phases': phases,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def complex_signal(self, length: int, components: List[Dict] = None,
                      **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a complex signal with multiple frequency components."""
        if components is None:
            components = [
                {'freq': 5, 'amp': 1.0, 'phase': 0},
                {'freq': 10, 'amp': 0.5, 'phase': np.pi/4},
                {'freq': 20, 'amp': 0.3, 'phase': np.pi/2}
            ]

        t = self._create_time_array(length)
        signal = np.zeros(length)

        for comp in components:
            signal += comp['amp'] * np.sin(2 * np.pi * comp['freq'] * t + comp.get('phase', 0))

        metadata = {
            'type': 'complex',
            'components': components,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Modulated Signals
    # ========================================================================

    def amplitude_modulated(self, length: int, carrier_freq: float = 10.0,
                          modulation_freq: float = 1.0, modulation_index: float = 0.5,
                          **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an amplitude modulated signal."""
        t = self._create_time_array(length)
        carrier = np.sin(2 * np.pi * carrier_freq * t)
        modulator = 1 + modulation_index * np.sin(2 * np.pi * modulation_freq * t)
        signal = modulator * carrier
        metadata = {
            'type': 'amplitude_modulated',
            'carrier_freq': carrier_freq,
            'modulation_freq': modulation_freq,
            'modulation_index': modulation_index,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def frequency_modulated(self, length: int, carrier_freq: float = 10.0,
                          modulation_freq: float = 1.0, modulation_index: float = 5.0,
                          **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a frequency modulated signal."""
        t = self._create_time_array(length)
        modulator = modulation_index * np.sin(2 * np.pi * modulation_freq * t)
        phase = 2 * np.pi * carrier_freq * t + modulator
        signal = np.sin(phase)
        metadata = {
            'type': 'frequency_modulated',
            'carrier_freq': carrier_freq,
            'modulation_freq': modulation_freq,
            'modulation_index': modulation_index,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def phase_modulated(self, length: int, carrier_freq: float = 10.0,
                       modulation_freq: float = 1.0, modulation_index: float = np.pi,
                       **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a phase modulated signal."""
        t = self._create_time_array(length)
        phase_modulation = modulation_index * np.sin(2 * np.pi * modulation_freq * t)
        signal = np.sin(2 * np.pi * carrier_freq * t + phase_modulation)
        metadata = {
            'type': 'phase_modulated',
            'carrier_freq': carrier_freq,
            'modulation_freq': modulation_freq,
            'modulation_index': modulation_index,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def pulse_width_modulated(self, length: int, carrier_freq: float = 10.0,
                            modulation_freq: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a pulse width modulated signal."""
        t = self._create_time_array(length)
        duty_cycle = 0.5 + 0.4 * np.sin(2 * np.pi * modulation_freq * t)
        signal = np.zeros(length)

        # Generate PWM signal
        phase = (carrier_freq * t) % 1
        for i in range(length):
            signal[i] = 1 if phase[i] < duty_cycle[i] else -1

        metadata = {
            'type': 'pulse_width_modulated',
            'carrier_freq': carrier_freq,
            'modulation_freq': modulation_freq,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Transient Signals
    # ========================================================================

    def impulse_train(self, length: int, period: int = 100, amplitude: float = 1.0,
                     jitter: float = 0.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an impulse train with optional jitter."""
        t = self._create_time_array(length)
        signal = np.zeros(length)

        if jitter > 0:
            positions = np.arange(0, length, period)
            positions += np.random.uniform(-jitter * period, jitter * period, len(positions))
            positions = np.clip(positions.astype(int), 0, length - 1)
            signal[positions] = amplitude
        else:
            signal[::period] = amplitude

        metadata = {
            'type': 'impulse_train',
            'period': period,
            'amplitude': amplitude,
            'jitter': jitter,
            'num_impulses': np.sum(signal != 0),
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def step_function(self, length: int, step_time: float = 0.5, amplitude: float = 1.0,
                     **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a step function."""
        t = np.linspace(0, 1, length)
        signal = np.ones(length) * amplitude
        signal[t < step_time] = 0
        metadata = {
            'type': 'step',
            'step_time': step_time,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t * length / self.sampling_rate, signal, metadata

    def ramp_function(self, length: int, slope: float = 1.0, start_value: float = 0.0,
                     **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a ramp function."""
        t = self._create_time_array(length)
        signal = start_value + slope * t
        metadata = {
            'type': 'ramp',
            'slope': slope,
            'start_value': start_value,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def exponential_decay(self, length: int, amplitude: float = 1.0, decay_rate: float = 1.0,
                        **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an exponential decay signal."""
        t = self._create_time_array(length)
        signal = amplitude * np.exp(-decay_rate * t)
        metadata = {
            'type': 'exponential_decay',
            'amplitude': amplitude,
            'decay_rate': decay_rate,
            'time_constant': 1 / decay_rate,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def damped_sine(self, length: int, freq: float = 5.0, amplitude: float = 1.0,
                   damping: float = 0.1, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a damped sine wave."""
        t = self._create_time_array(length)
        envelope = amplitude * np.exp(-damping * t)
        signal = envelope * np.sin(2 * np.pi * freq * t)
        metadata = {
            'type': 'damped_sine',
            'frequency': freq,
            'amplitude': amplitude,
            'damping': damping,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Biological/Movement Signals
    # ========================================================================

    def ecg_like(self, length: int, heart_rate: float = 60.0, amplitude: float = 1.0,
                **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an ECG-like signal."""
        t = self._create_time_array(length)
        beat_period = 60.0 / heart_rate  # Period in seconds
        n_beats = int(t[-1] / beat_period)

        signal = np.zeros(length)

        # Simple ECG model with P, QRS, T waves
        for beat in range(n_beats):
            beat_start = beat * beat_period
            beat_indices = np.where((t >= beat_start) & (t < beat_start + beat_period))[0]

            if len(beat_indices) > 0:
                beat_t = t[beat_indices] - beat_start
                # P wave
                p_wave = 0.2 * amplitude * np.exp(-((beat_t - 0.15) ** 2) / (2 * 0.01))
                # QRS complex
                qrs = amplitude * np.exp(-((beat_t - 0.2) ** 2) / (2 * 0.001))
                # T wave
                t_wave = 0.3 * amplitude * np.exp(-((beat_t - 0.4) ** 2) / (2 * 0.02))
                signal[beat_indices] = p_wave + qrs + t_wave

        metadata = {
            'type': 'ecg_like',
            'heart_rate': heart_rate,
            'amplitude': amplitude,
            'n_beats': n_beats,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def emg_like(self, length: int, burst_frequency: float = 2.0, burst_duration: float = 0.2,
                amplitude: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an EMG-like signal with bursts of activity."""
        t = self._create_time_array(length)
        signal = np.zeros(length)

        # Generate burst envelope
        burst_period = 1.0 / burst_frequency
        for burst_start in np.arange(0, t[-1], burst_period):
            burst_mask = (t >= burst_start) & (t < burst_start + burst_duration)
            # High-frequency noise during burst
            signal[burst_mask] = amplitude * np.random.normal(0, 1, np.sum(burst_mask))

        # Add baseline noise
        signal += 0.05 * amplitude * np.random.normal(0, 1, length)

        metadata = {
            'type': 'emg_like',
            'burst_frequency': burst_frequency,
            'burst_duration': burst_duration,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def tremor_signal(self, length: int, tremor_freq: float = 5.0, base_freq: float = 0.5,
                     tremor_amplitude: float = 0.3, base_amplitude: float = 1.0,
                     **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a tremor-like signal (slow movement with superimposed tremor)."""
        t = self._create_time_array(length)
        base_movement = base_amplitude * np.sin(2 * np.pi * base_freq * t)
        tremor = tremor_amplitude * np.sin(2 * np.pi * tremor_freq * t)
        signal = base_movement + tremor
        metadata = {
            'type': 'tremor',
            'tremor_freq': tremor_freq,
            'base_freq': base_freq,
            'tremor_amplitude': tremor_amplitude,
            'base_amplitude': base_amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def gait_pattern(self, length: int, step_frequency: float = 2.0, amplitude: float = 1.0,
                    **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a gait-like pattern."""
        t = self._create_time_array(length)
        # Double bump pattern for heel strike and toe-off
        signal = amplitude * (np.sin(2 * np.pi * step_frequency * t) +
                             0.3 * np.sin(4 * np.pi * step_frequency * t))
        # Add some variability
        signal += 0.05 * amplitude * np.random.normal(0, 1, length)
        metadata = {
            'type': 'gait_pattern',
            'step_frequency': step_frequency,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def breathing_pattern(self, length: int, breathing_rate: float = 12.0,
                        inhale_ratio: float = 0.4, amplitude: float = 1.0,
                        **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a breathing-like pattern."""
        t = self._create_time_array(length)
        breathing_period = 60.0 / breathing_rate  # Period in seconds
        signal = np.zeros(length)

        for breath_start in np.arange(0, t[-1], breathing_period):
            inhale_end = breath_start + inhale_ratio * breathing_period
            exhale_end = breath_start + breathing_period

            # Inhale phase (rising)
            inhale_mask = (t >= breath_start) & (t < inhale_end)
            if np.any(inhale_mask):
                inhale_t = (t[inhale_mask] - breath_start) / (inhale_ratio * breathing_period)
                signal[inhale_mask] = amplitude * (1 - np.cos(np.pi * inhale_t)) / 2

            # Exhale phase (falling)
            exhale_mask = (t >= inhale_end) & (t < exhale_end)
            if np.any(exhale_mask):
                exhale_t = (t[exhale_mask] - inhale_end) / ((1 - inhale_ratio) * breathing_period)
                signal[exhale_mask] = amplitude * (1 + np.cos(np.pi * exhale_t)) / 2

        metadata = {
            'type': 'breathing_pattern',
            'breathing_rate': breathing_rate,
            'inhale_ratio': inhale_ratio,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Special Signals
    # ========================================================================

    def lorenz_attractor(self, length: int, sigma: float = 10.0, rho: float = 28.0,
                        beta: float = 8/3, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate signal from Lorenz attractor (chaotic system)."""
        dt = 0.01
        t = np.arange(0, length * dt, dt)[:length]

        # Initialize
        x, y, z = 1.0, 1.0, 1.0
        signal = np.zeros(length)

        # Integrate Lorenz equations
        for i in range(length):
            dx = sigma * (y - x) * dt
            dy = (x * (rho - z) - y) * dt
            dz = (x * y - beta * z) * dt
            x += dx
            y += dy
            z += dz
            signal[i] = x  # Use x coordinate as signal

        # Normalize
        signal = (signal - np.mean(signal)) / np.std(signal)

        metadata = {
            'type': 'lorenz_attractor',
            'sigma': sigma,
            'rho': rho,
            'beta': beta,
            'sampling_rate': self.sampling_rate
        }
        return t * self.sampling_rate, signal, metadata

    def logistic_map(self, length: int, r: float = 3.8, x0: float = 0.5,
                    **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate signal from logistic map (chaotic for r > 3.57)."""
        t = self._create_time_array(length)
        signal = np.zeros(length)
        x = x0

        for i in range(length):
            x = r * x * (1 - x)
            signal[i] = x

        metadata = {
            'type': 'logistic_map',
            'r': r,
            'x0': x0,
            'chaotic': r > 3.57,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def fractal_noise(self, length: int, hurst: float = 0.5, amplitude: float = 1.0,
                     **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate fractal noise using fractional Brownian motion."""
        from scipy.fft import fft, ifft, fftfreq

        # Generate frequencies
        freqs = fftfreq(length, 1/self.sampling_rate)
        freqs[0] = 1  # Avoid division by zero

        # Generate random phases
        phases = np.random.uniform(0, 2*np.pi, length)

        # Create power spectrum with 1/f^(2H+1) scaling
        power = np.abs(freqs) ** -(2 * hurst + 1)
        power[0] = 0  # Remove DC component

        # Generate signal in frequency domain
        fft_signal = np.sqrt(power) * np.exp(1j * phases)

        # Transform to time domain
        signal = np.real(ifft(fft_signal))
        signal = amplitude * signal / np.std(signal)

        t = self._create_time_array(length)
        metadata = {
            'type': 'fractal_noise',
            'hurst': hurst,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def burst_signal(self, length: int, burst_freq: float = 2.0, burst_duration: float = 0.1,
                    carrier_freq: float = 20.0, amplitude: float = 1.0,
                    **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate burst signal (periodic bursts of oscillation)."""
        t = self._create_time_array(length)
        carrier = amplitude * np.sin(2 * np.pi * carrier_freq * t)

        # Create burst envelope
        burst_period = 1.0 / burst_freq
        envelope = np.zeros(length)
        for burst_start in np.arange(0, t[-1], burst_period):
            burst_mask = (t >= burst_start) & (t < burst_start + burst_duration)
            envelope[burst_mask] = 1.0

        signal = carrier * envelope
        metadata = {
            'type': 'burst_signal',
            'burst_freq': burst_freq,
            'burst_duration': burst_duration,
            'carrier_freq': carrier_freq,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def spike_train(self, length: int, spike_rate: float = 10.0, refractory_period: float = 0.002,
                   amplitude: float = 1.0, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a neural spike train."""
        t = self._create_time_array(length)
        dt = 1.0 / self.sampling_rate
        signal = np.zeros(length)

        # Generate spikes with refractory period
        last_spike_time = -refractory_period
        spike_times = []

        for i, time in enumerate(t):
            if time - last_spike_time > refractory_period:
                if np.random.random() < spike_rate * dt:
                    signal[i] = amplitude
                    last_spike_time = time
                    spike_times.append(time)

        metadata = {
            'type': 'spike_train',
            'spike_rate': spike_rate,
            'refractory_period': refractory_period,
            'amplitude': amplitude,
            'num_spikes': len(spike_times),
            'actual_rate': len(spike_times) / (t[-1] - t[0]) if t[-1] > t[0] else 0,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    # ========================================================================
    # Combined Signals
    # ========================================================================

    def noisy_sine(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                  noise_level: float = 0.1, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a sine wave with added noise."""
        t, clean_signal, _ = self.sine_wave(length, freq, amplitude)
        noise = np.random.normal(0, noise_level, length)
        signal = clean_signal + noise
        metadata = {
            'type': 'noisy_sine',
            'frequency': freq,
            'amplitude': amplitude,
            'noise_level': noise_level,
            'snr': 20 * np.log10(amplitude / noise_level) if noise_level > 0 else np.inf,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def sine_with_drift(self, length: int, freq: float = 1.0, amplitude: float = 1.0,
                       drift_rate: float = 0.01, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a sine wave with linear drift."""
        t, sine_signal, _ = self.sine_wave(length, freq, amplitude)
        drift = drift_rate * t
        signal = sine_signal + drift
        metadata = {
            'type': 'sine_with_drift',
            'frequency': freq,
            'amplitude': amplitude,
            'drift_rate': drift_rate,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def intermittent_signal(self, length: int, active_ratio: float = 0.3,
                          signal_freq: float = 5.0, amplitude: float = 1.0,
                          **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate an intermittent signal (randomly switches on/off)."""
        t = self._create_time_array(length)
        base_signal = amplitude * np.sin(2 * np.pi * signal_freq * t)

        # Create random on/off pattern
        switch_period = int(self.sampling_rate / 2)  # Switch every 0.5 seconds
        n_switches = length // switch_period + 1
        switches = np.random.random(n_switches) < active_ratio
        gate = np.repeat(switches, switch_period)[:length]

        signal = base_signal * gate
        metadata = {
            'type': 'intermittent_signal',
            'active_ratio': active_ratio,
            'signal_freq': signal_freq,
            'amplitude': amplitude,
            'actual_active_ratio': np.mean(gate),
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata

    def switched_signal(self, length: int, switch_period: int = 200,
                       freq1: float = 2.0, freq2: float = 8.0, amplitude: float = 1.0,
                       **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """Generate a signal that switches between two frequencies."""
        t = self._create_time_array(length)
        signal = np.zeros(length)

        for i in range(0, length, switch_period * 2):
            # First period: freq1
            end1 = min(i + switch_period, length)
            signal[i:end1] = amplitude * np.sin(2 * np.pi * freq1 * t[i:end1])

            # Second period: freq2
            start2 = end1
            end2 = min(start2 + switch_period, length)
            if start2 < length:
                signal[start2:end2] = amplitude * np.sin(2 * np.pi * freq2 * t[start2:end2])

        metadata = {
            'type': 'switched_signal',
            'switch_period': switch_period,
            'freq1': freq1,
            'freq2': freq2,
            'amplitude': amplitude,
            'sampling_rate': self.sampling_rate
        }
        return t, signal, metadata


# Convenience function for quick signal generation
def generate_signal(signal_type: str, length: int = 1000, **kwargs) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Quick signal generation without instantiating the class.

    Args:
        signal_type: Type of signal to generate
        length: Number of samples
        **kwargs: Additional parameters

    Returns:
        Tuple of (time_array, signal_array, metadata_dict)
    """
    generator = SignalGenerator()
    return generator.generate(signal_type, length, **kwargs)


# List all available signals
def list_available_signals() -> List[str]:
    """Get list of all available signal types."""
    generator = SignalGenerator()
    return generator.available_signals