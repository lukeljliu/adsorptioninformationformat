# -*- coding: utf-8 -*-
"""Web interface for converting .txt to .aif files."""
# pylint: disable-msg=invalid-name

import os
import tempfile
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template_string, request, send_file, after_this_request

from raw2aif import parse, makeAIF, detect_filetype


def generate_plot(meta, ads, des, output_path):
    """
    Generate adsorption isotherm plot.

    Parameters
    ----------
    meta : dict
        Metadata dictionary
    ads : DataFrame
        Adsorption data
    des : DataFrame
        Desorption data
    output_path : str
        Path to save the plot image

    Returns
    -------
    str
        Path to the saved image
    """
    # Get metadata for labels
    material_id = meta.get('material', 'Unknown')
    adsorbate = meta.get('adsorbate', 'N₂')
    temperature = meta.get('temperature', '')
    temp_unit = meta.get('temperature_unit', 'K')
    pressure_unit = meta.get('pressure_unit', 'Torr')
    loading_unit = meta.get('loading_unit', 'cm³ STP/g')

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))

    # Use loading_mass (per gram) if available, otherwise use loading
    if 'loading_mass' in ads.columns:
        ads_y = ads['loading_mass']
        des_y = des['loading_mass'] if len(des) > 0 and 'loading_mass' in des.columns else des['loading']
    else:
        ads_y = ads['loading']
        des_y = des['loading'] if len(des) > 0 else None

    # Plot adsorption data (solid circles)
    if len(ads) > 0:
        ax.scatter(ads['pressure'], ads_y, c='#2E86AB', s=60, marker='o',
                   label='Adsorption', zorder=3, edgecolors='none')

    # Plot desorption data (hollow circles)
    if len(des) > 0 and des_y is not None:
        ax.scatter(des['pressure'], des_y, color='#E94F37', s=60, marker='o',
                   label='Desorption', zorder=3, facecolors='none', edgecolors='#E94F37', linewidths=1.5)

    # Labels and title
    ax.set_xlabel(f'Pressure ({pressure_unit})', fontsize=15)
    ax.set_ylabel(f'Amount Adsorbed ({loading_unit})', fontsize=15)

    # Main title
    ax.set_title(f'Adsorption Isotherm - {material_id}', fontsize=18, fontweight='bold', pad=20)

    # Subtitle below the main title (inside the plot area)
    subtitle = f'{adsorbate} at {temperature} {temp_unit}'
    ax.text(0.5, -0.15, subtitle, transform=ax.transAxes, ha='center', fontsize=13, color='#666', style='italic')

    # Grid
    ax.grid(True, linestyle='--', alpha=0.7, zorder=1)
    ax.set_axisbelow(True)

    # Tick label size
    ax.tick_params(axis='both', labelsize=13)

    # Legend
    ax.legend(loc='lower right', fontsize=13)

    # Set y-axis limits
    all_y = list(ads_y)
    if len(des) > 0 and des_y is not None:
        all_y.extend(des_y)

    if all(y >= 0 for y in all_y):
        # All values are positive, set ymin to 0
        ax.set_ylim(bottom=0)
    # If there are negative values, let matplotlib auto-set the limits

    # Tight layout
    plt.tight_layout()

    # Save figure
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

    return output_path

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adsorption Data Converter - TXT to AIF</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        .upload-area:hover {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .upload-area.dragover {
            border-color: #667eea;
            background: #f0f3ff;
        }
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        .file-input {
            display: none;
        }
        .file-name {
            color: #667eea;
            font-weight: 600;
            margin-top: 10px;
            min-height: 24px;
        }
        .options {
            margin-bottom: 25px;
        }
        .options label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        select, input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .btn-converting {
            background: #764ba2;
        }
        .result {
            margin-top: 25px;
            padding: 20px;
            border-radius: 10px;
            display: none;
        }
        .result.success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .result.error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            display: block;
        }
        .result h3 {
            margin-bottom: 10px;
            font-size: 16px;
        }
        .result.success h3 {
            color: #155724;
        }
        .result.error h3 {
            color: #721c24;
        }
        .download-link {
            display: inline-block;
            margin-top: 15px;
            padding: 12px 25px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
        }
        .download-link:hover {
            background: #218838;
        }
        .info-box {
            background: #e7f3ff;
            border: 1px solid #b3d7ff;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 13px;
            color: #004085;
        }
        .detected-type {
            margin-top: 10px;
            padding: 8px 12px;
            background: #fff3cd;
            border-radius: 6px;
            font-size: 13px;
            display: none;
        }
        .detected-type.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>TXT to AIF Converter</h1>
        <p class="subtitle">Convert adsorption isotherm data files to AIF format</p>

        <div class="info-box">
            <strong>Supported instruments:</strong> Anton Paar Autosorb 6300 XR, Quantachrome ASiQwin, BEL, Micromeritics
        </div>

        <p style="text-align: center; font-size: 12px; color: #888; margin-bottom: 20px;">
            Based on <a href="https://github.com/AIF-development-team/adsorptioninformationformat" target="_blank" style="color: #667eea;">adsorptioninformationformat</a>.
            Added support for Anton Paar Autosorb instruments.
        </p>

        <form id="uploadForm" method="post" enctype="multipart/form-data">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div>Click to select or drag & drop a .txt file</div>
                <div class="file-name" id="fileName"></div>
                <input type="file" name="file" id="fileInput" class="file-input" accept=".txt">
            </div>

            <div class="detected-type" id="detectedType"></div>

            <div class="options">
                <label for="filetype">File Type</label>
                <select name="filetype" id="filetype">
                    <option value="auto">Auto-detect (recommended)</option>
                    <option value="anton_paar">Anton Paar Autosorb 6300 XR</option>
                    <option value="quantachrome">Quantachrome ASiQwin</option>
                    <option value="BELSORP-max">BELSORP-max (.dat)</option>
                    <option value="BEL-csv">BEL-csv (.csv)</option>
                    <option value="micromeritics">Micromeritics (.xls)</option>
                </select>
            </div>

            <div class="options">
                <label for="material_id">Material ID</label>
                <input type="text" name="material_id" id="material_id" placeholder="Enter material ID (e.g., EL1-112)">
            </div>

            <button type="submit" class="btn" id="convertBtn">Convert to AIF</button>
        </form>

        <div class="result" id="result"></div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileName = document.getElementById('fileName');
        const filetype = document.getElementById('filetype');
        const materialId = document.getElementById('material_id');
        const convertBtn = document.getElementById('convertBtn');
        const result = document.getElementById('result');
        const detectedType = document.getElementById('detectedType');

        // 点击上传区域触发文件选择
        uploadArea.addEventListener('click', () => fileInput.click());

        // 文件选择
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                fileName.textContent = e.target.files[0].name;
                detectedType.classList.remove('show');
            }
        });

        // 拖放
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileName.textContent = e.dataTransfer.files[0].name;
                detectedType.classList.remove('show');
            }
        });

        // 表单提交
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!fileInput.files.length) {
                showResult('error', 'Please select a file first.');
                return;
            }

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('filetype', filetype.value);
            formData.append('material_id', materialId.value || file.name.split('.')[0]);

            convertBtn.disabled = true;
            convertBtn.textContent = 'Converting...';
            convertBtn.classList.add('btn-converting');
            result.className = 'result';

            try {
                const response = await fetch('/convert', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    showResult('success', `
                        <h3>✓ Conversion Successful!</h3>
                        <p>Material: ${data.material_id}</p>
                        <p>Adsorption points: ${data.ads_points}</p>
                        <p>Desorption points: ${data.des_points}</p>
                        <div style="margin: 20px 0;">
                            <img src="/plot/${data.plot_file}" alt="Adsorption Isotherm" style="max-width: 100%; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        </div>
                        <a href="/download/${data.output_file}" class="download-link" download>Download AIF File</a>
                    `);
                } else {
                    showResult('error', `<h3>✗ Error</h3><p>${data.error}</p>`);
                }
            } catch (err) {
                showResult('error', `<h3>✗ Error</h3><p>${err.message}</p>`);
            }

            convertBtn.disabled = false;
            convertBtn.textContent = 'Convert to AIF';
            convertBtn.classList.remove('btn-converting');
        });

        function showResult(type, html) {
            result.className = 'result ' + type;
            result.innerHTML = html;
        }
    </script>
