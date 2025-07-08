"""
Configuration management for GEO Downloader
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


class Config:
    """Configuration manager for GEO Downloader"""
    
    DEFAULT_CONFIG = {
        "output_dir": "downloads",
        "parallel": False,
        "workers": None,  # Will be set to 75% of CPU cores
        "delay": 0.4,
        "chunk_size": 32768,
        "max_retries": 3,
        "retry_delay": 2,
        "verify_integrity": True,
        "force": False,
        "pattern": "!Platform_series_id",
        "gse_ids": [],
        "input_file": None,
        "config_file": None
    }
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize configuration with default values"""
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Set default workers to 75% of CPU cores
        if self.config["workers"] is None:
            self.config["workers"] = max(1, int(os.cpu_count() * 0.75))
        
        # Update with provided config
        if config_dict:
            self.update(config_dict)
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        for key, value in config_dict.items():
            if key in self.DEFAULT_CONFIG:
                self.config[key] = value
            else:
                raise ValueError(f"Unknown configuration key: {key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        if key in self.DEFAULT_CONFIG:
            self.config[key] = value
        else:
            raise ValueError(f"Unknown configuration key: {key}")
    
    def load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            
            # Validate config structure
            if not isinstance(file_config, dict):
                raise ValueError("Configuration file must contain a JSON object")
            
            self.update(file_config)
            self.config["config_file"] = config_file
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def save_to_file(self, config_file: str) -> None:
        """Save current configuration to JSON file"""
        # Create directory if it doesn't exist
        Path(config_file).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save configuration file: {e}")
    
    def validate(self) -> None:
        """Validate configuration values"""
        # Validate workers
        if not isinstance(self.config["workers"], int) or self.config["workers"] < 1:
            raise ValueError("Workers must be a positive integer")
        
        # Validate delay
        if not isinstance(self.config["delay"], (int, float)) or self.config["delay"] < 0:
            raise ValueError("Delay must be a non-negative number")
        
        # Validate chunk_size
        if not isinstance(self.config["chunk_size"], int) or self.config["chunk_size"] < 1:
            raise ValueError("Chunk size must be a positive integer")
        
        # Validate max_retries
        if not isinstance(self.config["max_retries"], int) or self.config["max_retries"] < 0:
            raise ValueError("Max retries must be a non-negative integer")
        
        # Validate retry_delay
        if not isinstance(self.config["retry_delay"], (int, float)) or self.config["retry_delay"] < 0:
            raise ValueError("Retry delay must be a non-negative number")
        
        # Validate GSE IDs format
        if self.config["gse_ids"]:
            if not isinstance(self.config["gse_ids"], list):
                raise ValueError("GSE IDs must be a list")
            
            for gse_id in self.config["gse_ids"]:
                if not isinstance(gse_id, str):
                    raise ValueError("All GSE IDs must be strings")
                if not gse_id.upper().startswith("GSE"):
                    raise ValueError(f"Invalid GSE ID format: {gse_id}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self.config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access"""
        return self.config[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dict-like assignment"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator"""
        return key in self.config
    
    def __str__(self) -> str:
        """String representation"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)