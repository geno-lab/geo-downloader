"""
GSE ID extraction utilities for GEO Downloader
"""

import re
import json
from typing import List, Set, Dict, Any, Optional
from pathlib import Path


class GSEExtractor:
    """Extract GSE IDs from various input sources"""
    
    def __init__(self, pattern: str = "!Platform_series_id"):
        """
        Initialize GSE extractor
        
        Args:
            pattern: Pattern to match in GPL files (default: "!Platform_series_id")
        """
        self.pattern = pattern
    
    def extract_from_text(self, text: str) -> List[str]:
        """
        Extract GSE IDs from text content
        
        Args:
            text: Input text content
            
        Returns:
            List of unique GSE IDs
        """
        gse_ids = set()
        
        # Split text into lines
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line matches GPL pattern format
            if self.pattern in line:
                # Extract GSE ID from pattern line
                match = re.search(r'(GSE\d+)', line, re.IGNORECASE)
                if match:
                    gse_ids.add(match.group(1).upper())
            else:
                # Check if line is a direct GSE ID
                if re.match(r'^GSE\d+$', line.upper()):
                    gse_ids.add(line.upper())
                else:
                    # Try to extract GSE ID from any format
                    matches = re.findall(r'GSE\d+', line, re.IGNORECASE)
                    for match in matches:
                        gse_ids.add(match.upper())
        
        return sorted(list(gse_ids))
    
    def extract_from_file(self, file_path: str) -> List[str]:
        """
        Extract GSE IDs from file
        
        Args:
            file_path: Path to input file
            
        Returns:
            List of unique GSE IDs
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.extract_from_text(content)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Input file not found: {file_path}")
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                return self.extract_from_text(content)
            except Exception as e:
                raise ValueError(f"Failed to read file {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to process file {file_path}: {e}")
    
    def extract_from_config(self, config_data: Dict[str, Any]) -> List[str]:
        """
        Extract GSE IDs from configuration data
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            List of unique GSE IDs
        """
        gse_ids = set()
        
        # Direct GSE IDs list
        if "gse_ids" in config_data and isinstance(config_data["gse_ids"], list):
            for gse_id in config_data["gse_ids"]:
                if isinstance(gse_id, str) and re.match(r'^GSE\d+$', gse_id.upper()):
                    gse_ids.add(gse_id.upper())
        
        # GSE IDs from text content
        if "gse_text" in config_data and isinstance(config_data["gse_text"], str):
            extracted = self.extract_from_text(config_data["gse_text"])
            gse_ids.update(extracted)
        
        # GSE IDs from file reference
        if "gse_file" in config_data and isinstance(config_data["gse_file"], str):
            if Path(config_data["gse_file"]).exists():
                extracted = self.extract_from_file(config_data["gse_file"])
                gse_ids.update(extracted)
        
        return sorted(list(gse_ids))
    
    def extract_from_args(self, args: List[str]) -> List[str]:
        """
        Extract GSE IDs from command line arguments
        
        Args:
            args: List of command line arguments
            
        Returns:
            List of unique GSE IDs
        """
        gse_ids = set()
        
        for arg in args:
            if re.match(r'^GSE\d+$', arg.upper()):
                gse_ids.add(arg.upper())
        
        return sorted(list(gse_ids))
    
    def validate_gse_ids(self, gse_ids: List[str]) -> List[str]:
        """
        Validate and clean GSE IDs
        
        Args:
            gse_ids: List of GSE IDs to validate
            
        Returns:
            List of valid GSE IDs
        """
        valid_ids = []
        
        for gse_id in gse_ids:
            if isinstance(gse_id, str):
                gse_id = gse_id.strip().upper()
                if re.match(r'^GSE\d+$', gse_id):
                    valid_ids.append(gse_id)
        
        return list(set(valid_ids))  # Remove duplicates
    
    def format_gse_summary(self, gse_ids: List[str]) -> str:
        """
        Format GSE IDs for display
        
        Args:
            gse_ids: List of GSE IDs
            
        Returns:
            Formatted string summary
        """
        if not gse_ids:
            return "No GSE IDs found"
        
        summary = f"Found {len(gse_ids)} GSE ID(s):\n"
        
        # Group by ranges for better display
        if len(gse_ids) <= 20:
            # Show all IDs if 20 or fewer
            for i, gse_id in enumerate(gse_ids, 1):
                summary += f"  {i:2d}. {gse_id}\n"
        else:
            # Show first 10 and last 10 with ellipsis
            for i in range(10):
                summary += f"  {i+1:2d}. {gse_ids[i]}\n"
            summary += f"  ... ({len(gse_ids) - 20} more) ...\n"
            for i in range(len(gse_ids) - 10, len(gse_ids)):
                summary += f"  {i+1:2d}. {gse_ids[i]}\n"
        
        return summary
    
    def save_gse_list(self, gse_ids: List[str], output_file: str) -> None:
        """
        Save GSE IDs to file
        
        Args:
            gse_ids: List of GSE IDs
            output_file: Output file path
        """
        # Create directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for gse_id in gse_ids:
                    f.write(f"{gse_id}\n")
        except Exception as e:
            raise IOError(f"Failed to save GSE list to {output_file}: {e}")
    
    def load_gse_list(self, input_file: str) -> List[str]:
        """
        Load GSE IDs from file
        
        Args:
            input_file: Input file path
            
        Returns:
            List of GSE IDs
        """
        return self.extract_from_file(input_file)