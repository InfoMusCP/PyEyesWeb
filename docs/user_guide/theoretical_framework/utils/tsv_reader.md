# TSV Reader Module

The TSV Reader module provides efficient parsing and validation of motion capture data stored in Tab-Separated Values (TSV) format. It handles common motion capture file structures and provides data integrity checking.

## Overview

Motion capture systems often export data in TSV format with specific structures:
- Header information (marker names, coordinate labels)
- Frame-by-frame coordinate data
- Timestamp information
- Quality indicators and metadata

The TSV Reader module standardizes this data input for analysis pipeline integration.

## Class: `TSVReader`

### Constructor

```python
TSVReader(file_path, validate_data=True, coordinate_system='xyz')
```

**Parameters:**
- `file_path` (str): Path to TSV file
- `validate_data` (bool): Enable data validation and integrity checking
- `coordinate_system` (str): Expected coordinate ordering ('xyz', 'xzy', etc.)

### Methods

#### `load_data()`

Loads complete TSV file into memory with validation.

**Returns:**
Dictionary containing:
- `'data'`: Numpy array of motion data (frames × markers × coordinates)
- `'marker_names'`: List of marker identifiers
- `'frame_rate'`: Sampling frequency (if available)
- `'metadata'`: Additional file information

#### `stream_frames(buffer_size=100)`

Generator for memory-efficient streaming of large files.

**Parameters:**
- `buffer_size` (int): Number of frames to buffer

**Yields:**
Frame dictionaries with marker coordinates and metadata

#### `get_marker_trajectory(marker_name)`

Extracts complete trajectory for a specific marker.

**Parameters:**
- `marker_name` (str): Name of target marker

**Returns:**
Numpy array of shape (n_frames, n_coordinates)

## File Format Specifications

### Standard TSV Structure

```
# Header with metadata
Frame	Timestamp	MARKER1_X	MARKER1_Y	MARKER1_Z	MARKER2_X	MARKER2_Y	MARKER2_Z
1	0.000	10.5	20.3	15.2	8.7	18.9	14.1
2	0.020	10.6	20.4	15.3	8.8	19.0	14.2
...
```

### Supported Variations
- Multiple coordinate systems (XYZ, XZY, YXZ, etc.)
- Optional quality indicators per marker
- Variable marker counts per frame
- Custom delimiter support

## Usage Examples

### Basic File Loading

```python
from pyeyesweb.utils.tsv_reader import TSVReader

# Load complete motion capture file
reader = TSVReader('motion_capture_data.tsv')
data = reader.load_data()

print(f"Loaded {data['data'].shape[0]} frames")
print(f"Markers: {data['marker_names']}")
print(f"Frame rate: {data['frame_rate']} Hz")

# Access specific marker data
marker_trajectory = data['data'][:, 0, :]  # First marker, all coordinates
```

### Streaming Large Files

```python
def process_large_mocap_file(file_path):
    """Process large motion capture files without loading into memory."""
    reader = TSVReader(file_path)
    
    frame_count = 0
    marker_velocities = []
    
    previous_frame = None
    
    for frame in reader.stream_frames(buffer_size=50):
        frame_count += 1
        
        if previous_frame is not None:
            # Calculate frame-to-frame velocity
            velocity = calculate_velocity(previous_frame, frame)
            marker_velocities.append(velocity)
        
        previous_frame = frame
        
        # Process in chunks to avoid memory overflow
        if frame_count % 1000 == 0:
            print(f"Processed {frame_count} frames")
    
    return marker_velocities

# Usage with large files
velocities = process_large_mocap_file('large_motion_file.tsv')
```

### Marker-Specific Analysis

```python
def analyze_specific_markers(file_path, target_markers):
    """Extract and analyze specific markers from motion data."""
    reader = TSVReader(file_path)
    
    results = {}
    
    for marker_name in target_markers:
        try:
            trajectory = reader.get_marker_trajectory(marker_name)
            
            # Basic trajectory analysis
            results[marker_name] = {
                'mean_position': np.mean(trajectory, axis=0),
                'position_std': np.std(trajectory, axis=0),
                'trajectory_length': calculate_path_length(trajectory),
                'velocity_profile': calculate_velocity(trajectory)
            }
            
        except KeyError:
            print(f"Marker '{marker_name}' not found in file")
            results[marker_name] = None
    
    return results

# Analyze specific markers
target_markers = ['HEAD', 'LEFT_WRIST', 'RIGHT_WRIST']
marker_analysis = analyze_specific_markers('motion_data.tsv', target_markers)
```

### Data Validation and Quality Assessment

```python
def validate_motion_data(file_path):
    """Comprehensive validation of motion capture data quality."""
    reader = TSVReader(file_path, validate_data=True)
    
    validation_report = {
        'file_valid': True,
        'missing_frames': [],
        'outlier_markers': [],
        'discontinuities': [],
        'quality_summary': {}
    }
    
    try:
        data = reader.load_data()
        
        # Check for missing data
        missing_mask = np.isnan(data['data'])
        if np.any(missing_mask):
            missing_frames = np.where(np.any(missing_mask, axis=(1,2)))[0]
            validation_report['missing_frames'] = missing_frames.tolist()
        
        # Detect outliers using z-score
        for marker_idx, marker_name in enumerate(data['marker_names']):
            marker_data = data['data'][:, marker_idx, :]
            z_scores = np.abs(stats.zscore(marker_data, axis=0, nan_policy='omit'))
            
            if np.any(z_scores > 3):
                validation_report['outlier_markers'].append(marker_name)
        
        # Check for large discontinuities
        velocities = np.diff(data['data'], axis=0)
        velocity_magnitudes = np.linalg.norm(velocities, axis=2)
        
        # Detect frames with unusually high velocities
        velocity_threshold = np.percentile(velocity_magnitudes.flatten(), 99)
        discontinuous_frames = np.where(
            np.any(velocity_magnitudes > velocity_threshold, axis=1)
        )[0]
        
        validation_report['discontinuities'] = discontinuous_frames.tolist()
        
        validation_report['quality_summary'] = {
            'total_frames': data['data'].shape[0],
            'missing_data_percentage': np.sum(missing_mask) / missing_mask.size * 100,
            'outlier_markers_count': len(validation_report['outlier_markers']),
            'discontinuity_frames': len(validation_report['discontinuities'])
        }
        
    except Exception as e:
        validation_report['file_valid'] = False
        validation_report['error_message'] = str(e)
    
    return validation_report

# Validate file quality
quality_report = validate_motion_data('motion_capture_data.tsv')
print(f"File valid: {quality_report['file_valid']}")
print(f"Missing data: {quality_report['quality_summary']['missing_data_percentage']:.2f}%")
```

## Configuration Options

### Coordinate System Handling

```python
# Different coordinate system conventions
readers = {
    'standard': TSVReader('data.tsv', coordinate_system='xyz'),
    'maya': TSVReader('maya_export.tsv', coordinate_system='xzy'),
    'blender': TSVReader('blender_data.tsv', coordinate_system='xyz')
}

# Automatic coordinate system detection
reader = TSVReader('unknown_system.tsv', coordinate_system='auto')
```

### Custom Validation Rules

```python
def custom_validator(data_frame):
    """Custom validation function for specific data requirements."""
    # Check frame completeness
    if len(data_frame) < expected_marker_count * 3:
        return False, "Incomplete frame data"
    
    # Check coordinate ranges
    coordinates = np.array(data_frame).reshape(-1, 3)
    if np.any(np.abs(coordinates) > 1000):  # 1 meter limit
        return False, "Coordinates outside expected range"
    
    return True, "Valid frame"

# Use custom validation
reader = TSVReader('data.tsv', custom_validator=custom_validator)
```

## Performance Optimization

### Memory Management
- Streaming interface for large files
- Configurable buffer sizes
- Lazy loading of marker data

### Processing Speed
- NumPy-based operations
- Vectorized coordinate transformations
- Efficient string parsing

### Error Handling
- Graceful handling of malformed data
- Detailed error reporting
- Recovery from partial file corruption

## Integration with Analysis Modules

### Pipeline Integration

```python
def complete_analysis_pipeline(tsv_file):
    """Complete motion analysis using TSV reader and analysis user_guide."""
    # Load data
    reader = TSVReader(tsv_file)
    data = reader.load_data()
    
    # Initialize analysis user_guide
    smoothness = Smoothness(rate_hz=data['frame_rate'])
    bilateral_analyzer = BilateralSymmetryAnalyzer()
    
    results = {}
    
    # Analyze each marker
    for i, marker_name in enumerate(data['marker_names']):
        marker_trajectory = data['data'][:, i, :]
        
        # Smoothness analysis
        window = SlidingWindow(window_size=100)
        window.add_frames(marker_trajectory)
        
        results[marker_name] = {
            'smoothness': smoothness(window),
            'trajectory_stats': {
                'mean_position': np.mean(marker_trajectory, axis=0),
                'movement_range': np.ptp(marker_trajectory, axis=0)
            }
        }
    
    # Bilateral analysis (if applicable)
    left_markers = [name for name in data['marker_names'] if 'LEFT' in name]
    right_markers = [name for name in data['marker_names'] if 'RIGHT' in name]
    
    if left_markers and right_markers:
        bilateral_results = analyze_bilateral_coordination(
            data, left_markers, right_markers, bilateral_analyzer
        )
        results['bilateral_analysis'] = bilateral_results
    
    return results
```

## Common File Format Issues

### Missing Data Handling
```python
# Strategies for handling missing marker data
def interpolate_missing_data(trajectory):
    """Linear interpolation for short gaps in trajectory data."""
    mask = ~np.isnan(trajectory).any(axis=1)
    
    if np.sum(mask) < 2:
        return trajectory  # Cannot interpolate
    
    valid_indices = np.where(mask)[0]
    
    for coord_idx in range(trajectory.shape[1]):
        trajectory[:, coord_idx] = np.interp(
            np.arange(len(trajectory)),
            valid_indices,
            trajectory[valid_indices, coord_idx]
        )
    
    return trajectory
```

### Timestamp Synchronization
```python
# Handle irregular timestamps
def regularize_timestamps(data, target_fps=50):
    """Resample data to regular timestamps."""
    original_times = data['timestamps']
    target_times = np.arange(0, original_times[-1], 1/target_fps)
    
    resampled_data = []
    for marker_idx in range(data['data'].shape[1]):
        marker_trajectory = data['data'][:, marker_idx, :]
        
        resampled_trajectory = np.zeros((len(target_times), 3))
        for coord_idx in range(3):
            resampled_trajectory[:, coord_idx] = np.interp(
                target_times, 
                original_times,
                marker_trajectory[:, coord_idx]
            )
        
        resampled_data.append(resampled_trajectory)
    
    return {
        'data': np.stack(resampled_data, axis=1),
        'timestamps': target_times,
        'frame_rate': target_fps
    }
```

## Best Practices

### File Organization
- Consistent marker naming conventions
- Include metadata headers
- Regular timestamp intervals
- Quality indicators when available

### Data Preprocessing
- Validate data integrity before analysis
- Handle missing data appropriately
- Consider coordinate system transformations
- Apply appropriate filtering for noise reduction

### Performance Optimization
- Use streaming for large files
- Buffer size tuning for memory constraints
- Parallel processing for multiple files
- Efficient marker selection for targeted analysis