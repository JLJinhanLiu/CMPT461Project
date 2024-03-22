import rawpy
from PIL import Image

img_start = 3374
img_end = 3752

raw = rawpy.imread(f'data/DSC0{img_start}.ARW')
user_wbv = raw.camera_whitebalance

output_path = "output/"

# Open a raw image file
for i in range(img_start, img_end+1):
    raw = rawpy.imread(f'data/DSC0{i}.ARW')
    exif_data = raw.camera_whitebalance
    print("EXIF Data:", exif_data)

    # Process the raw image with the manual white balance
    rgb = raw.postprocess(user_wb=user_wbv)

    image = Image.fromarray(rgb)

    image.save(f'{output_path}{i}.jpg')

    print("Image saved as JPEG successfully.")