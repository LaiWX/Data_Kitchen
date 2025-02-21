import sys
from PySide6.QtWidgets import QApplication
from views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
