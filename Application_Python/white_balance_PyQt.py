from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout,\
      QStyle, QSlider, QFileDialog
from PyQt5.QtGui import QPalette
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl
import sys
from gen_colour_palette import *

class window(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(350,100, 700,500)
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
window = window()
window.show()
sys.exit(app.exec_())