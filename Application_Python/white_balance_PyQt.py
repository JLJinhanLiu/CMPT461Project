from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout,\
      QStyle, QSlider, QFileDialog, QLabel, QDialog, QComboBox, QSizePolicy
from PyQt5.QtGui import QPalette, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl
from functools import partial
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import rawpy
from PIL import Image
import sys
import pathlib
from multiprocessing import Pool, cpu_count
import concurrent.futures
import subprocess
import io

from gen_colour_palette import *
from helper import *

directory = ""
wb_values = []

class file_selection_window(QDialog):
    def __init__(self):
        super().__init__()
        self.setGeometry(350,100, 700,500)
        self.move(QApplication.desktop().screen().rect().center()- self.rect().center())
        self.setWindowTitle("File Selection")

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        file_hint_label = QLabel("Select the directory with your timelapse files:")
        self.file_label = QLabel("")
        start_label = QLabel("Starting frame:")
        end_label = QLabel("Ending frame:")
        file_hint_label.setMaximumHeight(30)
        self.file_label.setMaximumHeight(30)
        start_label.setMaximumHeight(30)
        end_label.setMaximumHeight(30)

        directory_button = QPushButton("Open Folder...")
        directory_button.clicked.connect(self.open_folder)
        next_button = QPushButton("Next")
        next_button.clicked.connect(self.check_validity)
        directory_button.setMaximumWidth(150)

        self.start_image = QLabel()
        self.end_image = QLabel()

        self.start_combobox = QComboBox()
        self.end_combobox = QComboBox()
        self.start_combobox.setEnabled(False)
        self.end_combobox.setEnabled(False)
        self.start_combobox.currentTextChanged.connect(partial(self.update_images, 0))
        self.end_combobox.currentTextChanged.connect(partial(self.update_images, 1))

        hbox_file_picker = QHBoxLayout()
        hbox_start_row = QHBoxLayout()
        hbox_end_row = QHBoxLayout()

        hbox_file_picker.setContentsMargins(0,0,0,0)        
        hbox_start_row.setContentsMargins(0,0,0,0)
        hbox_end_row.setContentsMargins(0,0,0,0)

        hbox_file_picker.addWidget(directory_button)
        hbox_file_picker.addWidget(self.file_label)
        hbox_start_row.addWidget(self.start_image)
        hbox_start_row.addWidget(self.start_combobox)
        hbox_end_row.addWidget(self.end_image)
        hbox_end_row.addWidget(self.end_combobox)

        vbox = QVBoxLayout()
        vbox.addWidget(file_hint_label)
        vbox.addLayout(hbox_file_picker)
        vbox.addWidget(start_label)
        vbox.addLayout(hbox_start_row)
        vbox.addWidget(end_label)
        vbox.addLayout(hbox_end_row)
        vbox.addWidget(next_button)

        self.setLayout(vbox)

    def open_folder(self):
        global directory 
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", "")
        self.file_label.setText(directory)
        
        # validate folder
        min_number, max_number, self.file_list = find_numbered_files(directory)
        if min_number is None or max_number is None:
            return False

        # populate comboboxes
        self.start_combobox.clear()
        self.start_combobox.addItems(self.file_list)
        self.end_combobox.clear()
        self.end_combobox.addItems(self.file_list)
        self.end_combobox.setCurrentIndex(self.end_combobox.count() - 1)

        # set up images
        self.update_images(0, self.file_list[0])
        self.update_images(1, self.file_list[-1])

    def update_images(self, index, text):
        # TODO: Add progress indicator
        global directory
        print(directory + '/' + text)
        with rawpy.imread(directory + '/' + text) as raw:
            rgb = raw.postprocess()
            h, w, ch = rgb.shape
            bytesPerLine = ch * w
            buf = bytes(rgb.data)
            image = QImage(buf, w, h, bytesPerLine, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
        
        pixmap = pixmap.scaled(300, 200, Qt.KeepAspectRatio)

        if index == 0:
            self.start_image.setPixmap(pixmap)
            self.start_combobox.setEnabled(True)
        else:
            self.end_image.setPixmap(pixmap)
            self.end_combobox.setEnabled(True)

    def check_validity(self):
        # TODO: Check if file sequence follows logical order
        # aka start < end

        # Define the maximum dimensions for resizing
        max_width = 1200
        max_height = 800

        global wb_values
        new_dir = pathlib.Path(os.path.join(directory, 'proxy'))
        new_dir.mkdir(parents=True, exist_ok=True)

        for i in range(0, len(self.file_list)):

            if not os.path.exists(os.path.join(directory, self.file_list[i])):
                print(f"Input file {os.path.join(directory, self.file_list[i])} not found. Skipping.")
                continue
            
            raw = rawpy.imread(os.path.join(directory, self.file_list[i]))
            wb_values.append(raw.camera_whitebalance)

            if os.path.exists(f"{os.path.join(directory, 'proxy', f'{i}.jpg')}"):
                print(f"Skipping {os.path.join(directory, 'proxy', f'{i}.jpg')}. File already exists.")
                continue
                        
            raw = raw.extract_thumb()
            image = Image.open(io.BytesIO(raw.data))

            # Calculate new dimensions while preserving aspect ratio
            width, height = image.size

            if width > max_width:
                new_width = max_width
                new_height = int(height * (max_width / width))
                new_height -= new_height % 2
                height = new_height 
                width = new_width
            if height > max_height:
                new_height = max_height
                new_width = int(width * (max_height / height))
                new_width -= new_width % 2
                height = new_height
                width = new_width

            image = image.resize((new_width, new_height))
            image.save(f"{os.path.join(directory, 'proxy', f'{i}.jpg')}", quality=70)

            print(f"Image {self.file_list[i]} saved as JPEG.")

        print("Starting ffmpeg...")

        # ffmpeg command
        ffmpeg_command = [
            "ffmpeg",   
            "-framerate", "30",
            "-n", "-i", f"{os.path.join(directory, 'proxy', '%d.jpg')}",
            f"{os.path.join(directory, 'proxy', 'proxy.mp4')}"
        ]
        subprocess.run(ffmpeg_command)

        self.accept() 


class main_window(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(350,100, 1300,800)
        self.move(QApplication.desktop().screen().rect().center()- self.rect().center())
        self.setWindowTitle("Timelapse Whitebalance Correction")

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        self.create_player()
        filename = os.path.join(directory, "proxy", "proxy.mp4")
        self.original_media.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
        self.edited_media.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
        self.original_media.play()
        self.edited_media.play()
        self.playButton.setEnabled(True)

    def create_player(self):

        self.original_media = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.original_media.positionChanged.connect(self.position_changed)
        self.original_media.durationChanged.connect(self.duration_changed)
        
        self.edited_media = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        original_video = QVideoWidget()
        edited_video = QVideoWidget()

        self.original_media.setVideoOutput(original_video)
        self.edited_media.setVideoOutput(edited_video)

        original_label = QLabel("Original")
        original_label.setAlignment(Qt.AlignCenter)
        original_label.setMaximumHeight(30)
        edited_label = QLabel("Edited")
        edited_label.setAlignment(Qt.AlignCenter)
        edited_label.setMaximumHeight(30)

        self.left_keyframe_button = QPushButton("Set Left Keyframe")
        self.right_keyframe_button = QPushButton("Set Right Keyframe")
        self.export_button = QPushButton("Export")
        # TODO: link buttons 

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.playButton.clicked.connect(self.play_video)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.sliderMoved.connect(self.set_position)

        self.left_keyframe_slider = QSlider(Qt.Vertical)
        self.right_keyframe_slider = QSlider(Qt.Vertical)
        self.left_keyframe_slider.setMaximumHeight(120)
        self.right_keyframe_slider.setMaximumHeight(120)


        # Create the Matplotlib widget
        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self.plot_line_graph()

        labels_hbox = QHBoxLayout()
        medias_hbox = QHBoxLayout()
        keyframes_hbox = QHBoxLayout()
        graph_hbox = QHBoxLayout()
        controls_hbox = QHBoxLayout()

        labels_hbox.addWidget(original_label)
        labels_hbox.addWidget(edited_label)
        medias_hbox.addWidget(original_video)
        medias_hbox.addWidget(edited_video)
        keyframes_hbox.addWidget(self.left_keyframe_button)
        keyframes_hbox.addWidget(self.right_keyframe_button)
        graph_hbox.addWidget(self.left_keyframe_slider)
        graph_hbox.addWidget(self.right_keyframe_slider)
        graph_hbox.addWidget(self.canvas)
        controls_hbox.addWidget(self.playButton)
        controls_hbox.addWidget(self.seek_slider)

        vbox = QVBoxLayout()
        vbox.addLayout(labels_hbox)
        vbox.addLayout(medias_hbox)
        vbox.addLayout(keyframes_hbox)
        vbox.addLayout(controls_hbox)
        vbox.addLayout(graph_hbox)
        vbox.addWidget(self.export_button)
        self.setLayout(vbox)

    def play_video(self):
        if self.original_media.state() == QMediaPlayer.PlayingState:
            self.original_media.pause()
            self.edited_media.pause()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.original_media.play()
            self.edited_media.play()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def position_changed(self, position):
        self.seek_slider.setValue(position)
        self.update_seek_bar(position)

    def duration_changed(self, duration):
        self.seek_slider.setRange(0, duration)

    def set_position(self, position):
        self.original_media.setPosition(position)
        self.edited_media.setPosition(position)
        self.update_seek_bar(position)

    def plot_line_graph(self):
        self.ax = self.canvas.figure.add_subplot(111)
        self.ax.set_facecolor('black')
        self.canvas.figure.set_facecolor('black')

        # Plot the data
        self.ax.plot(wb_values, '-', color='white')  
        self.seekline = self.ax.axvline(0, color='red')  
        self.canvas.draw_idle()

    def update_seek_bar(self, position = 0):
        self.seekline.set_xdata(int(position / self.seek_slider.maximum() * len(wb_values)))
        self.canvas.draw_idle()


# Writing a list to a file
def write_list_to_file(file_path, my_list):
    with open(file_path, 'w') as file:
        for item in my_list:
            file.write(str(item) + '\n')

# Reading a list from a file
def read_list_from_file(file_path):
    with open(file_path, 'r') as file:
        my_list = file.readlines()
        my_list = [item.strip() for item in my_list]
    return my_list

app = QApplication(sys.argv)

# Step 1: Directory dialog
file_selection_window = file_selection_window()
if file_selection_window.exec() == QDialog.Accepted:

    # write_list_to_file(os.path.join(directory, "proxy", "wb.txt"), wb_values)
    # wb_values = read_list_from_file(os.path.join(directory, "proxy", "wb.txt"))
    # Step 2: Main interface
    main_window = main_window()
    main_window.show()
    sys.exit(app.exec())