from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPalette, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl, QThread, QObject, pyqtSignal
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
file_list = []
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

        file_hint_label = QLabel("Select the directory with your timelapse files (Currently only .ARW files are supported):")
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
        self.start_combobox.clear()
        self.end_combobox.clear()

        global directory, file_list
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", "")
        self.file_label.setText(directory)
        
        # validate folder
        min_number, max_number, file_list = find_numbered_files(directory)
        if min_number is None or max_number is None or len(file_list) == 0:
            self.file_label.setText("Directory does not contain a series of .ARW files. Please pick another one.")
            return False

        # populate comboboxes
        self.start_combobox.addItems(file_list)
        self.end_combobox.addItems(file_list)
        self.end_combobox.setCurrentIndex(self.end_combobox.count() - 1)

        # set up images
        self.update_images(0, file_list[0])
        self.update_images(1, file_list[-1])

    def update_images(self, index, text):
        global directory
        with rawpy.imread(os.path.join(directory, text)) as raw:
            raw = raw.extract_thumb()
            image = Image.open(io.BytesIO(raw.data))
            image = QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888)
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

        self.loading_window = LoadingWindow(self)
        self.loading_window.show()

       # Start the process in a separate thread
        self.process_thread = QThread()
        self.process_worker = ProcessWorker()
        self.process_worker.moveToThread(self.process_thread)
        self.process_thread.started.connect(self.process_worker.execute_code)
        self.process_worker.output_ready.connect(self.loading_window.set_output)
        self.process_worker.finished.connect(self.on_process_finished)
        self.process_thread.start()

    def on_process_finished(self):
        self.process_thread.quit()
        self.loading_window.close()

        self.accept() 

class ProcessWorker(QObject):
    output_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def execute_code(self):
        # Define the maximum dimensions for resizing
        max_width = 1200
        max_height = 800

        global wb_values
        new_dir = pathlib.Path(os.path.join(directory, 'proxy'))
        new_dir.mkdir(parents=True, exist_ok=True)

        for i in range(0, len(file_list)):

            if not os.path.exists(os.path.join(directory, file_list[i])):
                self.output_ready.emit(f"Input file {os.path.join(directory, file_list[i])} not found. Skipping.")
                print(f"Input file {os.path.join(directory, file_list[i])} not found. Skipping.")
                continue
            
            raw = rawpy.imread(os.path.join(directory, file_list[i]))
            wb_values.append(raw.camera_whitebalance)

            if os.path.exists(f"{os.path.join(directory, 'proxy', f'{i}.jpg')}"):
                self.output_ready.emit(f"Skipping {os.path.join(directory, 'proxy', f'{i}.jpg')}. File already exists.")
                print(f"Skipping {os.path.join(directory, 'proxy', f'{i}.jpg')}. File already exists.")
                continue
                        
            raw = raw.extract_thumb() # Use the jpeg thumbnail within the raw file - saves processing time.
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

            self.output_ready.emit(f"Image {file_list[i]} saved as JPEG.")
            print(f"Image {file_list[i]} saved as JPEG.")
            
        self.output_ready.emit("Starting ffmpeg...")
        print("Starting ffmpeg...")

        # ffmpeg command
        ffmpeg_command = [
            "ffmpeg",   
            "-framerate", "30",
            "-n", "-i", f"{os.path.join(directory, 'proxy', '%d.jpg')}",
            f"{os.path.join(directory, 'proxy', 'proxy.mp4')}"
        ]
        subprocess.run(ffmpeg_command)
        
        # Emit signal to indicate that the process is finished
        self.finished.emit()

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

        self.left_keyframe = 0
        self.right_keyframe = len(wb_values) - 1

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

        self.export_button.clicked.connect(self.save_video)

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

    def save_video(self):
        self.loading_window = LoadingWindow(self)
        self.loading_window.show()

       # Start the process in a separate thread
        self.process_thread = QThread()
        self.process_worker = ProcessWorker2()
        self.process_worker.moveToThread(self.process_thread)
        self.process_thread.started.connect(self.process_worker.execute_code)
        self.process_worker.output_ready.connect(self.loading_window.set_output)
        self.process_worker.finished.connect(self.on_process_finished)
        self.process_thread.start()

    def on_process_finished(self):
        self.process_thread.quit()
        self.loading_window.close()
        self.accept() 

class LoadingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading")
        self.setGeometry(100, 100, 400, 300)
        
        layout = QVBoxLayout()

        # Loading label
        self.loading_label = QLabel("Generating Proxy Media...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)

        # Text box to display output
        self.output_textbox = QTextEdit(self)
        self.output_textbox.setReadOnly(True)
        layout.addWidget(self.output_textbox)

        self.setLayout(layout)
        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

    def set_output(self, output):
        self.output_textbox.append(output)

    def closeEvent(self, event):
        self.hide()

class ProcessWorker2(QObject):
    output_ready = pyqtSignal(str)
    finished = pyqtSignal()

    def execute_code(self):

        counter = 0
        for file in file_list:
            raw = rawpy.imread(os.path.join(directory, file))

            rgb = raw.postprocess(
                user_wb = wb_values[counter],  # Use the camera's white balance settings
                output_color=rawpy.ColorSpace.sRGB,  # Output in sRGB color space
                gamma=(2.222, 4.5),  # gamma correction
                no_auto_bright=False,  # automatically adjust brightness
                output_bps=8,  # 8 bits per channel (standard for JPEG)
                demosaic_algorithm=rawpy.DemosaicAlgorithm.LINEAR,  # Simple demosaicing
            )

            # Save the processed image as JPEG
            pil_image = Image.fromarray(rgb)
            pil_image.save(os.path.join(directory, "proxy", f"{counter}-final.jpg"))
            self.output_ready.emit(f"Image {file_list[counter]} saved as JPEG.")
            print(f"Image {file_list[counter]} saved as JPEG.")

            counter += 1
        
        self.output_ready.emit("Starting ffmpeg...")
        print("Starting ffmpeg...")

        # ffmpeg command
        ffmpeg_command = [
            "ffmpeg",   
            "-framerate", "30",
            "-y", "-i", f"{os.path.join(directory, 'proxy', '%d-final.jpg')}",
            f"{os.path.join(directory, 'output.mp4')}"
        ]
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            self.process_worker.output_ready.emit(line.strip())
        process.wait()
        self.finished.emit()

app = QApplication(sys.argv)

# Step 1: Directory dialog
file_selection_window = file_selection_window()
if file_selection_window.exec() == QDialog.Accepted:

    # Step 2: Main interface
    main_window = main_window()
    main_window.show()
    sys.exit(app.exec())