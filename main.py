import sys
import os
import subprocess
import yt_dlp

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)


# =========================================================
# RESOURCE PATH
# Works in normal Python mode and PyInstaller --onefile mode
# =========================================================

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


# =========================================================
# DOWNLOAD WORKER
# =========================================================

class DownloadWorker(QThread):

    progress = Signal(int)
    status = Signal(str)
    finished_success = Signal()
    failed = Signal(str)

    def __init__(
        self,
        url,
        download_type,
        quality,
        save_folder,
        ffmpeg_path
    ):
        super().__init__()

        self.url = url
        self.download_type = download_type
        self.quality = quality
        self.save_folder = save_folder
        self.ffmpeg_path = ffmpeg_path

    def progress_hook(self, data):

        if data["status"] == "downloading":

            downloaded = data.get(
                "downloaded_bytes",
                0
            )

            total = (
                data.get("total_bytes")
                or data.get("total_bytes_estimate")
            )

            if total:

                percent = int(
                    downloaded / total * 100
                )

                self.progress.emit(percent)

            speed = data.get("speed")
            eta = data.get("eta")

            status_text = "Downloading..."

            if speed:

                speed_mb = speed / 1024 / 1024

                status_text += (
                    f"  {speed_mb:.2f} MB/s"
                )

            if eta is not None:

                minutes = eta // 60
                seconds = eta % 60

                if minutes > 0:
                    status_text += (
                        f"  ETA: {minutes}m {seconds}s"
                    )
                else:
                    status_text += (
                        f"  ETA: {seconds}s"
                    )

            self.status.emit(status_text)

        elif data["status"] == "finished":

            self.progress.emit(100)

            self.status.emit(
                "Download finished. Processing..."
            )

    def run(self):

        try:

            # =================================================
            # MP3 AUDIO MODE
            # =================================================

            if self.download_type == "MP3 Audio":

                bitrate = self.quality.replace(
                    " kbps",
                    ""
                )

                ydl_opts = {

                    "format":
                        "bestaudio/best",

                    "outtmpl":
                        os.path.join(
                            self.save_folder,
                            "%(title)s.%(ext)s"
                        ),

                    "ffmpeg_location":
                        self.ffmpeg_path,

                    "noplaylist":
                        True,

                    "progress_hooks": [
                        self.progress_hook
                    ],

                    "postprocessors": [
                        {
                            "key":
                                "FFmpegExtractAudio",

                            "preferredcodec":
                                "mp3",

                            "preferredquality":
                                bitrate,
                        }
                    ],
                }

            # =================================================
            # MP4 VIDEO MODE
            # =================================================

            else:

                if self.quality == "1080p":

                    video_format = (
                        "bestvideo[height<=1080]+"
                        "bestaudio/"
                        "best[height<=1080]"
                    )

                elif self.quality == "720p":

                    video_format = (
                        "bestvideo[height<=720]+"
                        "bestaudio/"
                        "best[height<=720]"
                    )

                elif self.quality == "480p":

                    video_format = (
                        "bestvideo[height<=480]+"
                        "bestaudio/"
                        "best[height<=480]"
                    )

                else:

                    video_format = (
                        "bestvideo+bestaudio/best"
                    )

                ydl_opts = {

                    "format":
                        video_format,

                    "outtmpl":
                        os.path.join(
                            self.save_folder,
                            "%(title)s.%(ext)s"
                        ),

                    "merge_output_format":
                        "mp4",

                    "ffmpeg_location":
                        self.ffmpeg_path,

                    "noplaylist":
                        True,

                    "progress_hooks": [
                        self.progress_hook
                    ],
                }

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                ydl.download(
                    [self.url]
                )

            self.finished_success.emit()

        except Exception as error:

            self.failed.emit(
                str(error)
            )


# =========================================================
# MAIN WINDOW
# =========================================================

class MainWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.download_folder = os.path.join(
            os.path.expanduser("~"),
            "Downloads"
        )

        self.worker = None

        self.setWindowTitle(
            "ClipForge"
        )

        self.resize(
            700,
            540
        )

        self.create_ui()

    def create_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setSpacing(12)

        # =====================================================
        # TITLE
        # =====================================================

        title = QLabel(
            "ClipForge"
        )

        title.setStyleSheet(
            """
            font-size: 30px;
            font-weight: bold;
            """
        )

        main_layout.addWidget(
            title
        )

        subtitle = QLabel(
            "Video & Audio Downloader"
        )

        subtitle.setStyleSheet(
            """
            font-size: 14px;
            """
        )

        main_layout.addWidget(
            subtitle
        )

        # =====================================================
        # URL
        # =====================================================

        url_label = QLabel(
            "Video URL"
        )

        main_layout.addWidget(
            url_label
        )

        url_layout = QHBoxLayout()

        self.url_input = QLineEdit()

        self.url_input.setPlaceholderText(
            "Paste video URL here..."
        )

        paste_button = QPushButton(
            "Paste"
        )

        clear_button = QPushButton(
            "Clear"
        )

        paste_button.clicked.connect(
            self.paste_url
        )

        clear_button.clicked.connect(
            self.clear_url
        )

        url_layout.addWidget(
            self.url_input
        )

        url_layout.addWidget(
            paste_button
        )

        url_layout.addWidget(
            clear_button
        )

        main_layout.addLayout(
            url_layout
        )

        # =====================================================
        # DOWNLOAD TYPE
        # =====================================================

        type_label = QLabel(
            "Download As"
        )

        self.type_combo = QComboBox()

        self.type_combo.addItems([
            "MP4 Video",
            "MP3 Audio"
        ])

        self.type_combo.currentTextChanged.connect(
            self.update_quality_options
        )

        main_layout.addWidget(
            type_label
        )

        main_layout.addWidget(
            self.type_combo
        )

        # =====================================================
        # QUALITY
        # =====================================================

        quality_label = QLabel(
            "Quality"
        )

        self.quality_combo = QComboBox()

        main_layout.addWidget(
            quality_label
        )

        main_layout.addWidget(
            self.quality_combo
        )

        self.update_quality_options()

        # =====================================================
        # SAVE LOCATION
        # =====================================================

        folder_label = QLabel(
            "Save Location"
        )

        main_layout.addWidget(
            folder_label
        )

        folder_layout = QHBoxLayout()

        self.folder_input = QLineEdit()

        self.folder_input.setText(
            self.download_folder
        )

        self.folder_input.setReadOnly(
            True
        )

        browse_button = QPushButton(
            "Browse"
        )

        browse_button.clicked.connect(
            self.choose_folder
        )

        folder_layout.addWidget(
            self.folder_input
        )

        folder_layout.addWidget(
            browse_button
        )

        main_layout.addLayout(
            folder_layout
        )

        # =====================================================
        # DOWNLOAD BUTTON
        # =====================================================

        self.download_button = QPushButton(
            "Download"
        )

        self.download_button.setMinimumHeight(
            50
        )

        self.download_button.setStyleSheet(
            """
            font-size: 16px;
            font-weight: bold;
            """
        )

        self.download_button.clicked.connect(
            self.start_download
        )

        main_layout.addWidget(
            self.download_button
        )

        # =====================================================
        # PROGRESS BAR
        # =====================================================

        self.progress_bar = QProgressBar()

        self.progress_bar.setValue(
            0
        )

        main_layout.addWidget(
            self.progress_bar
        )

        # =====================================================
        # STATUS
        # =====================================================

        self.status_label = QLabel(
            "Ready"
        )

        main_layout.addWidget(
            self.status_label
        )

        # =====================================================
        # BOTTOM BUTTONS
        # =====================================================

        bottom_layout = QHBoxLayout()

        self.open_folder_button = QPushButton(
            "Open Download Folder"
        )

        self.open_folder_button.clicked.connect(
            self.open_download_folder
        )

        about_button = QPushButton(
            "About ClipForge"
        )

        about_button.clicked.connect(
            self.show_about
        )

        bottom_layout.addWidget(
            self.open_folder_button
        )

        bottom_layout.addWidget(
            about_button
        )

        main_layout.addLayout(
            bottom_layout
        )

        self.setLayout(
            main_layout
        )

    # =========================================================
    # QUALITY OPTIONS
    # =========================================================

    def update_quality_options(self):

        self.quality_combo.clear()

        if self.type_combo.currentText() == "MP3 Audio":

            self.quality_combo.addItems([
                "320 kbps",
                "256 kbps",
                "192 kbps",
                "128 kbps"
            ])

        else:

            self.quality_combo.addItems([
                "Best",
                "1080p",
                "720p",
                "480p"
            ])

    # =========================================================
    # PASTE
    # =========================================================

    def paste_url(self):

        clipboard = QApplication.clipboard()

        self.url_input.setText(
            clipboard.text().strip()
        )

    # =========================================================
    # CLEAR
    # =========================================================

    def clear_url(self):

        self.url_input.clear()

        self.progress_bar.setValue(
            0
        )

        self.status_label.setText(
            "Ready"
        )

    # =========================================================
    # CHOOSE FOLDER
    # =========================================================

    def choose_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Download Folder"
        )

        if folder:

            self.download_folder = folder

            self.folder_input.setText(
                folder
            )

    # =========================================================
    # OPEN DOWNLOAD FOLDER
    # =========================================================

    def open_download_folder(self):

        if os.path.exists(
            self.download_folder
        ):

            subprocess.Popen(
                [
                    "explorer",
                    self.download_folder
                ]
            )

    # =========================================================
    # ABOUT
    # =========================================================

    def show_about(self):

        QMessageBox.about(
            self,
            "About ClipForge",
            """
            <div style="text-align:center;">

            <h2>ClipForge</h2>

            <p>
            <b>Video & Audio Downloader</b>
            </p>

            <p>
            Version 1.0.0
            </p>

            <hr>

            <p>
            <b>Developed by</b><br>
            Sudeera Dilhan Fernando
            </p>

            <p>
            <b>Country:</b> Sri Lanka<br>
            <b>Release Date:</b> 1 October 2026
            </p>

            <hr>

            <p>
            Built with Python, PySide6,<br>
            yt-dlp and FFmpeg.
            </p>

            <p>
            ClipForge is designed to download
            permitted video content and extract
            audio into MP3 format through a
            simple Windows desktop interface.
            </p>

            <p>
            Please use ClipForge only for content
            you own, have permission to download,
            or are otherwise legally permitted to use.
            </p>

            <p>
            © 2026 Sudeera Dilhan Fernando
            </p>

            </div>
            """
        )

    # =========================================================
    # START DOWNLOAD
    # =========================================================

    def start_download(self):

        url = self.url_input.text().strip()

        if not url:

            QMessageBox.warning(
                self,
                "Missing URL",
                "Please paste a video URL."
            )

            return

        download_type = (
            self.type_combo.currentText()
        )

        quality = (
            self.quality_combo.currentText()
        )

        # This now works both:
        # 1. while developing with Python
        # 2. inside a PyInstaller --onefile EXE
        ffmpeg_path = resource_path(
            "bin"
        )

        self.progress_bar.setValue(
            0
        )

        self.status_label.setText(
            "Preparing download..."
        )

        self.download_button.setEnabled(
            False
        )

        self.worker = DownloadWorker(
            url,
            download_type,
            quality,
            self.download_folder,
            ffmpeg_path
        )

        self.worker.progress.connect(
            self.update_progress
        )

        self.worker.status.connect(
            self.update_status
        )

        self.worker.finished_success.connect(
            self.download_finished
        )

        self.worker.failed.connect(
            self.download_failed
        )

        self.worker.start()

    # =========================================================
    # UPDATE PROGRESS
    # =========================================================

    def update_progress(
        self,
        value
    ):

        self.progress_bar.setValue(
            value
        )

    # =========================================================
    # UPDATE STATUS
    # =========================================================

    def update_status(
        self,
        text
    ):

        self.status_label.setText(
            text
        )

    # =========================================================
    # DOWNLOAD FINISHED
    # =========================================================

    def download_finished(self):

        self.progress_bar.setValue(
            100
        )

        self.status_label.setText(
            "Download complete!"
        )

        self.download_button.setEnabled(
            True
        )

        QMessageBox.information(
            self,
            "ClipForge",
            "Download completed successfully."
        )

    # =========================================================
    # DOWNLOAD FAILED
    # =========================================================

    def download_failed(
        self,
        error
    ):

        self.status_label.setText(
            "Download failed"
        )

        self.download_button.setEnabled(
            True
        )

        QMessageBox.critical(
            self,
            "ClipForge - Download Error",
            error
        )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "ClipForge"
    )

    app.setApplicationVersion(
        "1.0.0"
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )