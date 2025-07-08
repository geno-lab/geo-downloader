#!/bin/bash

# Installation and testing script for geo-downloader

echo "Installing geo-downloader..."
cd ..
pip install -e .

echo "Testing basic functionality..."

# Test 1: Show help
echo "=== Test 1: Show help ==="
geo-downloader --help

# Test 2: Dry run with command line GSE IDs
echo "=== Test 2: Dry run with command line GSE IDs ==="
geo-downloader GSE42861 GSE49064 --dry-run

# Test 3: Dry run with input file
echo "=== Test 3: Dry run with input file ==="
geo-downloader --input examples/gse_list.txt --dry-run --parallel

# Test 4: Dry run with config file
echo "=== Test 4: Dry run with config file ==="
geo-downloader --config examples/config.json --dry-run

# Test 5: Test small download (uncomment to actually download)
# echo "=== Test 5: Small download test ==="
# geo-downloader GSE42861 --output test_downloads --force

echo "All tests completed!"
echo "To perform actual downloads, run:"
echo "  geo-downloader GSE42861 --force"
echo "  geo-downloader --input examples/gse_list.txt --parallel"