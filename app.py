import os
import rasterio
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__, 
            template_folder='app/templates', 
            static_folder='app/static')

# Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'outputs')
ALLOWED_EXTENSIONS = {'tif', 'tiff'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MB Upload Limit

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Optional MongoDB Connection Setup
mongo_client = None
db = None
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/rasterlab_db")

try:
    from pymongo import MongoClient
    mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    mongo_client.server_info()  # Trigger connection check
    db = mongo_client.get_database()
    print("MongoDB Connected Successfully (Optional Data Logging Enabled)")
except Exception:
    print("MongoDB Not Connected. Running in Standalone Core Mode.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/normalize', methods=['POST'])
def normalize_raster():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file partition found in request.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected for upload.'}), 400
    
    if not (file and allowed_file(file.filename)):
        return jsonify({'success': False, 'message': 'Invalid file format. Only .tif and .tiff supported.'}), 400

    try:
        filename = secure_filename(file.filename)
        unique_id = uuid.uuid4().hex[:8]
        input_filename = f"{unique_id}_{filename}"
        output_filename = f"normalized_{unique_id}_{filename}"
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        file.save(input_path)

        # Raster processing execution block
        with rasterio.open(input_path) as src:
            meta = src.meta.copy()
            band_count = src.count
            width = src.width
            height = src.height
            crs_str = str(src.crs) if src.crs else "Undefined/Unknown"
            dtype_str = str(src.dtypes[0])

            # Processing container array initialization
            normalized_bands = []

            for b_idx in range(1, band_count + 1):
                band_data = src.read(b_idx)
                nodata_val = src.nodatavals[b_idx - 1]

                # Mask building for NoData handling
                if nodata_val is not None:
                    valid_mask = (band_data != nodata_val)
                    if np.isnan(nodata_val):
                        valid_mask = valid_mask & (~np.isnan(band_data))
                else:
                    valid_mask = ~np.isnan(band_data)

                # Output array with NaN for masked pixels
                norm_band = np.full(band_data.shape, np.nan, dtype=np.float32)

                if np.any(valid_mask):
                    valid_pixels = band_data[valid_mask].astype(np.float32)
                    b_min = np.min(valid_pixels)
                    b_max = np.max(valid_pixels)

                    if b_max > b_min:
                        norm_band[valid_mask] = (valid_pixels - b_min) / (b_max - b_min)
                    else:
                        norm_band[valid_mask] = 0.0

                normalized_bands.append(norm_band)

            # Metadata updates for float output and compressed storage
            meta.update({
                'dtype': 'float32',
                'count': band_count,
                'nodata': np.nan,
                'compress': 'deflate'
            })

            with rasterio.open(output_path, 'w', **meta) as dst:
                for idx, norm_data in enumerate(normalized_bands, start=1):
                    dst.write(norm_data, idx)

        # Optional MongoDB record persistence
        if db is not None:
            try:
                db.processing_logs.insert_one({
                    "original_filename": filename,
                    "output_filename": output_filename,
                    "width": width,
                    "height": height,
                    "bands": band_count,
                    "crs": crs_str,
                    "original_dtype": dtype_str
                })
            except Exception as mongo_err:
                print(f"MongoDB non-blocking error: {mongo_err}")

        return jsonify({
            'success': True,
            'message': 'Raster min-max normalization completed successfully.',
            'output_filename': output_filename,
            'download_url': f"/download/{output_filename}",
            'width': width,
            'height': height,
            'bands': band_count,
            'crs': crs_str,
            'original_dtype': dtype_str
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Processing Error: {str(e)}'}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    safe_name = secure_filename(filename)
    return send_from_directory(app.config['OUTPUT_FOLDER'], safe_name, as_attachment=True)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)