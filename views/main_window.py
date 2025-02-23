from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLineEdit, QPushButton, 
                                QProgressBar, QLabel, QMessageBox,
                                QMenuBar, QMenu)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot
import os
from views.file_list_widget import FileTreeWidget
from views.login_dialog import LoginDialog
from utils.network import NetworkManager
from utils.downloader import DownloadManager
from utils.config import ConfigManager
import base64

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.network = NetworkManager()
        self.downloader = DownloadManager()
        self.setup_ui()
        self.setup_connections()
        self.current_url = ""
        
        # Try to restore base URL
        base_url = self.config.get_base_url()
        if base_url:
            self.address_bar.setText(base_url)

    def setup_ui(self):
        self.setWindowTitle("File Explorer Client")
        self.setMinimumSize(800, 600)

        # Create menu bar
        self.create_menu_bar()

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create address bar
        address_layout = QHBoxLayout()
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Enter URL...")
        self.go_button = QPushButton("Go")
        address_layout.addWidget(self.address_bar)
        address_layout.addWidget(self.go_button)
        layout.addLayout(address_layout)

        # Create file list
        self.file_list = FileTreeWidget()
        layout.addWidget(self.file_list)

        # Create status bar with progress
        self.statusBar().showMessage("Ready")
        
        # Create progress bar layout
        progress_layout = QHBoxLayout()
        
        # File progress
        self.file_progress_label = QLabel("Current file:")
        self.file_progress_bar = QProgressBar()
        self.file_progress_bar.setMaximumWidth(200)
        self.file_progress_bar.hide()
        
        # Overall progress
        self.overall_progress_label = QLabel("Overall progress:")
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setMaximumWidth(200)
        self.overall_progress_bar.hide()
        
        # Add progress bars to layout
        progress_widget = QWidget()
        progress_layout.addWidget(self.file_progress_label)
        progress_layout.addWidget(self.file_progress_bar)
        progress_layout.addWidget(self.overall_progress_label)
        progress_layout.addWidget(self.overall_progress_bar)
        progress_widget.setLayout(progress_layout)
        
        self.statusBar().addPermanentWidget(progress_widget)

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        # Login action
        login_action = QAction("Login", self)
        login_action.triggered.connect(self.show_login_dialog)
        file_menu.addAction(login_action)
        
        # Logout action
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        file_menu.addAction(logout_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def setup_connections(self):
        # Connect address bar
        self.go_button.clicked.connect(self.navigate_to_url)
        self.address_bar.returnPressed.connect(self.navigate_to_url)

        # Connect file list signals
        self.file_list.navigate_requested.connect(self.handle_navigation)
        self.file_list.download_requested.connect(self.handle_download)

        # Connect downloader signals
        self.downloader.progress_updated.connect(self.update_download_progress)
        self.downloader.overall_progress_updated.connect(self.update_overall_progress)
        self.downloader.download_completed.connect(self.handle_download_completed)
        self.downloader.download_error.connect(self.handle_download_error)
        self.downloader.directory_scan_completed.connect(self.handle_directory_scan_completed)
        self.downloader.all_downloads_completed.connect(self.handle_all_downloads_completed)

    def show_login_dialog(self):
        dialog = LoginDialog(self)
        
        # Pre-fill credentials and base URL if available
        if self.config.get_auth_header():
            dialog.set_credentials(
                self.config.config.get('username', ''),
                self.config.config.get('password', ''),
                self.config.get_base_url() or self.address_bar.text().strip()
            )
            
        if dialog.exec():
            if dialog.save_credentials:
                self.network.set_credentials(
                    dialog.username, 
                    dialog.password,
                    dialog.base_url
                )
                # Update address bar with new base URL
                if dialog.base_url:
                    self.address_bar.setText(dialog.base_url)
            else:
                # Use credentials for this session only
                self.network.session.headers.update({
                    'Authorization': f'Basic {base64.b64encode(f"{dialog.username}:{dialog.password}".encode()).decode()}'
                })
                self.config.clear_credentials()

    def handle_logout(self):
        self.config.clear_credentials()
        self.network._update_auth()
        self.statusBar().showMessage("Logged out")

    @Slot()
    def navigate_to_url(self):
        url = self.address_bar.text().strip()
        if url:
            self.handle_navigation(url)

    @Slot(str)
    def handle_navigation(self, url: str):
        try:
            self.current_url = url
            self.address_bar.setText(url)
            self.statusBar().showMessage("Loading...")
            
            # Clear current view
            self.file_list.clear_and_set_path(url)
            
            # Load directory contents
            items = self.network.list_directory(url)
            
            # Add items to view
            for item in items:
                self.file_list.add_file_item(
                    name=item.name,
                    size=item.size,
                    modified=item.modified_date,
                    url=item.url,
                    is_directory=item.is_directory
                )
                
            self.statusBar().showMessage("Ready")
            
        except Exception as e:
            self.statusBar().showMessage("Error loading directory")
            if "401" in str(e):
                self.show_login_dialog()
            else:
                QMessageBox.critical(self, "Error", f"Failed to load directory: {str(e)}")

    @Slot(str, str, bool)
    def handle_download(self, url: str, save_path: str, skip_images: bool):
        try:
            # Show progress bars
            self.file_progress_bar.show()
            self.overall_progress_bar.show()
            self.file_progress_bar.setValue(0)
            self.overall_progress_bar.setValue(0)
            
            # Start download
            self.downloader.start_download_task(url, skip_images)
            
        except Exception as e:
            self.handle_download_error(save_path, str(e))

    @Slot(str, float)
    def update_download_progress(self, file_name: str, progress: float):
        self.file_progress_label.setText(f"Current file: {file_name}")
        self.file_progress_bar.setValue(int(progress))

    @Slot(float)
    def update_overall_progress(self, progress: float):
        self.overall_progress_bar.setValue(int(progress))

    @Slot(str)
    def handle_download_completed(self, file_name: str):
        self.statusBar().showMessage(f"Downloaded {file_name}")

    @Slot()
    def handle_all_downloads_completed(self):
        self.statusBar().showMessage("All downloads completed")
        self.file_progress_bar.hide()
        self.overall_progress_bar.hide()

    @Slot(str, str)
    def handle_download_error(self, file_name: str, error: str):
        self.file_progress_bar.hide()
        self.overall_progress_bar.hide()
        self.statusBar().showMessage("Download failed")
        if "401" in error:
            self.show_login_dialog()
        else:
            QMessageBox.critical(
                self, 
                "Download Error",
                f"Failed to download {file_name}: {error}"
            )

    @Slot(str, int)
    def handle_directory_scan_completed(self, directory_name: str, file_count: int):
        """Handle completion of directory scanning"""
        self.statusBar().showMessage(f"Queued {file_count} files from {directory_name} for download")

    def closeEvent(self, event):
        """Handle application closing"""
        self.downloader.stop()
        super().closeEvent(event) 