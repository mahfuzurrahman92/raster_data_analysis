document.addEventListener('DOMContentLoaded', () => {
    const phrases = [
        "Welcome to Raster Data Analyzer",
        "Welcome to Image Normalization Lab",
        "Welcome to GeoTIFF & JPG Processor"
    ];
    let phraseIdx = 0, charIdx = 0, isDeleting = false;
    const typedTextSpan = document.getElementById("typed-text");

    function typeEffect() {
        const currentPhrase = phrases[phraseIdx];
        if (isDeleting) {
            typedTextSpan.textContent = currentPhrase.substring(0, charIdx - 1);
            charIdx--;
        } else {
            typedTextSpan.textContent = currentPhrase.substring(0, charIdx + 1);
            charIdx++;
        }

        let typeSpeed = isDeleting ? 40 : 80;
        if (!isDeleting && charIdx === currentPhrase.length) {
            typeSpeed = 2000;
            isDeleting = true;
        } else if (isDeleting && charIdx === 0) {
            isDeleting = false;
            phraseIdx = (phraseIdx + 1) % phrases.length;
            typeSpeed = 500;
        }
        setTimeout(typeEffect, typeSpeed);
    }
    typeEffect();

    const PALETTES = {
        viridis: [[68, 1, 84], [72, 35, 116], [64, 67, 135], [52, 94, 141], [41, 120, 142], [32, 144, 141], [34, 168, 132], [68, 190, 112], [121, 209, 81], [189, 223, 38], [253, 231, 37]],
        turbo: [[48, 18, 59], [70, 107, 227], [40, 187, 246], [36, 248, 160], [162, 252, 60], [238, 207, 48], [251, 126, 33], [208, 33, 13], [122, 4, 3]],
        grayscale: [[0, 0, 0], [255, 255, 255]],
        terrain: [[51, 102, 0], [102, 153, 0], [204, 204, 102], [153, 102, 51], [204, 153, 102], [255, 255, 255]]
    };

    function getColorForValue(val, paletteName = 'viridis') {
        if (val === null || isNaN(val)) return 'rgb(30, 30, 30)';
        val = Math.max(0, Math.min(1, val));
        const colors = PALETTES[paletteName] || PALETTES.viridis;
        
        if (colors.length === 2) {
            const r = Math.round(colors[0][0] + val * (colors[1][0] - colors[0][0]));
            const g = Math.round(colors[0][1] + val * (colors[1][1] - colors[0][1]));
            const b = Math.round(colors[0][2] + val * (colors[1][2] - colors[0][2]));
            return `rgb(${r}, ${g}, ${b})`;
        }

        const idx = val * (colors.length - 1);
        const lower = Math.floor(idx);
        const upper = Math.ceil(idx);
        if (lower === upper) return `rgb(${colors[lower].join(',')})`;

        const weight = idx - lower;
        const c1 = colors[lower], c2 = colors[upper];
        const r = Math.round(c1[0] * (1 - weight) + c2[0] * weight);
        const g = Math.round(c1[1] * (1 - weight) + c2[1] * weight);
        const b = Math.round(c1[2] * (1 - weight) + c2[2] * weight);
        return `rgb(${r}, ${g}, ${b})`;
    }

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileDetails = document.getElementById('file-details');
    const fileNameDisplay = document.getElementById('file-name');
    const fileSizeDisplay = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file-btn');

    const metadataCard = document.getElementById('metadata-card');
    const rawGridCard = document.getElementById('raw-grid-card');
    const normalizeCard = document.getElementById('normalize-card');
    const normResultCard = document.getElementById('normalized-result-card');

    const metaWidth = document.getElementById('meta-width');
    const metaHeight = document.getElementById('meta-height');
    const metaBands = document.getElementById('meta-bands');
    const metaCrs = document.getElementById('meta-crs');
    const metaDtype = document.getElementById('meta-dtype');
    const metaNodata = document.getElementById('meta-nodata');
    const statMin = document.getElementById('stat-min');
    const statMax = document.getElementById('stat-max');
    const statMean = document.getElementById('stat-mean');

    const bandSelect = document.getElementById('band-select');
    const gridRowsInput = document.getElementById('grid-rows');
    const gridColsInput = document.getElementById('grid-cols');
    const buildGridBtn = document.getElementById('build-grid-btn');
    const normalizeBtn = document.getElementById('normalize-btn');
    const exportFormatSelect = document.getElementById('export-format-select');

    const rawPixelTable = document.getElementById('raw-pixel-table');
    const normPixelTable = document.getElementById('norm-pixel-table');

    const rawToggleLabels = document.getElementById('raw-toggle-labels');
    const rawToggleValues = document.getElementById('raw-toggle-values');
    const normToggleLabels = document.getElementById('norm-toggle-labels');
    const normToggleValues = document.getElementById('norm-toggle-values');
    const paletteSelect = document.getElementById('palette-select');

    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const downloadFileBtn = document.getElementById('download-file-btn');

    const exportRawCsvBtn = document.getElementById('export-raw-csv-btn');
    const exportRawPngBtn = document.getElementById('export-raw-png-btn');
    const exportNormCsvBtn = document.getElementById('export-norm-csv-btn');
    const exportNormPngBtn = document.getElementById('export-norm-png-btn');

    let currentFile = null;
    let currentFileId = null;
    let rasterMetadata = null;

    browseBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileSelection(e.target.files[0]);
    });

    ['dragenter', 'dragover'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length > 0) handleFileSelection(e.dataTransfer.files[0]);
    });

    function handleFileSelection(file) {
        const validExts = ['tif', 'tiff', 'jpg', 'jpeg', 'png', 'img'];
        const ext = file.name.split('.').pop().toLowerCase();
        if (!validExts.includes(ext)) {
            alert('Invalid file format! Supported formats: .tif, .tiff, .jpg, .jpeg, .png, .img');
            return;
        }

        currentFile = file;
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        fileDetails.classList.remove('hidden');

        normResultCard.classList.add('hidden');
        loadRasterMetadata(1);
    }

    removeFileBtn.addEventListener('click', () => {
        currentFile = null;
        currentFileId = null;
        fileInput.value = '';
        fileDetails.classList.add('hidden');
        metadataCard.classList.add('hidden');
        rawGridCard.classList.add('hidden');
        normalizeCard.classList.add('hidden');
        normResultCard.classList.add('hidden');
    });

    function loadRasterMetadata(bandNum) {
        if (!currentFile) return;

        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('band', bandNum);
        formData.append('rows', gridRowsInput.value);
        formData.append('cols', gridColsInput.value);

        fetch('/api/read-raster', {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert('Error reading file: ' + data.error);
                return;
            }

            rasterMetadata = data;
            currentFileId = data.file_id;

            metaWidth.textContent = data.width + ' px';
            metaHeight.textContent = data.height + ' px';
            metaBands.textContent = data.total_bands;
            metaCrs.textContent = data.crs;
            metaDtype.textContent = data.dtype;
            metaNodata.textContent = data.nodata;

            statMin.textContent = data.stats.min;
            statMax.textContent = data.stats.max;
            statMean.textContent = data.stats.mean;

            bandSelect.innerHTML = '';
            for (let i = 1; i <= data.total_bands; i++) {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = `Band ${i}`;
                if (i === data.selected_band) opt.selected = true;
                bandSelect.appendChild(opt);
            }

            metadataCard.classList.remove('hidden');
            normalizeCard.classList.remove('hidden');

            renderRawTable();
            if (rasterMetadata.norm_grid) renderNormTable();
        })
        .catch(err => {
            alert('Server error: ' + err.message);
        });
    }

    bandSelect.addEventListener('change', () => loadRasterMetadata(parseInt(bandSelect.value)));
    buildGridBtn.addEventListener('click', () => loadRasterMetadata(parseInt(bandSelect.value)));

    function renderRawTable() {
        if (!rasterMetadata || !rasterMetadata.raw_grid) return;

        const grid = rasterMetadata.raw_grid;
        const rows = grid.length;
        const cols = rows > 0 ? grid[0].length : 0;
        const showLabels = rawToggleLabels.checked;
        const showValues = rawToggleValues.checked;

        let html = '';
        if (showLabels) {
            html += '<thead><tr><th>R/C</th>';
            for (let c = 1; c <= cols; c++) html += `<th>C${c}</th>`;
            html += '</tr></thead>';
        }

        html += '<tbody>';
        for (let r = 0; r < rows; r++) {
            html += '<tr>';
            if (showLabels) html += `<td class="row-header">R${r + 1}</td>`;
            for (let c = 0; c < cols; c++) {
                const val = grid[r][c];
                const displayVal = (val === null || !showValues) ? '' : val;
                html += `<td style="background-color: #121824; color: #e2e8f0;">${displayVal}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody>';

        rawPixelTable.innerHTML = html;
        rawGridCard.classList.remove('hidden');
    }

    function renderNormTable() {
        if (!rasterMetadata || !rasterMetadata.norm_grid) return;

        const grid = rasterMetadata.norm_grid;
        const rows = grid.length;
        const cols = rows > 0 ? grid[0].length : 0;
        const showLabels = normToggleLabels.checked;
        const showValues = normToggleValues.checked;
        const selectedPalette = paletteSelect.value;

        let html = '';
        if (showLabels) {
            html += '<thead><tr><th>R/C</th>';
            for (let c = 1; c <= cols; c++) html += `<th>C${c}</th>`;
            html += '</tr></thead>';
        }

        html += '<tbody>';
        for (let r = 0; r < rows; r++) {
            html += '<tr>';
            if (showLabels) html += `<td class="row-header">R${r + 1}</td>`;
            for (let c = 0; c < cols; c++) {
                const val = grid[r][c];
                const bg = getColorForValue(val, selectedPalette);
                const displayVal = (val === null || !showValues) ? '' : val;
                const textColor = (selectedPalette === 'grayscale' && val > 0.5) ? '#000' : '#fff';
                html += `<td style="background-color: ${bg}; color: ${textColor};">${displayVal}</td>`;
            }
            html += '</tr>';
        }
        html += '</tbody>';

        normPixelTable.innerHTML = html;
        normResultCard.classList.remove('hidden');
    }

    rawToggleLabels.addEventListener('change', renderRawTable);
    rawToggleValues.addEventListener('change', renderRawTable);
    normToggleLabels.addEventListener('change', renderNormTable);
    normToggleValues.addEventListener('change', renderNormTable);
    paletteSelect.addEventListener('change', renderNormTable);

    normalizeBtn.addEventListener('click', () => {
        if (!currentFileId) return;

        progressContainer.classList.remove('hidden');
        progressFill.style.width = '40%';
        progressPercent.textContent = '40%';

        const selectedFormat = exportFormatSelect.value;

        fetch('/api/normalize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_id: currentFileId, format: selectedFormat })
        })
        .then(res => res.json())
        .then(data => {
            progressFill.style.width = '100%';
            progressPercent.textContent = '100%';

            setTimeout(() => progressContainer.classList.add('hidden'), 500);

            if (!data.success) {
                alert('Normalization Error: ' + data.error);
                return;
            }

            downloadFileBtn.href = data.download_url;
            downloadFileBtn.innerHTML = `<i class="fa-solid fa-download"></i> Download Normalized ${selectedFormat.toUpperCase()} File`;
            renderNormTable();
        })
        .catch(err => {
            progressContainer.classList.add('hidden');
            alert('Server Error during normalization: ' + err.message);
        });
    });

    exportRawCsvBtn.addEventListener('click', () => {
        if (rasterMetadata) triggerCsvExport(rasterMetadata.raw_grid, 'raw_grid');
    });

    exportNormCsvBtn.addEventListener('click', () => {
        if (rasterMetadata) triggerCsvExport(rasterMetadata.norm_grid, 'normalized_grid');
    });

    exportRawPngBtn.addEventListener('click', () => {
        if (rasterMetadata) triggerPngExport(rasterMetadata.raw_grid, paletteSelect.value, 'raw');
    });

    exportNormPngBtn.addEventListener('click', () => {
        if (rasterMetadata) triggerPngExport(rasterMetadata.norm_grid, paletteSelect.value, 'normalized');
    });

    function triggerCsvExport(grid, type) {
        fetch('/api/export-csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grid: grid, type: type })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) window.location.href = data.download_url;
            else alert('CSV Export failed: ' + data.error);
        });
    }

    function triggerPngExport(grid, palette, type) {
        fetch('/api/export-png', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grid: grid, palette: palette, type: type })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) window.location.href = data.download_url;
            else alert('PNG Export failed: ' + data.error);
        });
    }
});