# RasterLab – GeoTIFF Raster Data Analyzer

RasterLab is a high-performance web dashboard designed for automated Min-Max normalization of multi-band GeoTIFF spatial rasters while preserving spatial reference, affine transformation, and coordinate reference system (CRS) metadata.

## Tech Stack
* **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 Variables, FontAwesome 6
* **Backend**: Python (Flask framework)
* **Geospatial Processing Engine**: Rasterio, NumPy
* **Data Storage (Optional)**: MongoDB

## System Installation & Setup (VS Code / Windows)

### 1. Prerequisites
* Python 3.9+ installed on Windows.
* VS Code IDE.

### 2. Environment Setup
Open terminal inside VS Code in your root project folder `raster_data_analyzer`:

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment on Windows
venv\Scripts\activate

# Upgrade PIP
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt