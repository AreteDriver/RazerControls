#!/bin/bash
# Build script for Razer Control Center AppImage
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_DIR}/build/appimage"
APPDIR="${BUILD_DIR}/Razer_Control_Center.AppDir"

echo "=== Building Razer Control Center AppImage ==="
echo "Project: ${PROJECT_DIR}"
echo "Build: ${BUILD_DIR}"

# Clean previous build
rm -rf "${BUILD_DIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib/python3/site-packages"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/scalable/apps"

# Copy AppRun and desktop file
cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/"
chmod +x "${APPDIR}/AppRun"
cp "${SCRIPT_DIR}/razer-control-center.desktop" "${APPDIR}/"
cp "${SCRIPT_DIR}/razer-control-center.desktop" "${APPDIR}/usr/share/applications/"

# Copy icon
cp "${SCRIPT_DIR}/razer-control-center.svg" "${APPDIR}/"
cp "${SCRIPT_DIR}/razer-control-center.svg" "${APPDIR}/usr/share/icons/hicolor/scalable/apps/"

# Create virtual environment and install dependencies
echo "=== Installing Python dependencies ==="
python3 -m venv "${BUILD_DIR}/venv"
source "${BUILD_DIR}/venv/bin/activate"

pip install --upgrade pip wheel
pip install "${PROJECT_DIR}"

# Copy Python interpreter
echo "=== Bundling Python ==="
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
cp "$(which python3)" "${APPDIR}/usr/bin/"

# Copy site-packages
cp -r "${BUILD_DIR}/venv/lib/python${PYTHON_VERSION}/site-packages/"* "${APPDIR}/usr/lib/python3/site-packages/"

# Copy the application source
echo "=== Copying application ==="
for dir in apps services crates tools; do
    cp -r "${PROJECT_DIR}/${dir}" "${APPDIR}/usr/lib/python3/site-packages/"
done

# Copy Python standard library (minimal)
PYTHON_LIB=$(python3 -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VERSION}"
cp -r "${PYTHON_LIB}/"*.py "${APPDIR}/usr/lib/python${PYTHON_VERSION}/" 2>/dev/null || true
for subdir in collections encodings importlib json logging urllib email http; do
    if [ -d "${PYTHON_LIB}/${subdir}" ]; then
        cp -r "${PYTHON_LIB}/${subdir}" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/"
    fi
done

# Copy lib-dynload
if [ -d "${PYTHON_LIB}/lib-dynload" ]; then
    cp -r "${PYTHON_LIB}/lib-dynload" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/"
fi

deactivate

# Download appimagetool if not present
APPIMAGETOOL="${BUILD_DIR}/appimagetool-x86_64.AppImage"
if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "=== Downloading appimagetool ==="
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" \
        -O "${APPIMAGETOOL}"
    chmod +x "${APPIMAGETOOL}"
fi

# Build AppImage (use extract-and-run to avoid FUSE requirement)
echo "=== Creating AppImage ==="
cd "${BUILD_DIR}"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "${APPIMAGETOOL}" --no-appstream "${APPDIR}"

# Move to dist
mkdir -p "${PROJECT_DIR}/dist"
mv Razer_Control_Center-x86_64.AppImage "${PROJECT_DIR}/dist/"

echo ""
echo "=== Build complete ==="
echo "AppImage: ${PROJECT_DIR}/dist/Razer_Control_Center-x86_64.AppImage"
echo ""
echo "Run with: ./dist/Razer_Control_Center-x86_64.AppImage"
