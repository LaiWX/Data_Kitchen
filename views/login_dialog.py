from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton,
                               QCheckBox)
from PySide6.QtCore import Qt

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.username = ""
        self.password = ""
        self.base_url = ""
        self.save_credentials = False

    def setup_ui(self):
        self.setWindowTitle("Login")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Base URL
        base_url_layout = QHBoxLayout()
        base_url_label = QLabel("Base URL:")
        self.base_url_input = QLineEdit()
        base_url_layout.addWidget(base_url_label)
        base_url_layout.addWidget(self.base_url_input)
        layout.addLayout(base_url_layout)
        
        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember credentials")
        layout.addWidget(self.remember_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
    def accept(self):
        self.username = self.username_input.text()
        self.password = self.password_input.text()
        self.base_url = self.base_url_input.text().strip()
        self.save_credentials = self.remember_checkbox.isChecked()
        super().accept()
        
    def set_credentials(self, username: str, password: str, base_url: str = ""):
        """Pre-fill credentials if available"""
        self.username_input.setText(username)
        self.password_input.setText(password)
        self.base_url_input.setText(base_url)
        self.remember_checkbox.setChecked(True) 