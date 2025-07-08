"""
Command Line Interface for GEO Downloader
"""

import argparse
import sys
import os
from typing import List, Optional

from .config import Config
from .extractor import GSEExtractor
from .downloader import GEODownloader
from .utils import confirm_action, handle_keyboard_interrupt


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        prog="geo-downloader",
        description="Download GEO datasets from NCBI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download specific GSE datasets
  geo-downloader GSE42861 GSE49064 GSE50498
  
  # Download from a file containing GSE IDs
  geo-downloader --input gse_list.txt
  
  # Download from GPL platform file with custom pattern
  geo-downloader --input GPL13534.txt --pattern "!Platform_series_id"
  
  # Use configuration file
  geo-downloader --config config.json
  
  # Enable parallel downloading with custom settings
  geo-downloader --input gse_list.txt --parallel --workers 8 --force
  
  # Download to specific directory
  geo-downloader GSE42861 --output /path/to/downloads
        """
    )
    
    # Positional arguments for GSE IDs
    parser.add_argument(
        "gse_ids",
        nargs="*",
        help="GSE IDs to download (e.g., GSE42861 GSE49064)"
    )
    
    # Input options
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Input file containing GSE IDs or GPL platform data"
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Configuration file (JSON format)"
    )
    
    parser.add_argument(
        "--pattern", "-p",
        type=str,
        default="!Platform_series_id",
        help="Pattern to match in GPL files (default: '!Platform_series_id')"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="downloads",
        help="Output directory for downloaded files (default: 'downloads')"
    )
    
    # Download options
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel downloading"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        help="Number of parallel workers (default: 75%% of CPU cores)"
    )
    
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.4,
        help="Delay between requests in seconds (default: 0.4)"
    )
    
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=32768,
        help="Download chunk size in bytes (default: 32768)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for failed downloads (default: 3)"
    )
    
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Delay between retries in seconds (default: 2.0)"
    )
    
    # Control options
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation and start downloading immediately"
    )
    
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip download integrity verification"
    )
    
    # Information options
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    
    return parser


def load_gse_ids_from_sources(args: argparse.Namespace) -> List[str]:
    """Load GSE IDs from various sources"""
    extractor = GSEExtractor(pattern=args.pattern)
    all_gse_ids = []
    
    # From command line arguments
    if args.gse_ids:
        cmd_ids = extractor.extract_from_args(args.gse_ids)
        if cmd_ids:
            all_gse_ids.extend(cmd_ids)
            print(f"[INFO] Found {len(cmd_ids)} GSE ID(s) from command line")
    
    # From input file
    if args.input:
        if not os.path.exists(args.input):
            print(f"[ERROR] Input file not found: {args.input}")
            sys.exit(1)
        
        try:
            file_ids = extractor.extract_from_file(args.input)
            if file_ids:
                all_gse_ids.extend(file_ids)
                print(f"[INFO] Found {len(file_ids)} GSE ID(s) from input file: {args.input}")
            else:
                print(f"[WARNING] No GSE IDs found in input file: {args.input}")
        except Exception as e:
            print(f"[ERROR] Failed to process input file: {e}")
            sys.exit(1)
    
    # From config file
    if args.config:
        if not os.path.exists(args.config):
            print(f"[ERROR] Configuration file not found: {args.config}")
            sys.exit(1)
        
        try:
            import json
            with open(args.config, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            config_ids = extractor.extract_from_config(config_data)
            if config_ids:
                all_gse_ids.extend(config_ids)
                print(f"[INFO] Found {len(config_ids)} GSE ID(s) from configuration file")
        except Exception as e:
            print(f"[ERROR] Failed to process configuration file: {e}")
            sys.exit(1)
    
    # Remove duplicates and validate
    unique_ids = extractor.validate_gse_ids(all_gse_ids)
    
    if not unique_ids:
        print("[ERROR] No valid GSE IDs found")
        print("\nUsage examples:")
        print("  geo-downloader GSE42861 GSE49064")
        print("  geo-downloader --input gse_list.txt")
        print("  geo-downloader --config config.json")
        sys.exit(1)
    
    return unique_ids


def create_config_from_args(args: argparse.Namespace) -> Config:
    """Create configuration from command line arguments"""
    config = Config()
    
    # Update config with command line arguments
    config_updates = {
        "output_dir": args.output,
        "parallel": args.parallel,
        "delay": args.delay,
        "chunk_size": args.chunk_size,
        "max_retries": args.max_retries,
        "retry_delay": args.retry_delay,
        "force": args.force,
        "verify_integrity": not args.no_verify,
        "pattern": args.pattern
    }
    
    # Set workers if specified
    if args.workers:
        config_updates["workers"] = args.workers
    
    # Load from config file if specified
    if args.config:
        try:
            config.load_from_file(args.config)
        except Exception as e:
            print(f"[ERROR] Failed to load configuration file: {e}")
            sys.exit(1)
    
    # Apply command line overrides
    config.update(config_updates)
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"[ERROR] Invalid configuration: {e}")
        sys.exit(1)
    
    return config


def show_download_preview(gse_ids: List[str], config: Config) -> None:
    """Show preview of what will be downloaded"""
    print("\n" + "=" * 80)
    print("DOWNLOAD PREVIEW")
    print("=" * 80)
    
    extractor = GSEExtractor()
    print(extractor.format_gse_summary(gse_ids))
    
    print(f"Configuration:")
    print(f"  Output directory: {os.path.abspath(config['output_dir'])}")
    print(f"  Parallel mode: {'Enabled' if config['parallel'] else 'Disabled'}")
    if config["parallel"]:
        print(f"  Worker threads: {config['workers']}")
    print(f"  Request delay: {config['delay']} seconds")
    print(f"  Verify integrity: {'Yes' if config['verify_integrity'] else 'No'}")
    print(f"  Max retries: {config['max_retries']}")
    
    print("=" * 80)


@handle_keyboard_interrupt
def main() -> None:
    """Main CLI entry point"""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    # Load GSE IDs from various sources
    try:
        gse_ids = load_gse_ids_from_sources(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Show preview
    if args.dry_run:
        show_download_preview(gse_ids, config)
        print("\n[DRY RUN] No files will be downloaded")
        return
    
    # Show preview and get confirmation (unless --force is used)
    if not config["force"]:
        show_download_preview(gse_ids, config)
        
        if not confirm_action("\nProceed with download?", default=False):
            print("Download cancelled by user")
            sys.exit(0)
    else:
        print(f"[INFO] Starting download of {len(gse_ids)} GSE dataset(s)")
        print(f"[INFO] Output directory: {os.path.abspath(config['output_dir'])}")
    
    # Create downloader and start download
    try:
        downloader = GEODownloader(config)
        results = downloader.download_multiple_datasets(gse_ids)
        
        # Exit with appropriate code
        if results["failed"] == 0:
            print("\n[SUCCESS] All downloads completed successfully!")
            sys.exit(0)
        elif results["completed"] > 0:
            print(f"\n[PARTIAL] {results['completed']} of {results['total']} downloads completed")
            sys.exit(1)
        else:
            print("\n[FAILED] No downloads completed successfully")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()