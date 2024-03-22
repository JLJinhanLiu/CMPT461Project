import cv2
import os
import numpy as np

### TODO: It currently does not flatten all white balance to certain input - but instead it is like a filter.
### we need to calculate PER IMAGE what the correct shift is.

def calculate_white_balance_coeffs(color_temperature):
    # Convert color temperature to mired scale
    mired_scale = 1000000 / color_temperature
    # Calculate white balance coefficients
    blue = (mired_scale - 2) / (mired_scale + 2)
    red = 1 - blue
    return np.array([blue, 1.0, red])

def apply_white_balance(image, white_balance_coeffs):
    # Apply white balance adjustment
    return np.clip(image * white_balance_coeffs, 0, 255).astype(np.uint8)

# Change these to desired names
# TODO: Make this a cmd line arg
input_folder = 'data'
output_video = 'output_video.mp4'
fps = 30

image_files = sorted([f for f in os.listdir(input_folder) if f.endswith('.JPG')])

frame = cv2.imread(os.path.join(input_folder, image_files[0]))
height, width, _ = frame.shape
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, fps, (width, height))

# Calculate white balance coefficients for 5000K color temperature
white_balance_coeffs = calculate_white_balance_coeffs(5000)

for image_file in image_files:
    image_path = os.path.join(input_folder, image_file)
    image = cv2.imread(image_path)
    
    # Perform white balance correction
    corrected_image = apply_white_balance(image, white_balance_coeffs)

    out.write(corrected_image)

out.release()

print("Video created successfully.")
