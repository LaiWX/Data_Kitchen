import os
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal
import threading
from .network import NetworkManager

class DownloadManager(QObject):
    progress_updated = Signal(str, float)  # file_name, progress percentage
    download_completed = Signal(str)  # file_name
    download_error = Signal(str, str)  # file_name, error message

    def __init__(self):
        super().__init__()
        self.network = NetworkManager()
        self._active_downloads = {}
        self._lock = threading.Lock()

    def _download_worker(self, url: str, dest_path: str, skip_images: bool = False):
        try:
            # Check if we should skip images
            if skip_images and self._is_image(url):
                return

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Convert .gls to .csv if necessary
            if dest_path.lower().endswith('.gls'):
                dest_path = dest_path[:-4] + '.csv'

            response = self.network.download_file(url)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(dest_path, 'wb') as f:
                if total_size == 0:
                    f.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = (downloaded / total_size) * 100
                            self.progress_updated.emit(os.path.basename(dest_path), progress)

            self.download_completed.emit(os.path.basename(dest_path))

        except Exception as e:
            self.download_error.emit(os.path.basename(dest_path), str(e))
        finally:
            with self._lock:
                if url in self._active_downloads:
                    del self._active_downloads[url]

    def start_download(self, url: str, dest_path: str, skip_images: bool = False):
        """Start a new download in a separate thread"""
        with self._lock:
            if url in self._active_downloads:
                return
            
            thread = threading.Thread(
                target=self._download_worker,
                args=(url, dest_path, skip_images)
            )
            self._active_downloads[url] = thread
            thread.start()

    def _is_image(self, url: str) -> bool:
        """Check if the URL points to an image file"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff'}
        return any(url.lower().endswith(ext) for ext in image_extensions)

    def cancel_download(self, url: str):
        """Cancel an active download"""
        with self._lock:
            if url in self._active_downloads:
                # Note: We can't actually stop the thread, but we can remove it from active downloads
                del self._active_downloads[url] 