from PySide6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, 
                                QAbstractItemView, QHeaderView, QTreeWidgetItemIterator)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction
from datetime import datetime
from typing import Optional, List, Dict
import os

class FileTreeWidget(QTreeWidget):
    download_requested = Signal(str, str, bool)  # url, save_path, skip_images
    navigate_requested = Signal(str)  # url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_path = ""
        self.setup_context_menu()

    def setup_ui(self):
        # Set up columns
        self.setColumnCount(4)
        self.setHeaderLabels(['Name', 'Size', 'Modified', 'URL'])
        
        # Enable multiple selection and checkboxes
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setColumnWidth(0, 300)  # Name column
        self.setColumnWidth(1, 100)  # Size column
        self.setColumnWidth(2, 150)  # Modified column
        
        # Hide URL column
        self.hideColumn(3)
        
        # Enable sorting
        self.setSortingEnabled(True)
        self.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.header().setSectionResizeMode(2, QHeaderView.Interactive)
        
        # Enable checkboxes
        self.setRootIsDecorated(False)
        self.itemClicked.connect(self.handle_item_click)
        self.itemDoubleClicked.connect(self.handle_double_click)

    def setup_context_menu(self):
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # Create context menu
        self.context_menu = QMenu(self)
        self.download_action = QAction("Download", self)
        self.download_no_images_action = QAction("Download (Skip Images)", self)
        
        self.context_menu.addAction(self.download_action)
        self.context_menu.addAction(self.download_no_images_action)
        
        # Connect actions
        self.download_action.triggered.connect(
            lambda: self.handle_download(skip_images=False))
        self.download_no_images_action.triggered.connect(
            lambda: self.handle_download(skip_images=True))

    def show_context_menu(self, position):
        items = self.selectedItems()
        if items:
            self.context_menu.exec_(self.viewport().mapToGlobal(position))

    def handle_item_click(self, item: QTreeWidgetItem, column: int):
        # Handle checkbox toggling
        if column == 0:
            item.setCheckState(0, 
                Qt.Unchecked if item.checkState(0) == Qt.Checked else Qt.Checked)

    def handle_double_click(self, item: QTreeWidgetItem, column: int):
        # Navigate into directory on double click
        if item.data(0, Qt.UserRole) == "directory":
            self.navigate_requested.emit(item.text(3))  # Emit URL

    def handle_download(self, skip_images: bool = False):
        items = self.get_selected_or_checked_items()
        for item in items:
            url = item.text(3)
            # Create save path based on current structure
            relative_path = os.path.join(
                os.path.basename(self.current_path), 
                item.text(0)
            )
            self.download_requested.emit(url, relative_path, skip_images)

    def get_selected_or_checked_items(self) -> List[QTreeWidgetItem]:
        """Get items that are either selected or checked"""
        items = []
        for item in self.selectedItems():
            if item not in items:
                items.append(item)
        
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if (item.checkState(0) == Qt.Checked and 
                item not in items):
                items.append(item)
            iterator += 1
            
        return items

    def add_file_item(self, name: str, size: str, modified: datetime, 
                      url: str, is_directory: bool):
        item = QTreeWidgetItem(self)
        item.setText(0, name)
        item.setText(1, size)
        item.setText(2, modified.strftime("%Y-%m-%d %H:%M"))
        item.setText(3, url)
        
        # Set item type
        item.setData(0, Qt.UserRole, "directory" if is_directory else "file")
        
        # Set icon based on type
        icon = QIcon.fromTheme("folder" if is_directory else "text-x-generic")
        item.setIcon(0, icon)
        
        # Add checkbox
        item.setCheckState(0, Qt.Unchecked)
        
        return item

    def clear_and_set_path(self, path: str):
        """Clear the view and set new current path"""
        self.clear()
        self.current_path = path 