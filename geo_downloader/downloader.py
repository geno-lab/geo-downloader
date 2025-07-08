"""
GEO dataset downloader with parallel support and integrity verification
"""

import os
import json
import time
import urllib.request
import urllib.error
import threading
import concurrent.futures
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from xml.etree import ElementTree

from .config import Config
from .utils import (
    format_size, format_speed, format_time, build_geo_url, 
    get_file_size, verify_file_integrity, ensure_directory,
    safe_filename, ProgressTracker
)


class GEODownloader:
    """Main downloader class for GEO datasets"""
    
    def __init__(self, config: Config):
        """
        Initialize GEO downloader
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.download_status = {}
        self.active_downloads = {}
        self.print_lock = threading.Lock()
        self.status_lock = threading.Lock()
        
        # Ensure output directory exists
        ensure_directory(self.config["output_dir"])
    
    def get_gse_metadata(self, gse_id: str) -> Dict[str, Any]:
        """
        Get metadata for a GSE ID
        
        Args:
            gse_id: GSE ID to fetch metadata for
            
        Returns:
            Dictionary containing GSE metadata
        """
        metadata = {
            "gse_id": gse_id,
            "has_raw_data": False,
            "sample_count": 0,
            "title": "N/A",
            "summary": "N/A",
            "organism": "N/A",
            "submission_date": "N/A",
            "pubmed_id": "N/A",
            "platforms": [],
            "experiment_type": "N/A",
            "supplementary_files": [],
            "raw_files": [],
            "error": None
        }
        
        try:
            # Get GSE summary from NCBI
            summary_xml = self._fetch_gse_summary(gse_id)
            if summary_xml:
                metadata.update(self._parse_gse_summary(summary_xml, gse_id))
            
            # Check for raw data files
            raw_files, has_raw = self._check_raw_files(gse_id)
            metadata["raw_files"] = raw_files
            metadata["has_raw_data"] = has_raw
            
        except Exception as e:
            metadata["error"] = str(e)
            print(f"[ERROR] Failed to fetch metadata for {gse_id}: {e}")
        
        return metadata
    
    def _fetch_gse_summary(self, gse_id: str) -> Optional[bytes]:
        """Fetch GSE summary XML from NCBI"""
        try:
            # Search for GSE to get numeric ID
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term={gse_id}[Accession]&retmode=xml"
            
            with urllib.request.urlopen(search_url, timeout=30) as response:
                search_xml = response.read()
            
            search_root = ElementTree.fromstring(search_xml)
            id_elements = search_root.findall('.//Id')
            
            if not id_elements:
                return None
            
            numeric_id = id_elements[0].text
            
            # Get summary using numeric ID
            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id={numeric_id}&retmode=xml"
            
            with urllib.request.urlopen(summary_url, timeout=30) as response:
                return response.read()
                
        except Exception as e:
            print(f"[WARNING] Failed to fetch summary for {gse_id}: {e}")
            return None
    
    def _parse_gse_summary(self, summary_xml: bytes, gse_id: str) -> Dict[str, Any]:
        """Parse GSE summary XML"""
        metadata = {}
        
        try:
            root = ElementTree.fromstring(summary_xml)
            doc_sum = root.find('.//DocSum')
            
            if doc_sum is None:
                return metadata
            
            for item in doc_sum.findall('.//Item'):
                name = item.get('Name')
                
                if name == 'title':
                    metadata['title'] = item.text if item.text else "N/A"
                elif name == 'summary':
                    metadata['summary'] = item.text if item.text else "N/A"
                elif name == 'gdsType':
                    metadata['experiment_type'] = item.text if item.text else "N/A"
                elif name == 'taxon':
                    metadata['organism'] = item.text if item.text else "N/A"
                elif name == 'GPL':
                    platforms = item.text.split(';') if item.text else []
                    metadata['platforms'] = [p.strip() for p in platforms]
                elif name == 'PDAT':
                    metadata['submission_date'] = item.text if item.text else "N/A"
            
            # Get sample count
            metadata['sample_count'] = self._count_samples(gse_id)
            
        except Exception as e:
            print(f"[WARNING] Failed to parse summary for {gse_id}: {e}")
        
        return metadata
    
    def _count_samples(self, gse_id: str) -> int:
        """Count samples in GSE"""
        try:
            url = f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gse_id}&targ=self&form=xml&view=quick"
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_content = response.read()
            
            root = ElementTree.fromstring(xml_content)
            samples = root.findall('.//Sample')
            return len(samples)
            
        except Exception:
            return 0
    
    def _check_raw_files(self, gse_id: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Check for raw data files in GSE supplementary directory"""
        raw_files = []
        
        try:
            # Build supplementary directory URL
            gse_num = gse_id.replace("GSE", "")
            first_three = gse_num[:-3] if len(gse_num) >= 3 else "0"
            suppl_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/GSE{first_three}nnn/{gse_id}/suppl/"
            
            # Get directory listing
            with urllib.request.urlopen(suppl_url, timeout=30) as response:
                html_content = response.read().decode('utf-8')
            
            # Parse file links
            import re
            file_links = re.findall(r'<a href="([^"]+)">([^<]+)</a>', html_content)
            file_names = [name for _, name in file_links 
                         if name not in ["Parent Directory", "filelist.txt"]]
            
            # Look for raw data files
            raw_keywords = ['raw', '.idat', '.cel', '.fastq', '.fq', '.sra', '.bam', '.cram',
                           'signal', 'intensity', 'reads', 'sequencing']
            
            for filename in file_names:
                filename_lower = filename.lower()
                is_raw = (any(keyword in filename_lower for keyword in raw_keywords) or 
                         '_raw.' in filename_lower or filename_lower.endswith('_raw.tar'))
                
                if is_raw:
                    file_url = f"{suppl_url}{filename}"
                    file_size = get_file_size(file_url)
                    
                    raw_files.append({
                        "filename": filename,
                        "url": file_url,
                        "size_bytes": file_size,
                        "size_human": format_size(file_size) if file_size else "Unknown"
                    })
            
        except Exception as e:
            print(f"[WARNING] Failed to check raw files for {gse_id}: {e}")
        
        return raw_files, len(raw_files) > 0
    
    def download_gse_dataset(self, gse_id: str) -> Dict[str, Any]:
        """
        Download all raw files for a GSE dataset
        
        Args:
            gse_id: GSE ID to download
            
        Returns:
            Download status dictionary
        """
        print(f"[INFO] Processing {gse_id}...")
        
        # Get metadata
        metadata = self.get_gse_metadata(gse_id)
        
        if metadata["error"]:
            return {
                "gse_id": gse_id,
                "status": "failed",
                "error": metadata["error"],
                "files": []
            }
        
        if not metadata["has_raw_data"]:
            return {
                "gse_id": gse_id,
                "status": "no_raw_data",
                "error": "No raw data files found",
                "files": []
            }
        
        # Download files
        download_results = []
        
        if self.config["parallel"] and len(metadata["raw_files"]) > 1:
            # Parallel download
            download_results = self._download_files_parallel(gse_id, metadata["raw_files"])
        else:
            # Sequential download
            download_results = self._download_files_sequential(gse_id, metadata["raw_files"])
        
        # Determine overall status
        successful = sum(1 for result in download_results if result["status"] == "completed")
        total = len(download_results)
        
        if successful == total:
            status = "completed"
        elif successful > 0:
            status = "partial"
        else:
            status = "failed"
        
        return {
            "gse_id": gse_id,
            "status": status,
            "error": None,
            "files": download_results,
            "metadata": metadata
        }
    
    def _download_files_sequential(self, gse_id: str, raw_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Download files sequentially"""
        results = []
        
        for i, file_info in enumerate(raw_files, 1):
            print(f"[INFO] Downloading file {i}/{len(raw_files)}: {file_info['filename']}")
            result = self._download_single_file(gse_id, file_info)
            results.append(result)
            
            # Add delay between downloads
            if i < len(raw_files) and self.config["delay"] > 0:
                time.sleep(self.config["delay"])
        
        return results
    
    def _download_files_parallel(self, gse_id: str, raw_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Download files in parallel"""
        results = []
        
        print(f"[INFO] Starting parallel download of {len(raw_files)} files using {self.config['workers']} workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config["workers"]) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(self._download_single_file, gse_id, file_info): file_info
                for file_info in raw_files
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "filename": file_info["filename"],
                        "status": "failed",
                        "error": str(e),
                        "size_bytes": file_info.get("size_bytes", 0)
                    })
        
        return results
    
    def _download_single_file(self, gse_id: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Download a single file with resume support"""
        filename = file_info["filename"]
        file_url = file_info["url"]
        expected_size = file_info.get("size_bytes", 0)
        
        # Create safe local filename
        safe_name = safe_filename(filename)
        local_path = os.path.join(self.config["output_dir"], safe_name)
        
        # Check if file already exists and is complete
        if os.path.exists(local_path) and expected_size > 0:
            if verify_file_integrity(local_path, expected_size):
                with self.print_lock:
                    print(f"[INFO] File already exists and is complete: {filename}")
                return {
                    "filename": filename,
                    "local_path": local_path,
                    "status": "completed",
                    "error": None,
                    "size_bytes": expected_size
                }
        
        # Download with retries
        for attempt in range(self.config["max_retries"] + 1):
            try:
                result = self._download_with_progress(file_url, local_path, expected_size)
                
                # Verify download if expected size is known
                if expected_size > 0 and self.config["verify_integrity"]:
                    if not verify_file_integrity(local_path, expected_size):
                        raise ValueError("Downloaded file size doesn't match expected size")
                
                with self.print_lock:
                    print(f"[SUCCESS] Downloaded: {filename}")
                
                return {
                    "filename": filename,
                    "local_path": local_path,
                    "status": "completed",
                    "error": None,
                    "size_bytes": os.path.getsize(local_path)
                }
                
            except Exception as e:
                error_msg = str(e)
                
                if attempt < self.config["max_retries"]:
                    with self.print_lock:
                        print(f"[WARNING] Download failed (attempt {attempt + 1}/{self.config['max_retries'] + 1}): {error_msg}")
                        print(f"[INFO] Retrying in {self.config['retry_delay']} seconds...")
                    time.sleep(self.config["retry_delay"])
                else:
                    with self.print_lock:
                        print(f"[ERROR] Download failed after {self.config['max_retries'] + 1} attempts: {error_msg}")
                    
                    return {
                        "filename": filename,
                        "local_path": local_path,
                        "status": "failed",
                        "error": error_msg,
                        "size_bytes": 0
                    }
    
    def _download_with_progress(self, url: str, local_path: str, expected_size: int) -> None:
        """Download file with progress tracking"""
        # Check for existing partial file
        resume_pos = 0
        mode = 'wb'
        
        if os.path.exists(local_path):
            existing_size = os.path.getsize(local_path)
            if existing_size < expected_size:
                resume_pos = existing_size
                mode = 'ab'
                with self.print_lock:
                    print(f"[INFO] Resuming download from {format_size(resume_pos)}")
        
        # Create request with resume header if needed
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; GEO-Downloader/1.0)')
        
        if resume_pos > 0:
            req.add_header('Range', f'bytes={resume_pos}-')
        
        # Open connection and download
        with urllib.request.urlopen(req, timeout=60) as response:
            # Get total size
            if resume_pos > 0:
                if 'Content-Range' in response.headers:
                    total_size = int(response.headers['Content-Range'].split('/')[-1])
                else:
                    total_size = expected_size
            else:
                total_size = int(response.headers.get('Content-Length', expected_size))
            
            # Download with progress
            with open(local_path, mode) as f:
                downloaded = resume_pos
                start_time = time.time()
                last_print_time = start_time
                
                while True:
                    chunk = response.read(self.config["chunk_size"])
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Print progress occasionally (not too frequently)
                    current_time = time.time()
                    if current_time - last_print_time >= 1.0:  # Print every second
                        if total_size > 0:
                            percent = min(100, int(100 * downloaded / total_size))
                            speed = downloaded / (current_time - start_time) if current_time > start_time else 0
                            eta = (total_size - downloaded) / speed if speed > 0 else 0
                            
                            with self.print_lock:
                                print(f"  Progress: {percent}% ({format_size(downloaded)}/{format_size(total_size)}) "
                                     f"@ {format_speed(speed)} ETA: {format_time(eta)}")
                        
                        last_print_time = current_time
    
    def save_download_status(self, status_file: str) -> None:
        """Save download status to file"""
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(self.download_status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WARNING] Failed to save download status: {e}")
    
    def load_download_status(self, status_file: str) -> None:
        """Load download status from file"""
        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    self.download_status = json.load(f)
                print(f"[INFO] Loaded download status for {len(self.download_status)} GSE datasets")
            except Exception as e:
                print(f"[WARNING] Failed to load download status: {e}")
                self.download_status = {}
    
    def download_multiple_datasets(self, gse_ids: List[str]) -> Dict[str, Any]:
        """
        Download multiple GSE datasets
        
        Args:
            gse_ids: List of GSE IDs to download
            
        Returns:
            Summary of download results
        """
        if not gse_ids:
            return {"error": "No GSE IDs provided"}
        
        print(f"[INFO] Starting download of {len(gse_ids)} GSE datasets")
        print(f"[INFO] Output directory: {os.path.abspath(self.config['output_dir'])}")
        print(f"[INFO] Parallel mode: {'Enabled' if self.config['parallel'] else 'Disabled'}")
        
        if self.config["parallel"]:
            print(f"[INFO] Using {self.config['workers']} worker threads")
        
        print("-" * 80)
        
        # Load existing status
        status_file = os.path.join(self.config["output_dir"], "download_status.json")
        self.load_download_status(status_file)
        
        start_time = time.time()
        results = []
        
        for i, gse_id in enumerate(gse_ids, 1):
            print(f"\n[{i}/{len(gse_ids)}] Processing {gse_id}...")
            
            result = self.download_gse_dataset(gse_id)
            results.append(result)
            
            # Update status
            self.download_status[gse_id] = result
            
            # Save status periodically
            if i % 5 == 0:
                self.save_download_status(status_file)
        
        # Final status save
        self.save_download_status(status_file)
        
        # Print summary
        total_time = time.time() - start_time
        completed = sum(1 for r in results if r["status"] == "completed")
        partial = sum(1 for r in results if r["status"] == "partial")
        failed = sum(1 for r in results if r["status"] in ["failed", "no_raw_data"])
        
        print("\n" + "=" * 80)
        print("[SUMMARY] Download Results:")
        print(f"  Total datasets processed: {len(results)}")
        print(f"  Successfully completed: {completed}")
        print(f"  Partially completed: {partial}")
        print(f"  Failed or no raw data: {failed}")
        print(f"  Total time: {format_time(total_time)}")
        print("=" * 80)
        
        return {
            "total": len(results),
            "completed": completed,
            "partial": partial,
            "failed": failed,
            "results": results,
            "total_time": total_time
        }