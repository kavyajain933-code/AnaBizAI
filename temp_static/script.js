// This array will hold all the files the user selects
let uploadedFiles = [];

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const fileInput = document.getElementById('fileInput');

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', getAnalysis);
    }

    if(fileInput) {
        fileInput.addEventListener('change', () => {
            addFiles(fileInput.files);
            fileInput.value = ''; 
        });
    }
});

function addFiles(newFiles) {
    const fileListDiv = document.getElementById('fileList');
    const existingFileNames = new Set(uploadedFiles.map(f => f.name));

    for (const file of newFiles) {
        if (!existingFileNames.has(file.name)) {
            uploadedFiles.push(file);
        }
    }
    updateFileListUI();
}

function updateFileListUI() {
    const fileListDiv = document.getElementById('fileList');
    if (uploadedFiles.length > 0) {
        let fileNamesHTML = "<ul>";
        for (const file of uploadedFiles) {
            // UPDATED: Wrapped the filename in a <span> for better styling control
            fileNamesHTML += `<li><span>${file.name}</span><button class="remove-btn" data-filename="${file.name}">&times;</button></li>`;
        }
        fileNamesHTML += "</ul>";
        fileListDiv.innerHTML = fileNamesHTML;

        document.querySelectorAll('.remove-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const filenameToRemove = event.target.getAttribute('data-filename');
                uploadedFiles = uploadedFiles.filter(f => f.name !== filenameToRemove);
                updateFileListUI();
            });
        });

    } else {
        fileListDiv.innerHTML = 'No files selected';
    }
}

async function getAnalysis() {
    const contextInput = document.getElementById('contextInput');
    const resultDiv = document.getElementById('result');
    const loader = document.getElementById('loader');
    const analysisMeta = document.getElementById('analysis-meta');

    const analysisType = analysisMeta.dataset.analysisType;
    const files = uploadedFiles;
    const userContext = contextInput.value;

    if (files.length === 0) {
        alert("Please select one or more files first!");
        return;
    }

    loader.style.display = 'block';
    resultDiv.innerHTML = '';
    
    const formData = new FormData();
    for(const file of files) {
        formData.append('files[]', file);
    }
    formData.append('analysis_type', analysisType);
    formData.append('context', userContext);

    try {
        const response = await fetch(`http://127.0.0.1:5000/api/generate`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok) {
            resultDiv.innerHTML = marked.parse(data.analysis_result);
        } else {
            resultDiv.innerHTML = `<p style="color: #f85149;">Error: ${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p style="color: #f85149;">An error occurred. Make sure the Python server is running and accessible.</p>`;
    } finally {
        loader.style.display = 'none';
    }
}