document.addEventListener('DOMContentLoaded', () => {
    // Dynamic Typing Hero Animation
    const phrases = [
        "Welcome to Raster Data Analyzer",
        "Welcome to Spatial Data Processor",
        "Welcome to GeoTIFF Normalizer",
        "Welcome to GIS Analysis Lab"
    ];
    let phraseIdx = 0;
    let charIdx = 0;
    let isDeleting = false;
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

    // DOM Selection
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileDetails = document.getElementById('file-details');
    const fileNameDisplay = document.getElementById('file-name');
    const fileSizeDisplay = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file-btn');
    const normalizeBtn = document.getElementById('normalize-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressPercent = document.getElementById('progress-percent');
    const resultContainer = document.getElementById('result-container');
    
    // Result Meta Displays
    const metaWidth = document.getElementById('meta-width');
    const metaHeight = document.getElementById('meta-height');
    const metaBands = document.getElementById('meta-bands');
    const metaCrs = document.getElementById('meta-crs');
    const metaDtype = document.getElementById('meta-dtype');
    const downloadBtn = document.getElementById('download-btn');

    let selectedFile = null;

    // File selection trigger
    browseBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    // Drag and Drop Events
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    function handleFileSelection(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== 'tif' && ext !== 'tiff') {
            alert('Unsupported file type! Please upload a valid .tif or .tiff GeoTIFF raster.');
            return;
        }

        selectedFile = file;
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        
        fileDetails.classList.remove('hidden');
        normalizeBtn.disabled = false;
        resultContainer.classList.add('hidden');
    }

    removeFileBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        fileDetails.classList.add('hidden');
        normalizeBtn.disabled = true;
        resultContainer.classList.add('hidden');
        progressContainer.classList.add('hidden');
    });

    // Process Execute Request
    normalizeBtn.addEventListener('click', () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        const xhr = new XMLHttpRequest();
        
        // Setup initial processing state
        normalizeBtn.disabled = true;
        progressContainer.classList.remove('hidden');
        resultContainer.classList.add('hidden');
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 90); // Cap upload visual at 90% until backend computes
                progressFill.style.width = percent + '%';
                progressPercent.textContent = percent + '%';
            }
        });

        xhr.onreadystatechange = () => {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                progressFill.style.width = '100%';
                progressPercent.textContent = '100%';

                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.success) {
                        setTimeout(() => {
                            displayResults(response);
                        }, 400);
                    } else {
                        alert('Server processing error: ' + response.message);
                    }
                } else {
                    try {
                        const errResp = JSON.parse(xhr.responseText);
                        alert('Error: ' + errResp.message);
                    } catch (e) {
                        alert('An unknown server communication error occurred.');
                    }
                }
                normalizeBtn.disabled = false;
            }
        };

        xhr.open('POST', '/api/normalize', true);
        xhr.send(formData);
    });

    function displayResults(data) {
        metaWidth.textContent = data.width + ' px';
        metaHeight.textContent = data.height + ' px';
        metaBands.textContent = data.bands;
        metaCrs.textContent = data.crs;
        metaDtype.textContent = data.original_dtype;
        downloadBtn.href = data.download_url;

        progressContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
    }
});