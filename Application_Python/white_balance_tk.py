import tkinter as tk
from tkinter import filedialog
import vlc

class MediaPlayer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Media Player")

        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()

        self.setup_ui()

    def setup_ui(self):
        self.menu_bar = tk.Menu(self)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open File", command=self.open_file)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        self.config(menu=self.menu_bar)

        self.play_button = tk.Button(self, text="Play", command=self.play_pause)
        self.play_button.pack()

        self.time_label = tk.Label(self, text="00:00")
        self.time_label.pack()

        self.seek_bar = tk.Scale(self, from_=0, to=100, orient=tk.HORIZONTAL, command=self.seek)
        self.seek_bar.pack(fill=tk.X)

        self.update_time()

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            media = self.instance.media_new(file_path)
            self.player.set_media(media)
            self.play_pause()

    def play_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.play_button.config(text="Play")
        else:
            self.player.play()
            self.play_button.config(text="Pause")

    def seek(self, value):
        seek_time = int(int(value) * self.player.get_length() / 1000)
        self.player.set_time(seek_time)

    def update_time(self):
        current_time = self.player.get_time() / 1000
        duration = self.player.get_length() / 1000
        self.time_label.config(text="{:02d}:{:02d}".format(int(current_time // 60), int(current_time % 60)))
        self.seek_bar.set(current_time / duration * 100)
        self.after(1000, self.update_time)

if __name__ == "__main__":
    app = MediaPlayer()
    app.mainloop()
