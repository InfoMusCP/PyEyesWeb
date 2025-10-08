import sys, os

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pyeyesweb.utils.tsv_reader import TSVReader

current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "..", "resources", "QualisysTSVExample.tsv")

reader = TSVReader()
reader._set_file_name(file_path);

headers = reader.headers
print(headers)

#READ FILE USING TIME AS INPUT
reader.reset()
row = reader(time_value=1.677)
values = [f"{headers[i]}: {row[i]}" for i in range(len(headers))]
print(" | ".join(values))

#READ FILE USING BLOCK SIZE
reader.reset()
reader._set_block_size(10)
for row in reader():
    values = [f"{headers[i]}: {row[i]}" for i in range(len(headers))]
    print(" | ".join(values))


#READ FILE USING TIME COLUMN AND SPEED FACTOR=1
reader._set_use_time_and_speed(1)
reader.reset()
for row in reader():
    values = [f"{headers[i]}: {row[i]}" for i in range(len(headers))]
    print(" | ".join(values))
