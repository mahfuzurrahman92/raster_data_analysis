import os
import uuid
import numpy as np
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from PIL import Image, ImageDraw

app = Flask(
    __name__,
    template_folder="app/templates",
    static_folder="app/static"
)

# Upload / Output Configurations
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"

ALLOWED_EXTENSIONS = {"tif", "tiff", "jpg", "jpeg", "png", "img"}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB Limit

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Color Palettes for Grid & PNG Export
COLOR_PALETTES = {
    "viridis": [
        (68, 1, 84), (72, 35, 116), (64, 67, 135), (52, 94, 141),
        (41, 120, 142), (32, 144, 141), (34, 168, 132), (68, 190, 112),
        (121, 209, 81), (189, 223, 38), (253, 231, 37)
    ],
    "turbo": [
        (48, 18, 59), (70, 107, 227), (40, 187, 246), (36, 248, 160),
        (162, 252, 60), (238, 207, 48), (251, 126, 33), (208, 33, 13),
        (122, 4, 3)
    ],
    "grayscale": [
        (0, 0, 0), (255, 255, 255)
    ],
    "terrain": [
        (51, 102, 0), (102, 153, 0), (204, 204, 102), (153, 102, 51),
        (204, 153, 102), (255, 255, 255)
    ]
}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_color_from_value(val, palette_name="viridis"):
    """Maps a normalized value [0, 1] to an RGB color tuple using selected palette."""
    if val is None or np.isnan(val):
        return (30, 30, 30)  # Dark Gray for NoData
    
    val = float(np.clip(val, 0.0, 1.0))
    colors = COLOR_PALETTES.get(palette_name.lower(), COLOR_PALETTES["viridis"])
    
    if len(colors) == 2:
        c1, c2 = colors[0], colors[1]
        r = int(c1[0] + val * (c2[0] - c1[0]))
        g = int(c1[1] + val * (c2[1] - c1[1]))
        b = int(c1[2] + val * (c2[2] - c1[2]))
        return (r, g, b)
    
    idx = val * (len(colors) - 1)
    lower_idx = int(np.floor(idx))
    upper_idx = int(np.ceil(idx))
    
    if lower_idx == upper_idx:
        return colors[lower_idx]
    
    weight = idx - lower_idx
    c1, c2 = colors[lower_idx], colors[upper_idx]
    r = int(c1[0] * (1 - weight) + c2[0] * weight)
    g = int(c1[1] * (1 - weight) + c2[1] * weight)
    b = int(c1[2] * (1 - weight) + c2[2] * weight)
    return (r, g, b)


def convert_image_to_geotiff(input_path, output_path):
    """Converts non-raster images (JPG, PNG, JPEG) into temporary GeoTIFF format for unified processing."""
    with Image.open(input_path) as img:
        img_rgb = img.convert("RGB")
        arr = np.array(img_rgb)
        
        height, width, bands = arr.shape
        transform = from_origin(0, 0, 1, 1)

        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=bands,
            dtype=arr.dtype,
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            for b in range(bands):
                dst.write(arr[:, :, b], b + 1)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/api/read-raster", methods=["POST"])