</body>
</html>
'''


@app.route('/')
def index():
    """Render the main page."""
    return render_template_string(HTML_TEMPLATE)


@app.route('/convert', methods=['POST'])
def convert():
    """Handle file conversion."""
    try:
        # Get uploaded file
        file = request.files.get('file')
        if not file:
            return {'success': False, 'error': 'No file uploaded'}

        # Check file extension
        if not file.filename.lower().endswith('.txt'):
            return {'success': False, 'error': 'Only .txt files are supported'}

        # Get form data
        filetype = request.form.get('filetype', 'auto')
        material_id = request.form.get('material_id', '')

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        try:
            # Parse the file
            meta, ads, des = parse(filetype, tmp_path)

            # Use material ID from metadata if not provided
            if not material_id and 'material' in meta:
                material_id = meta['material']

            # Generate output filename (keep same name as input, just change extension)
            input_base = os.path.splitext(file.filename)[0]
            output_filename = f"{input_base}.aif"
            output_path = os.path.join(tempfile.gettempdir(), output_filename)

            # Create AIF file
            makeAIF(meta, ads, des, material_id, output_path)

            # Generate plot image
            plot_filename = f"{input_base}_plot.png"
            plot_path = os.path.join(tempfile.gettempdir(), plot_filename)
            generate_plot(meta, ads, des, plot_path)

            return {
                'success': True,
                'material_id': material_id,
                'ads_points': len(ads),
                'des_points': len(des),
                'output_file': output_filename,
                'plot_file': plot_filename
            }

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/plot/<filename>')
def get_plot(filename):
    """Serve the generated plot image."""
    filepath = os.path.join(tempfile.gettempdir(), filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        return response

    return send_file(filepath, mimetype='image/png')


@app.route('/download/<filename>')
def download(filename):
    """Serve the converted AIF file."""
    filepath = os.path.join(tempfile.gettempdir(), filename)

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass
        return response

    return send_file(filepath, as_attachment=True, download_name=filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
