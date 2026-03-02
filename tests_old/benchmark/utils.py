import csv
from collections import OrderedDict
import pandas as pd

def read_custom_tsv(filepath):
    """
    Reads a custom TSV file with metadata and data sections.
    Returns:
        metadata: OrderedDict of metadata key-value pairs
        columns: list of column names for the data section
        data: list of dicts, each representing a row of data
    """
    metadata = {}
    columns = []
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        # Read metadata
        for row in reader:
            if not row or all(cell.strip() == '' for cell in row):
                continue
            if row[0].startswith('Frame'):
                columns = [col for col in row if col]
                break
            key = row[0].lower()
            value = row[1:] if len(row) > 2 else row[1] if len(row) == 2 else None
            # Try to interpret value as int or float if possible
            if isinstance(value, list):
                parsed_value = []
                for v in value:
                    v = v.strip()
                    if v == '':
                        parsed_value.append(None)
                    else:
                        try:
                            parsed_value.append(int(v))
                        except ValueError:
                            try:
                                parsed_value.append(float(v))
                            except ValueError:
                                parsed_value.append(v)
                value = parsed_value
            elif isinstance(value, str):
                v = value.strip()
                if v == '':
                    value = None
                else:
                    try:
                        value = int(v)
                    except ValueError:
                        try:
                            value = float(v)
                        except ValueError:
                            pass
            metadata[key] = value
        # Read data
        for row in reader:
            if not row or all(cell.strip() == '' for cell in row):
                continue
            # Handle trailing empty columns
            if len(row) < len(columns):
                row += [''] * (len(columns) - len(row))
            parsed_row = []
            for val in row:
                v = val.strip()
                if v == '':
                    parsed_row.append(None)
                else:
                    try:
                        parsed_row.append(int(v))
                    except ValueError:
                        try:
                            parsed_row.append(float(v))
                        except ValueError:
                            parsed_row.append(v)
            data.append({col: val for col, val in zip(columns, parsed_row)})
    df = pd.DataFrame(data, columns=columns)
    return metadata, df

def read_imu_data(filepath):
    """
    Reads IMU data from a custom-formatted file.
    Ignores the 'auto_time' column.
    Returns:
        data: list of dicts, each representing a row of IMU data with keys:
              'frame', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'
    """
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Skip header lines (first 3 lines)
    for line in lines[3:]:
        if not line.strip():
            continue
        parts = line.strip().split()
        if len(parts) < 7:
            continue
        # parts[0]: auto_time (ignored)
        # parts[1]: frame (int)
        # parts[2]: unknown (ignored)
        # parts[3:6]: accel_x, accel_y, accel_z (float)
        # parts[6:9]: gyro_x, gyro_y, gyro_z (float)
        data.append({
            'frame': int(parts[1]),
            'accel_x': float(parts[3]),
            'accel_y': float(parts[4]),
            'accel_z': float(parts[5]),
            'gyro_x': float(parts[6]),
            'gyro_y': float(parts[7]),
            'gyro_z': float(parts[8]),
        })
    return data

# Example usage:
# import os
# from pathlib import Path
# metadata, df = read_custom_tsv(Path(__file__).parent / 'data' / 'Ele0001' / 'Ele0001_sample1_smooth_RArm.tsv')
# print("Metadata:", metadata)
# print("Data:", df.head(2))  # Print first two rows of data