def read_raster():
    """Validates uploaded image/raster, reads metadata, and returns stats for selected band."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file portion in request."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    if not (file and allowed_file(file.filename)):
        return jsonify({"success": False, "error": "Invalid format. Supported: .tif, .tiff, .jpg, .jpeg, .png, .img"}), 400

    try:
        orig_filename = secure_filename(file.filename)
        ext = orig_filename.rsplit(".", 1)[1].lower()
        file_id = f"{uuid.uuid4().hex[:8]}_{orig_filename}"
        file_path = UPLOAD_FOLDER / file_id
        file.save(file_path)

        # Handle standard image inputs by converting them internally to GeoTIFF structure
        working_file_path = file_path
        if ext in ["jpg", "jpeg", "png", "img"]:
            geotiff_converted_path = UPLOAD_FOLDER / f"converted_{file_id}.tif"
            convert_image_to_geotiff(file_path, geotiff_converted_path)
            working_file_path = geotiff_converted_path

        band_param = request.form.get("band", 1, type=int)
        rows_param = request.form.get("rows", 20, type=int)
        cols_param = request.form.get("cols", 20, type=int)

        rows_param = max(5, min(60, rows_param))
        cols_param = max(5, min(60, cols_param))

        with rasterio.open(working_file_path) as src:
            total_bands = src.count
            width = src.width
            height = src.height
            crs_str = str(src.crs) if src.crs else "Unprojected Image Space"
            dtype_str = str(src.dtypes[0])

            selected_band = max(1, min(total_bands, band_param))
            band_data = src.read(selected_band)
            nodata_val = src.nodatavals[selected_band - 1]

            if nodata_val is not None:
                valid_mask = (band_data != nodata_val)
                if np.isnan(nodata_val):
                    valid_mask &= ~np.isnan(band_data)
            else:
                valid_mask = ~np.isnan(band_data)

            if np.any(valid_mask):
                valid_pixels = band_data[valid_mask].astype(np.float64)
                min_val = float(np.min(valid_pixels))
                max_val = float(np.max(valid_pixels))
                mean_val = float(np.mean(valid_pixels))
            else:
                min_val = max_val = mean_val = 0.0

            sampled_raw = src.read(
                selected_band,
                out_shape=(rows_param, cols_param),
                resampling=Resampling.bilinear
            ).astype(np.float64)

            if nodata_val is not None:
                if np.isnan(nodata_val):
                    sampled_raw[np.isnan(sampled_raw)] = np.nan
                else:
                    sampled_raw[sampled_raw == nodata_val] = np.nan

            sampled_norm = np.full_like(sampled_raw, np.nan, dtype=np.float64)
            if max_val > min_val:
                valid_samp = ~np.isnan(sampled_raw)
                sampled_norm[valid_samp] = (sampled_raw[valid_samp] - min_val) / (max_val - min_val)
                sampled_norm[valid_samp] = np.clip(sampled_norm[valid_samp], 0.0, 1.0)
            elif max_val == min_val:
                valid_samp = ~np.isnan(sampled_raw)
                sampled_norm[valid_samp] = 0.0

            raw_grid_list = np.where(np.isnan(sampled_raw), None, np.round(sampled_raw, 2)).tolist()
            norm_grid_list = np.where(np.isnan(sampled_norm), None, np.round(sampled_norm, 4)).tolist()

        return jsonify({
            "success": True,
            "file_id": file_id,
            "filename": orig_filename,
            "width": width,
            "height": height,
            "total_bands": total_bands,
            "selected_band": selected_band,
            "crs": crs_str,
            "dtype": dtype_str,
            "nodata": "None" if nodata_val is None else str(nodata_val),
            "stats": {
                "min": round(min_val, 4),
                "max": round(max_val, 4),
                "mean": round(mean_val, 4)
            },
            "grid_rows": rows_param,
            "grid_cols": cols_param,
            "raw_grid": raw_grid_list,
            "norm_grid": norm_grid_list
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Error reading file: {str(e)}"}), 500


@app.route("/api/normalize", methods=["POST"])
def normalize_raster():
    """Normalizes all bands and exports into requested format (.tif, .png, .jpg)."""
    data = request.get_json() or {}
    file_id = data.get("file_id")
    export_format = data.get("format", "tif").lower()

    if not file_id:
        return jsonify({"success": False, "error": "File ID missing."}), 400

    file_id = secure_filename(file_id)
    input_path = UPLOAD_FOLDER / file_id
    
    ext = file_id.rsplit(".", 1)[1].lower() if "." in file_id else ""
    if ext in ["jpg", "jpeg", "png", "img"]:
        input_path = UPLOAD_FOLDER / f"converted_{file_id}.tif"

    if not input_path.exists():
        return jsonify({"success": False, "error": "Uploaded file not found on server."}), 404

    base_name = file_id.rsplit(".", 1)[0]
    output_filename = f"normalized_{base_name}.{export_format}"
    output_path = OUTPUT_FOLDER / output_filename

    try:
        with rasterio.open(input_path) as src:
            meta = src.meta.copy()
            band_count = src.count

            normalized_bands = []
            for b_idx in range(1, band_count + 1):
                band_data = src.read(b_idx)
                nodata_val = src.nodatavals[b_idx - 1]

                if nodata_val is not None:
                    valid_mask = (~np.isnan(band_data)) if np.isnan(nodata_val) else (band_data != nodata_val)
                else:
                    valid_mask = ~np.isnan(band_data)

                norm_band = np.full(band_data.shape, np.nan, dtype=np.float32)

                if np.any(valid_mask):
                    valid_pixels = band_data[valid_mask].astype(np.float32)
                    b_min, b_max = np.min(valid_pixels), np.max(valid_pixels)

                    if b_max > b_min:
                        norm_band[valid_mask] = (valid_pixels - b_min) / (b_max - b_min)
                    else:
                        norm_band[valid_mask] = 0.0

                normalized_bands.append(norm_band)

            if export_format in ["tif", "tiff"]:
                meta.update({
                    "dtype": "float32",
                    "nodata": np.nan,
                    "compress": "deflate"
                })
                with rasterio.open(output_path, "w", **meta) as dst:
                    for idx, norm_arr in enumerate(normalized_bands, start=1):
                        dst.write(norm_arr, idx)

            elif export_format in ["png", "jpg", "jpeg"]:
                # Convert normalized bands [0.0 - 1.0] to 8-bit image array [0 - 255]
                if band_count >= 3:
                    rgb_stack = [np.nan_to_num(normalized_bands[i], nan=0.0) * 255.0 for i in range(3)]
                    rgb_arr = np.stack(rgb_stack, axis=-1).astype(np.uint8)
                    img = Image.fromarray(rgb_arr, mode="RGB")
                else:
                    gray_arr = (np.nan_to_num(normalized_bands[0], nan=0.0) * 255.0).astype(np.uint8)
                    img = Image.fromarray(gray_arr, mode="L")

                if export_format in ["jpg", "jpeg"]:
                    img = img.convert("RGB")
                    img.save(output_path, format="JPEG", quality=95)
                else:
                    img.save(output_path, format="PNG")

        return jsonify({
            "success": True,
            "message": "Full-resolution normalization completed successfully.",
            "download_url": f"/download/{output_filename}",
            "filename": output_filename
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Normalization failed: {str(e)}"}), 500


@app.route("/api/export-csv", methods=["POST"])
def export_csv():
    data = request.get_json() or {}
    grid = data.get("grid")
    grid_type = data.get("type", "raster_grid")

    if not grid or not isinstance(grid, list):
        return jsonify({"success": False, "error": "Invalid grid data provided."}), 400

    try:
        output_filename = f"{grid_type}_{uuid.uuid4().hex[:6]}.csv"
        file_path = OUTPUT_FOLDER / output_filename

        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        with open(file_path, "w") as f:
            header = ["Row/Col"] + [f"C{c+1}" for c in range(cols)]
            f.write(",".join(header) + "\n")

            for r_idx, row_vals in enumerate(grid):
                row_str = [f"R{r_idx+1}"] + [("" if v is None else str(v)) for v in row_vals]
                f.write(",".join(row_str) + "\n")

        return jsonify({
            "success": True,
            "download_url": f"/download/{output_filename}",
            "filename": output_filename
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate CSV: {str(e)}"}), 500


@app.route("/api/export-png", methods=["POST"])
def export_png():
    data = request.get_json() or {}
    grid = data.get("grid")
    palette = data.get("palette", "viridis")
    grid_type = data.get("type", "normalized")

    if not grid or not isinstance(grid, list):
        return jsonify({"success": False, "error": "Invalid grid data."}), 400

    try:
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0
        cell_size, margin = 35, 40

        img_w = cols * cell_size + (margin * 2)
        img_h = rows * cell_size + (margin * 2)

        img = Image.new("RGB", (img_w, img_h), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        for r in range(rows):
            for c in range(cols):
                val = grid[r][c]
                x1 = margin + c * cell_size
                y1 = margin + r * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size

                if val is None:
                    color = (30, 41, 59)
                else:
                    if grid_type == "raw":
                        all_vals = [v for row in grid for v in row if v is not None]
                        min_v, max_v = (min(all_vals), max(all_vals)) if all_vals else (0, 1)
                        norm_v = (val - min_v) / (max_v - min_v) if max_v > min_v else 0.5
                        color = get_color_from_value(norm_v, palette)
                    else:
                        color = get_color_from_value(val, palette)

                draw.rectangle([x1, y1, x2, y2], fill=color, outline=(30, 41, 59))

        output_filename = f"{grid_type}_visual_{uuid.uuid4().hex[:6]}.png"
        output_path = OUTPUT_FOLDER / output_filename
        img.save(output_path)

        return jsonify({
            "success": True,
            "download_url": f"/download/{output_filename}",
            "filename": output_filename
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate PNG: {str(e)}"}), 500


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(app.config["OUTPUT_FOLDER"], safe_name, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)