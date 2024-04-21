from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout,\
      QStyle, QSlider, QFileDialog, QLabel, QDialog, QComboBox
from PyQt5.QtGui import QPalette, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl
from functools import partial
import sys

from gen_colour_palette import *
from gen_white_balance_data import *
from helper import *

class file_selection_window(QDialog):
    def __init__(self):
        super().__init__()
        self.setGeometry(350,100, 700,500)
        self.move(QApplication.desktop().screen().rect().center()- self.rect().center())
        self.setWindowTitle("File Selection")

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        self.directory = ""

        file_hint_label = QLabel("Select the directory with your timelapse files:")
        self.file_label = QLabel("")
        start_label = QLabel("Starting frame:")
        end_label = QLabel("Ending frame:")

        # self.file_label.setAlignment(Qt.AlignLeft)
        # start_label.setAlignment(Qt.AlignLeft)
        # end_label.setAlignment(Qt.AlignLeft) 

        directory_button = QPushButton("Open Folder...")
        directory_button.clicked.connect(self.open_folder)
        next_button = QPushButton("Next")
        next_button.clicked.connect(self.check_validity)

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
        self.directory = QFileDialog.getExistingDirectory(self, "Select Directory", "")
        self.file_label.setText(self.directory)
        
        # validate folder
        min_number, max_number, file_list = find_numbered_files(self.directory)
        if min_number is None or max_number is None:
            return False

        # populate comboboxes
        self.start_combobox.clear
        self.start_combobox.addItems(file_list)
        self.end_combobox.clear
        self.end_combobox.addItems(file_list)
        self.end_combobox.setCurrentIndex(self.end_combobox.count() - 1)

        # set up images
        start_pixmap = QPixmap(self.directory + '/' + file_list[0])
        start_pixmap = start_pixmap.scaled(300, 200, Qt.KeepAspectRatio)
        end_pixmap = QPixmap(self.directory + '/' + file_list[-1])
        end_pixmap = end_pixmap.scaled(300, 200, Qt.KeepAspectRatio)
        self.start_image.setPixmap(start_pixmap)
        self.end_image.setPixmap(end_pixmap)

    def update_images(self, index, text):
        pixmap = QPixmap(self.directory + '/' + text)
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

        # If all is good,
        # TODO: Generate proxy video file

        
        self.accept()

class main_window(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(350,100, 700,500)
        self.move(QApplication.desktop().screen().rect().center()- self.rect().center())
        self.setWindowTitle("Timelapse Whitebalance Correction")

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        self.create_player()

    def create_player(self):

        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        videoWidget = QVideoWidget()

        self.openButton = QPushButton("Open File...")
        self.openButton.clicked.connect(self.open_file)

        self.playButton = QPushButton()
        self.playButton.setEnabled(False)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.clicked.connect(self.play_video)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0,0)
        self.slider.sliderMoved.connect(self.set_position)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)

        hbox.addWidget(self.openButton)
        hbox.addWidget(self.playButton)
        hbox.addWidget(self.slider)
        # TODO: Add bar graph of white balance

        vbox = QVBoxLayout()
        vbox.addWidget(videoWidget)
        vbox.addLayout(hbox)

        self.mediaPlayer.setVideoOutput(videoWidget)

        self.setLayout(vbox)
        
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open Video")

        if filename != '':
            self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
            self.playButton.setEnabled(True)
            generate_palette(filename)
            # TODO: Generate bar graph for whitebalance changes

    def play_video(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        else:
            self.mediaPlayer.play()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def position_changed(self, position):
        self.slider.setValue(position)

    def duration_changed(self, duration):
        self.slider.setRange(0, duration)

    def set_position(self, position):
        self.mediaPlayer.setPosition(position)

app = QApplication(sys.argv)

# Step 1: Directory dialog
file_selection_window = file_selection_window()
if file_selection_window.exec() == QDialog.Accepted:
    # TODO: Step2: Pre-process files


    # Step 3: Main interface
    main_window = main_window()
    main_window.show()
    sys.exit(app.exec())