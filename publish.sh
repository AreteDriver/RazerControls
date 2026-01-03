#!/bin/bash
# =============================================================================
# PyPI Publishing Script for Razer Control Center
# =============================================================================
#
# This script builds and publishes the package to PyPI.
# Run with --test to publish to TestPyPI first.
#
# Prerequisites:
#   pip install build twine
#
# Usage:
#   ./publish.sh          # Publish to PyPI
#   ./publish.sh --test   # Publish to TestPyPI
#   ./publish.sh --build  # Build only, no upload
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
USE_TEST_PYPI=false
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --test)
            USE_TEST_PYPI=true
            shift
            ;;
        --build)
            BUILD_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Razer Control Center PyPI Publisher ===${NC}"

# Check for required tools
echo -e "${YELLOW}Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

# Install/upgrade build tools
echo -e "${YELLOW}Installing/upgrading build tools...${NC}"
python3 -m pip install --upgrade pip build twine --quiet

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf dist/ build/ src/*.egg-info/

# Build the package
echo -e "${YELLOW}Building package...${NC}"
python3 -m build

# Show what was built
echo -e "${GREEN}Built packages:${NC}"
ls -la dist/

if $BUILD_ONLY; then
    echo -e "${GREEN}Build complete. Skipping upload.${NC}"
    exit 0
fi

# Verify the package
echo -e "${YELLOW}Verifying package with twine...${NC}"
python3 -m twine check dist/*

# Upload
if $USE_TEST_PYPI; then
    echo -e "${YELLOW}Uploading to TestPyPI...${NC}"
    python3 -m twine upload --repository testpypi dist/*
    echo -e "${GREEN}Package uploaded to TestPyPI!${NC}"
    echo -e "${GREEN}Install with: pip install --index-url https://test.pypi.org/simple/ razer-control-center${NC}"
else
    echo -e "${YELLOW}Uploading to PyPI...${NC}"
    echo -e "${RED}WARNING: This will publish to the REAL PyPI!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m twine upload dist/*
        echo -e "${GREEN}Package uploaded to PyPI!${NC}"
        echo -e "${GREEN}Install with: pip install razer-control-center${NC}"
    else
        echo -e "${YELLOW}Upload cancelled.${NC}"
    fi
fi
