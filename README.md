# GEO Downloader

A comprehensive command-line tool for downloading Gene Expression Omnibus (GEO) datasets from NCBI. This tool supports multiple input formats, parallel downloading, resume capability, and integrity verification.

## Features

- **Multiple Input Formats**: Support for direct GSE IDs, text files, GPL platform files, and JSON configuration files
- **Flexible Pattern Matching**: Configurable pattern matching for GPL platform files
- **Parallel Downloads**: Multi-threaded downloading for improved performance
- **Resume Support**: Automatic resume of interrupted downloads
- **Integrity Verification**: Built-in file integrity checking
- **Progress Tracking**: Real-time download progress and status reporting
- **Error Handling**: Robust retry mechanisms and error recovery

## Installation

### From Source

```bash
git clone https://github.com/geno-lab/geo-downloader.git
cd geo-downloader
pip install -e .
```

### Using pip

```bash
pip install geo-downloader
```

## Quick Start

### Basic Usage

Download specific GSE datasets:
```bash
geo-downloader GSE42861 GSE49064 GSE50498
```

Download from a text file containing GSE IDs:
```bash
geo-downloader --input gse_list.txt
```

Download from a GPL platform file:
```bash
geo-downloader --input GPL13534.txt --pattern "!Platform_series_id"
```

### Advanced Usage

Enable parallel downloading:
```bash
geo-downloader --input gse_list.txt --parallel --workers 8
```

Skip confirmation and download immediately:
```bash
geo-downloader GSE42861 GSE49064 --force
```

Custom output directory:
```bash
geo-downloader GSE42861 --output /path/to/downloads
```

## Input Formats

### 1. Command Line GSE IDs
```bash
geo-downloader GSE42861 GSE49064 GSE50498
```

### 2. Simple Text File
Create a text file with one GSE ID per line:
```
GSE42861
GSE49064
GSE50498
GSE51954
```

### 3. GPL Platform File
GPL platform files containing lines like:
```
!Platform_series_id = GSE42861
!Platform_series_id = GSE49064
```

### 4. JSON Configuration File
```json
{
  "gse_ids": ["GSE42861", "GSE49064", "GSE50498"],
  "output_dir": "downloads",
  "parallel": true,
  "workers": 8,
  "force": false
}
```

## Command Line Options

### Input Options
- `gse_ids`: GSE IDs to download (positional arguments)
- `--input, -i`: Input file containing GSE IDs or GPL platform data
- `--config, -c`: Configuration file (JSON format)
- `--pattern, -p`: Pattern to match in GPL files (default: '!Platform_series_id')

### Output Options
- `--output, -o`: Output directory for downloaded files (default: 'downloads')

### Download Options
- `--parallel`: Enable parallel downloading
- `--workers, -w`: Number of parallel workers (default: 75% of CPU cores)
- `--delay, -d`: Delay between requests in seconds (default: 0.4)
- `--chunk-size`: Download chunk size in bytes (default: 32768)
- `--max-retries`: Maximum number of retries for failed downloads (default: 3)
- `--retry-delay`: Delay between retries in seconds (default: 2.0)

### Control Options
- `--force, -f`: Skip confirmation and start downloading immediately
- `--no-verify`: Skip download integrity verification
- `--dry-run`: Show what would be downloaded without actually downloading

## Configuration File

You can use a JSON configuration file to specify all settings:

```json
{
  "gse_ids": ["GSE42861", "GSE49064"],
  "output_dir": "my_downloads",
  "parallel": true,
  "workers": 4,
  "delay": 0.5,
  "chunk_size": 65536,
  "max_retries": 5,
  "retry_delay": 3.0,
  "verify_integrity": true,
  "force": false,
  "pattern": "!Platform_series_id"
}
```

Use the configuration file:
```bash
geo-downloader --config config.json
```

## Examples

### Example 1: Basic Download
```bash
geo-downloader GSE42861 GSE49064
```

### Example 2: Download from File with Custom Settings
```bash
geo-downloader --input gse_list.txt --parallel --workers 6 --output /data/geo
```

### Example 3: GPL Platform File Processing
```bash
geo-downloader --input GPL13534.txt --pattern "!Platform_series_id" --force
```

### Example 4: Dry Run to Preview
```bash
geo-downloader --input gse_list.txt --dry-run
```

### Example 5: Configuration File with Override
```bash
geo-downloader --config config.json --force --workers 10
```

## Output

The tool creates the following structure in the output directory:

```
downloads/
├── GSE42861_RAW.tar
├── GSE49064_RAW.tar
├── GSE50498_RAW.tar
└── download_status.json
```

The `download_status.json` file contains detailed information about each download, including:
- Download status (completed, failed, partial)
- File metadata
- Error messages (if any)
- Download timestamps

## Error Handling

The tool includes comprehensive error handling:

- **Network errors**: Automatic retry with configurable delays
- **File corruption**: Integrity verification and re-download
- **Interrupted downloads**: Automatic resume capability
- **Missing files**: Clear error messages and status tracking

## Performance Tips

1. **Use parallel mode** for downloading multiple large files
2. **Adjust chunk size** based on your network speed
3. **Set appropriate delays** to avoid overwhelming the server
4. **Use resume capability** for large files in unstable network conditions

## Requirements

- Python 3.7 or higher
- Internet connection
- Sufficient disk space for downloaded files

## Dependencies

- `requests`: HTTP library for downloading
- `urllib3`: URL handling utilities
- `tqdm`: Progress bar display (optional)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please open an issue on the GitHub repository.

## Citation

If you use this tool in your research, please cite:

```
GEO Downloader: A comprehensive tool for downloading GEO datasets from NCBI
Version 1.0.0
https://github.com/geno-lab/geo-downloader
```
