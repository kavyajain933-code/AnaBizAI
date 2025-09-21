// static/script.js
let uploadedFiles = [];
let activeCharts = [];
let generatedChartsData = []; // Store chart data for the explanation feature

document.addEventListener('DOMContentLoaded', () => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const explainBtn = document.getElementById('explainBtn');
    const fileInput = document.getElementById('fileInput');

    if (analyzeBtn) analyzeBtn.addEventListener('click', getAnalysis);
    if (explainBtn) explainBtn.addEventListener('click', getChartExplanation);
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            addFiles(fileInput.files);
            fileInput.value = '';
        });
    }
});

function addFiles(newFiles) {
    const existingFileNames = new Set(uploadedFiles.map(f => f.name));
    for (const file of newFiles) {
        if (!existingFileNames.has(file.name)) uploadedFiles.push(file);
    }
    updateFileListUI();
}

function updateFileListUI() {
    const fileListDiv = document.getElementById('fileList');
    if (uploadedFiles.length > 0) {
        let fileNamesHTML = "<ul>";
        for (const file of uploadedFiles) {
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
    if (uploadedFiles.length === 0) {
        alert("Please select one or more files first!");
        return;
    }

    const loader = document.getElementById('loader');
    const resultDiv = document.getElementById('result');
    const explanationSection = document.getElementById('explanation-section');
    const analysisType = document.getElementById('analysis-meta').dataset.analysisType;

    // Reset UI for new analysis
    loader.style.display = 'block';
    resultDiv.innerHTML = '';
    explanationSection.style.display = 'none';
    document.getElementById('explanation-result').innerHTML = '';
    document.getElementById('charts-container').innerHTML = ''; // Clear old charts
    activeCharts.forEach(chart => chart.destroy());
    activeCharts = [];
    generatedChartsData = []; // Clear old chart data

    const formData = new FormData();
    uploadedFiles.forEach(file => formData.append('files[]', file));
    formData.append('analysis_type', analysisType);

    try {
        const response = await fetch(`/api/generate`, { method: 'POST', body: formData });
        const data = await response.json();

        if (response.ok) {
            resultDiv.innerHTML = marked.parse(data.analysis_result);
            if (data.charts_data && data.charts_data.length > 0) {
                generatedChartsData = data.charts_data; // Save chart data
                renderCharts(generatedChartsData);
                explanationSection.style.display = 'block'; // Show explanation prompt
            }
        } else {
            resultDiv.innerHTML = `<p style="color: #f85149;">Error: ${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `<p style="color: #f85149;">An error occurred.</p>`;
    } finally {
        loader.style.display = 'none';
    }
}

async function getChartExplanation() {
    if (uploadedFiles.length === 0 || generatedChartsData.length === 0) {
        alert('Cannot explain charts without file and chart context.');
        return;
    }

    const loader = document.getElementById('explanation-loader');
    const resultContainer = document.getElementById('explanation-result');
    const explainBtn = document.getElementById('explainBtn');

    loader.style.display = 'block';
    explainBtn.style.display = 'none';
    resultContainer.innerHTML = '';

    const formData = new FormData();
    uploadedFiles.forEach(file => formData.append('files[]', file));
    formData.append('charts_data', JSON.stringify(generatedChartsData));

    try {
        const response = await fetch('/api/explain_charts', { method: 'POST', body: formData });
        const data = await response.json();

        if (response.ok) {
            resultContainer.innerHTML = marked.parse(data.explanation);
        } else {
            resultContainer.innerHTML = `<p style="color: #f85149;">Error: ${data.error}</p>`;
        }
    } catch (error) {
        console.error('Error:', error);
        resultContainer.innerHTML = `<p style="color: #f85149;">An error occurred while getting the explanation.</p>`;
    } finally {
        loader.style.display = 'none';
    }
}

function renderCharts(chartsData) {
    const chartsContainer = document.getElementById('charts-container');
    chartsContainer.innerHTML = '';
    activeCharts.forEach(chart => chart.destroy());
    activeCharts = [];

    chartsData.forEach((chartData, index) => {
        const chartWrapper = document.createElement('div');
        // This simple wrapper is what causes the 'slim' look, but it's what was there before.
        chartWrapper.style.marginBottom = '2rem';
        const title = document.createElement('h3');
        title.innerText = chartData.title;
        const canvas = document.createElement('canvas');
        
        chartWrapper.appendChild(title);
        chartWrapper.appendChild(canvas);
        chartsContainer.appendChild(chartWrapper);

        const newChart = new Chart(canvas.getContext('2d'), {
            type: chartData.type,
            data: chartData.data,
            options: {
                responsive: true,
                maintainAspectRatio: true, // This contributes to the slim look in a narrow container
                plugins: { legend: { labels: { color: '#e0e0e0' } } },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        ticks: { color: '#e0e0e0' }, 
                        grid: { color: '#222222' } 
                    },
                    x: { 
                        ticks: { color: '#e0e0e0' }, 
                        grid: { color: '#222222' } 
                    }
                }
            }
        });
        activeCharts.push(newChart);
    });
}