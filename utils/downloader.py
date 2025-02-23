import os
from typing import Optional, Callable, Dict, List, Tuple
from PySide6.QtCore import QObject, Signal
import threading
import queue
from .network import NetworkManager, FileItem

class DownloadManager(QObject):
    progress_updated = Signal(str, float)  # file_name, progress percentage
    overall_progress_updated = Signal(float)  # overall progress percentage
    download_completed = Signal(str)  # file_name
    download_error = Signal(str, str)  # file_name, error message
    directory_scan_completed = Signal(str, int)  # directory name, total files
    all_downloads_completed = Signal()  # emitted when all downloads are done

    def __init__(self, max_concurrent_downloads: int = 3):
        super().__init__()
        self.network = NetworkManager()
        self._active_downloads: Dict[str, threading.Thread] = {}
        self._download_queue = queue.Queue()
        self._lock = threading.Lock()
        self._max_concurrent_downloads = max_concurrent_downloads
        self._queue_processor = None
        self._stop_queue = False
        self._total_files = 0
        self._completed_files = 0
        
        # Start queue processor
        self._start_queue_processor()

    def _start_queue_processor(self):
        """Start the queue processor thread"""
        if self._queue_processor is None:
            self._stop_queue = False
            self._queue_processor = threading.Thread(target=self._process_queue)
            self._queue_processor.daemon = True
            self._queue_processor.start()

    def _process_queue(self):
        """Process downloads from the queue"""
        while not self._stop_queue:
            try:
                # Check if we can start new downloads
                with self._lock:
                    if len(self._active_downloads) >= self._max_concurrent_downloads:
                        # Wait a bit before checking again
                        threading.Event().wait(0.1)
                        continue

                # Get next download from queue with timeout
                try:
                    url, dest_path, skip_images = self._download_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Start the download
                thread = threading.Thread(
                    target=self._download_worker,
                    args=(url, dest_path, skip_images)
                )
                with self._lock:
                    self._active_downloads[url] = thread
                thread.start()

            except Exception:
                # Log error but keep processing
                continue

    def _download_worker(self, url: str, dest_path: str, skip_images: bool = False):
        try:
            # Check if we should skip images
            if skip_images and self._is_image(url):
                with self._lock:
                    self._completed_files += 1
                    progress = (self._completed_files / self._total_files) * 100
                    self.overall_progress_updated.emit(progress)
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
            
            with self._lock:
                self._completed_files += 1
                progress = (self._completed_files / self._total_files) * 100
                self.overall_progress_updated.emit(progress)
                
                # Check if all downloads are completed
                if self._completed_files == self._total_files:
                    self.all_downloads_completed.emit()

        except Exception as e:
            self.download_error.emit(os.path.basename(dest_path), str(e))
        finally:
            with self._lock:
                self._active_downloads.pop(url, None)

    def start_download_task(self, url: str, skip_images: bool = False):
        """Start a new download task, handling both single files and directories"""
        try:
            # Determine if it's a directory or single file
            is_directory = url.endswith('/')
            
            # Create base download directory
            base_dir = "downloads"
            if is_directory:
                base_dir = os.path.join(base_dir, url.rstrip('/').split('/')[-1])
            
            os.makedirs(base_dir, exist_ok=True)
            
            # Get files to download
            files = self.network.get_all_downloadable_files(url)
            if not files:
                self.download_error.emit("", "No files to download")
                return
                
            # Start the batch download
            self.start_batch_download(files, base_dir, skip_images)
            
        except Exception as e:
            self.download_error.emit("", str(e))

    def start_batch_download(self, files: List[FileItem], base_dir: str, skip_images: bool = False):
        """Start downloading a batch of files"""
        with self._lock:
            self._total_files = len(files)
            self._completed_files = 0
            
        for file in files:
            # For single files or files in directory
            file_path = self._get_relative_path(file.url, base_dir)
            dest_path = os.path.join(base_dir, file_path)
            self._download_queue.put((file.url, dest_path, skip_images))

    def _get_relative_path(self, url: str, base_dir: str) -> str:
        """Get the relative path for a file based on its URL and base directory"""
        base_name = os.path.basename(base_dir)
        url_parts = url.split('/')
        
        # If URL doesn't contain base_name, just return the file name
        if base_name not in url_parts:
            return url_parts[-1]
            
        # Get the path after base_name
        try:
            start_idx = url_parts.index(base_name) + 1
            return '/'.join(url_parts[start_idx:])
        except ValueError:
            return url_parts[-1]

    def _scan_and_queue_directory(self, url: str, base_path: str, skip_images: bool):
        """Scan directory and queue all files for download"""
        try:
            # Get all files in the directory recursively
            files = self.network.list_directory_recursive(url)
            
            # Queue regular files for download
            file_count = 0
            for file in files:
                if not file.is_directory:
                    dest_path = os.path.join(base_path, file.name)
                    self._download_queue.put((file.url, dest_path, skip_images))
                    file_count += 1
            
            # Emit signal with total file count
            self.directory_scan_completed.emit(os.path.basename(base_path), file_count)
                    
        except Exception as e:
            self.download_error.emit(os.path.basename(base_path), str(e))

    def _is_image(self, url: str) -> bool:
        """Check if URL points to an image file"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
        return url.lower().endswith(image_extensions)

    def cancel_download(self, url: str):
        """Cancel an active download"""
        with self._lock:
            if url in self._active_downloads:
                del self._active_downloads[url]

    def stop(self):
        """Stop the download manager and clean up"""
        self._stop_queue = True
        with self._lock:
            self._active_downloads.clear()
        if self._queue_processor:
            self._queue_processor.join(timeout=1)
            self._queue_processor = None 