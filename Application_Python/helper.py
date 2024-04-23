import os
import re

def find_numbered_files(directory):
    try:
        files = os.listdir(directory)
    except FileNotFoundError:
        return None, None, None
    
    min_number = float('inf')
    max_number = float('-inf')
    file_list = []
    
    # Regular expression pattern to match numeric parts of filenames
    pattern = re.compile(r'\d+')
    
    for filename in files:
        matches = pattern.findall(filename)
        
        if matches:
            file_list.append(filename)
            number = int(matches[-1])  # Assuming the last numeric part is the sequence number
            
            min_number = min(min_number, number)
            max_number = max(max_number, number)
    
    if min_number == float('inf') or max_number == float('-inf'):
        print("No numbered files found in the directory.")
        return None, None, None
    
    filtered_filenames = [filename for filename in file_list if filename.endswith(".ARW")]
    
    return min_number, max_number, sorted(filtered_filenames)