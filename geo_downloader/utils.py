"""
Utility functions for GEO Downloader
"""

import os
import sys
import time
import hashlib
import urllib.request
from typing import Optional, Tuple, Any
from pathlib import Path


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_mb = size_bytes / (1024 * 1024)
    size_gb = size_mb / 1024
    
    if size_gb >= 1:
        return f"{size_gb:.2f} GB"
    elif size_mb >= 1:
        return f"{size_mb:.2f} MB"
    else:
        return f"{size_bytes / 1024:.2f} KB"


def format_speed(bytes_per_second: float) -> str:
    """
    Format download speed in human-readable format
    
    Args:
        bytes_per_second: Speed in bytes per second
        
    Returns:
        Formatted speed string
    """
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second/(1024*1024):.2f} MB/s"
    elif bytes_per_second >= 1024:
        return f"{bytes_per_second/1024:.2f} KB/s"
    else:
        return f"{bytes_per_second:.2f} B/s"


def format_time(seconds: float) -> str:
    """
    Format time duration in human-readable format
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    if seconds > 3600:
        return f"{seconds/3600:.1f}h"
    elif seconds > 60:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds:.1f}s"


def build_geo_url(gse_id: str, file_name: str) -> str:
    """
    Build GEO FTP URL for a given GSE ID and file name
    
    Args:
        gse_id: GSE ID (e.g., "GSE12345")
        file_name: File name (e.g., "GSE12345_RAW.tar")
        
    Returns:
        Complete FTP URL
    """
    # Remove GSE prefix and get numeric part
    gse_num = gse_id.replace("GSE", "")
    
    # Get first part for directory structure
    if len(gse_num) >= 3:
        first_three = gse_num[:-3]
    else:
        first_three = "0"
    
    # Build URL
    base_url = "https://ftp.ncbi.nlm.nih.gov/geo/series"
    series_dir = f"GSE{first_three}nnn"
    gse_dir = gse_id
    
    return f"{base_url}/{series_dir}/{gse_dir}/suppl/{file_name}"


def get_file_size(url: str, timeout: int = 30) -> Optional[int]:
    """
    Get file size from URL using HEAD request
    
    Args:
        url: File URL
        timeout: Request timeout in seconds
        
    Returns:
        File size in bytes or None if failed
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; GEO-Downloader/1.0)')
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_length = response.headers.get('Content-Length')
            if content_length:
                return int(content_length)
    except Exception:
        pass
    
    return None


def verify_file_integrity(file_path: str, expected_size: int) -> bool:
    """
    Verify file integrity by checking size
    
    Args:
        file_path: Path to the file
        expected_size: Expected file size in bytes
        
    Returns:
        True if file is valid, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
        
        actual_size = os.path.getsize(file_path)
        return actual_size == expected_size
    except Exception:
        return False


def calculate_md5(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calculate MD5 hash of a file
    
    Args:
        file_path: Path to the file
        chunk_size: Chunk size for reading
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        raise IOError(f"Failed to calculate MD5 for {file_path}: {e}")


def ensure_directory(directory: str) -> None:
    """
    Ensure directory exists, create if necessary
    
    Args:
        directory: Directory path
    """
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise IOError(f"Failed to create directory {directory}: {e}")


def safe_filename(filename: str) -> str:
    """
    Make filename safe for filesystem
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip('. ')
    
    # Ensure filename is not empty
    if not safe_name:
        safe_name = "unnamed_file"
    
    return safe_name


def print_progress_bar(current: int, total: int, start_time: float, 
                      prefix: str = "", suffix: str = "", 
                      bar_length: int = 50) -> None:
    """
    Print progress bar to stdout
    
    Args:
        current: Current progress
        total: Total items
        start_time: Start time for speed calculation
        prefix: Prefix string
        suffix: Suffix string
        bar_length: Length of progress bar
    """
    if total == 0:
        percent = 0
    else:
        percent = min(100, int(100 * current / total))
    
    filled_length = int(bar_length * current / total) if total > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    
    # Calculate speed and ETA
    elapsed_time = time.time() - start_time
    if elapsed_time > 0 and current > 0:
        speed = current / elapsed_time
        eta = (total - current) / speed if speed > 0 else 0
        speed_str = f"{speed:.1f} items/s"
        eta_str = format_time(eta)
    else:
        speed_str = "0 items/s"
        eta_str = "N/A"
    
    # Print progress bar
    sys.stdout.write(f"\r{prefix} [{bar}] {percent}% {current}/{total} @ {speed_str} ETA: {eta_str} {suffix}")
    sys.stdout.flush()
    
    # Print newline when complete
    if current >= total:
        print()


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation
    
    Args:
        message: Confirmation message
        default: Default answer if user just presses Enter
        
    Returns:
        True if user confirms, False otherwise
    """
    while True:
        suffix = " [Y/n]" if default else " [y/N]"
        try:
            response = input(f"{message}{suffix}: ").strip().lower()
            
            if not response:
                return default
            elif response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return False
        except EOFError:
            return default


def handle_keyboard_interrupt(func):
    """
    Decorator to handle keyboard interrupts gracefully
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            sys.exit(1)
    return wrapper


class ProgressTracker:
    """Simple progress tracker for downloads"""
    
    def __init__(self, total: int, description: str = "Progress"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()
    
    def update(self, increment: int = 1) -> None:
        """Update progress"""
        self.current += increment
        self.print_progress()
    
    def print_progress(self) -> None:
        """Print current progress"""
        print_progress_bar(
            self.current, 
            self.total, 
            self.start_time,
            prefix=self.description
        )
    
    def finish(self) -> None:
        """Mark as finished"""
        self.current = self.total
        self.print_progress()
        print(f"\n{self.description} completed!")