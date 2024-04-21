import cv2
from PyQt5.QtGui import QPalette, QImage, QPixmap

# TODO: return plot of pixel color changes
def generate_palette(video_path, x=0, y=0):
    cap = cv2.VideoCapture(video_path)
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    colors = []

    for i in range(frames):
        # Read frame
        ret, frames = cap.read()
        if not ret:
            print("Error reading frames from video.")
            return

        # Convert frames from BGR to RGB
        frames_rgb = cv2.cvtColor(frames, cv2.COLOR_BGR2RGB)
        colors.append(frames_rgb[y, x])
        
    cap.release()