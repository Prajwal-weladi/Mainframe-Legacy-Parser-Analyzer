import os
import shutil
import tempfile
import uuid
from typing import List, Optional, Union
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.cobol_parser import COBOLParser
from src.analyzer import COBOLAnalyzer
from src.doc_generator import COBOLDocumentationGenerator
from src.pdf_converter import COBOLPDFConverter
from src.workspace_analyzer import WorkspaceAnalyzer

app = FastAPI(title="COBOL Analyst Web Service", version="1.0.0")

# Enable CORS for easier testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root directory for temp files (inside the workspace)
WORKSPACE_TEMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_workspaces")
os.makedirs(WORKSPACE_TEMP, exist_ok=True)

def cleanup_directory(path: str):
    """Safely removes temporary working folders after streaming response."""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"[*] Cleaned up temporary directory: {path}")
    except Exception as e:
        print(f"Warning: Failed to clean up {path}: {e}")

async def run_analysis_pipeline(
    background_tasks: BackgroundTasks,
    source_file: UploadFile,
    copybooks: Optional[List[Union[UploadFile, str]]],
    ollama_model: str,
    ollama_url: str,
    format: str
):
    print(f"[*] Received request to analyze file: {source_file.filename}")
    print(f"[*] Ollama Target model: {ollama_model} @ {ollama_url}")
    print(f"[*] Output Format: {format}")

    # Create a unique subfolder inside the workspace temp directory
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(WORKSPACE_TEMP, session_id)
    copybook_dir = os.path.join(session_dir, "copybooks")
    
    os.makedirs(session_dir, exist_ok=True)
    os.makedirs(copybook_dir, exist_ok=True)
    
    # Register cleanup
    background_tasks.add_task(cleanup_directory, session_dir)
    
    try:
        # Save COBOL source file
        source_path = os.path.join(session_dir, source_file.filename)
        with open(source_path, "wb") as f:
            f.write(await source_file.read())
        print(f"[+] Saved source file to {source_path}")
            
        # Save all copybooks (if provided as a list of files)
        saved_copybooks = []
        if copybooks and isinstance(copybooks, list):
            for cp in copybooks:
                if cp and not isinstance(cp, str) and cp.filename:
                    cp_path = os.path.join(copybook_dir, cp.filename)
                    with open(cp_path, "wb") as f:
                        f.write(await cp.read())
                    saved_copybooks.append(cp.filename)
        print(f"[+] Saved copybooks: {saved_copybooks}")

        # Step 1: Parse
        parser = COBOLParser(copybook_dir=copybook_dir)
        metadata = parser.parse(source_path)
        
        # Step 2: Analyze
        analyzer = COBOLAnalyzer(metadata)
        analyzed_metadata = analyzer.analyze()

        # Step 3: Generate Markdown
        doc_gen = COBOLDocumentationGenerator(
            metadata=analyzed_metadata,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            output_dir=session_dir
        )
        markdown_doc = doc_gen.generate_documentation()

        # Step 4: Output based on requested format
        if format.lower() == "markdown":
            output_md_path = os.path.join(session_dir, "documentation.md")
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(markdown_doc)
            return FileResponse(
                path=output_md_path,
                filename=f"{analyzed_metadata['program_id']}_documentation.md",
                media_type="text/markdown"
            )
        else:
            # Generate PDF
            output_pdf_path = os.path.join(session_dir, "documentation.pdf")
            pdf_converter = COBOLPDFConverter()
            success = pdf_converter.convert_markdown_to_pdf(markdown_doc, output_pdf_path)
            
            if not success or not os.path.exists(output_pdf_path):
                raise HTTPException(status_code=500, detail="Failed to compile HTML/Markdown into PDF.")

            return FileResponse(
                path=output_pdf_path,
                filename=f"{analyzed_metadata['program_id']}_documentation.pdf",
                media_type="application/pdf"
            )

    except Exception as e:
        # If execution fails, cleanup immediately and raise exception
        cleanup_directory(session_dir)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis pipeline crashed: {str(e)}")

@app.post("/analyze")
async def analyze_cobol(
    background_tasks: BackgroundTasks,
    source_file: UploadFile = File(...),
    copybooks: Optional[List[Union[UploadFile, str]]] = File(None),
    ollama_model: str = Form("llama3.2:latest"),
    ollama_url: str = Form("http://localhost:11434"),
    format: str = Form("pdf") # "pdf" or "markdown"
):
    """
    Main upload and processing endpoint. Accepts COBOL source, copybooks,
    runs the analysis and generates a downloadable PDF or Markdown report.
    """
    return await run_analysis_pipeline(
        background_tasks=background_tasks,
        source_file=source_file,
        copybooks=copybooks,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        format=format
    )

@app.post("/analyze-quick")
async def analyze_cobol_quick(
    background_tasks: BackgroundTasks,
    source_file: UploadFile = File(...),
    copybooks: Optional[List[Union[UploadFile, str]]] = File(None),
    ollama_model: str = Form("llama3.2:latest"),
    ollama_url: str = Form("http://localhost:11434"),
    format: str = Form("pdf") # "pdf" or "markdown"
):
    """
    Quick test endpoint for Swagger UI testing. Runs the full pipeline including Ollama,
    and handles empty copybooks gracefully without requiring the dashboard UI.
    """
    return await run_analysis_pipeline(
        background_tasks=background_tasks,
        source_file=source_file,
        copybooks=copybooks,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        format=format
    )

@app.post("/analyze-workspace")
async def analyze_workspace(
    background_tasks: BackgroundTasks,
    zip_file: UploadFile = File(...),
    ollama_model: str = Form("skip"),
    ollama_url: str = Form("http://localhost:11434"),
    format: str = Form("pdf") # "pdf" or "markdown"
):
    """
    Analyzes an uploaded workspace ZIP archive. Captures file relationships,
    creates component diagrams, and outputs a detailed markdown or PDF report.
    """
    print(f"[*] Received request to analyze workspace ZIP: {zip_file.filename}")
    print(f"[*] Ollama Target model: {ollama_model} @ {ollama_url}")
    print(f"[*] Output Format: {format}")

    # Create a unique session folder inside temp_workspaces
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(WORKSPACE_TEMP, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Register cleanup
    background_tasks.add_task(cleanup_directory, session_dir)

    try:
        # Save ZIP file
        zip_path = os.path.join(session_dir, "workspace.zip")
        with open(zip_path, "wb") as f:
            f.write(await zip_file.read())
        print(f"[+] Saved zip file to {zip_path}")
        
        # Instantiate and run analyzer
        analyzer = WorkspaceAnalyzer()
        analyzer.zip_path = zip_path
        analyzer.source_dir = os.path.join(session_dir, "extracted_sources")
        analyzer.output_dir = session_dir
        analyzer.output_md = os.path.join(session_dir, "workspace_comprehension.md")
        analyzer.output_pdf = os.path.join(session_dir, "workspace_comprehension.pdf")
        analyzer.ollama_config = {"url": ollama_url, "model": ollama_model}
        
        success = analyzer.run()
        if not success:
            raise HTTPException(status_code=500, detail="Workspace parser failed to execute successfully.")

        if format.lower() == "markdown":
            if not os.path.exists(analyzer.output_md):
                raise HTTPException(status_code=500, detail="Failed to locate generated markdown file.")
            return FileResponse(
                path=analyzer.output_md,
                filename="workspace_comprehension.md",
                media_type="text/markdown"
            )
        else:
            if not os.path.exists(analyzer.output_pdf):
                raise HTTPException(status_code=500, detail="Failed to compile HTML/Markdown into PDF.")
            return FileResponse(
                path=analyzer.output_pdf,
                filename="workspace_comprehension.pdf",
                media_type="application/pdf"
            )

    except Exception as e:
        cleanup_directory(session_dir)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Workspace analysis crashed: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Returns a highly premium, animated drag-and-drop web dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COBOL Modern Analyst Dashboard</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --primary-glow: rgba(99, 102, 241, 0.4);
            --accent-teal: #14b8a6;
            --accent-rose: #f43f5e;
            --glass-bg: rgba(30, 41, 59, 0.65);
            --glass-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow-x: hidden;
            padding: 20px;
        }

        /* Ambient glowing backgrounds */
        .ambient-glow-1 {
            position: absolute;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.2) 0%, rgba(0,0,0,0) 70%);
            top: -100px;
            left: -100px;
            z-index: -1;
            pointer-events: none;
        }

        .ambient-glow-2 {
            position: absolute;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(20, 184, 166, 0.15) 0%, rgba(0,0,0,0) 70%);
            bottom: -150px;
            right: -100px;
            z-index: -1;
            pointer-events: none;
        }

        .container {
            width: 100%;
            max-width: 800px;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
            position: relative;
        }

        header {
            text-align: center;
            margin-bottom: 25px;
        }

        header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(to right, #a5b4fc, #818cf8, #2dd4bf);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        header p {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 300;
        }

        /* Tab Styles */
        .tab-bar {
            display: flex;
            border-bottom: 1px solid var(--glass-border);
            margin-bottom: 25px;
            gap: 20px;
        }

        .tab-btn {
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 500;
            padding: 10px 5px;
            cursor: pointer;
            position: relative;
            transition: color 0.3s ease;
        }

        .tab-btn:hover {
            color: var(--text-primary);
        }

        .tab-btn.active {
            color: var(--text-primary);
            font-weight: 600;
        }

        .tab-btn.active::after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 2px;
            background: var(--primary);
        }

        /* Config fields */
        .config-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
        }

        .form-group label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }

        .form-group input {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }

        .form-group input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 10px var(--primary-glow);
        }

        /* Drag & Drop Area */
        .upload-section {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 30px;
        }

        .drop-zone {
            border: 2px dashed rgba(255, 255, 255, 0.15);
            border-radius: 20px;
            padding: 40px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(255, 255, 255, 0.02);
            position: relative;
            overflow: hidden;
        }

        .drop-zone.dragover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.08);
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
        }

        .drop-zone svg {
            width: 48px;
            height: 48px;
            stroke: var(--text-secondary);
            margin-bottom: 15px;
            transition: all 0.3s ease;
        }

        .drop-zone.dragover svg {
            stroke: var(--primary);
            transform: translateY(-4px) scale(1.05);
        }

        .drop-zone p {
            font-size: 1rem;
            margin-bottom: 5px;
            color: var(--text-primary);
        }

        .drop-zone span {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .file-list {
            margin-top: 15px;
            max-height: 150px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--glass-border);
            border-radius: 10px;
            padding: 8px 16px;
            font-size: 0.9rem;
            animation: slideIn 0.3s ease forwards;
        }

        .file-item-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .file-item-badge {
            background: var(--primary);
            color: white;
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .file-item-badge.cpy {
            background: var(--accent-teal);
        }

        .remove-file {
            cursor: pointer;
            color: var(--accent-rose);
            font-weight: bold;
            font-size: 1.1rem;
            transition: transform 0.2s ease;
        }

        .remove-file:hover {
            transform: scale(1.2);
        }

        /* Buttons Section */
        .action-row {
            display: flex;
            gap: 15px;
        }

        .btn {
            flex: 1;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 16px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            box-shadow: 0 4px 15px var(--primary-glow);
        }

        .btn:hover:not(:disabled) {
            background: var(--primary-hover);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px var(--primary-glow);
        }

        .btn:active:not(:disabled) {
            transform: translateY(0);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            box-shadow: none;
        }

        .btn-teal {
            background: var(--accent-teal);
            box-shadow: 0 4px 15px rgba(20, 184, 166, 0.3);
        }

        .btn-teal:hover:not(:disabled) {
            background: #0d9488;
            box-shadow: 0 6px 20px rgba(20, 184, 166, 0.4);
        }

        /* Status and Overlay */
        .status-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(8px);
            border-radius: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.4s ease;
            z-index: 10;
        }

        .status-overlay.active {
            opacity: 1;
            pointer-events: all;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(99, 102, 241, 0.1);
            border-top: 4px solid var(--primary);
            border-right: 4px solid var(--accent-teal);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 25px;
        }

        .status-text {
            font-size: 1.2rem;
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 10px;
            text-align: center;
        }

        .status-subtext {
            font-size: 0.9rem;
            color: var(--text-secondary);
            max-width: 350px;
            text-align: center;
        }

        /* Error notification */
        .error-banner {
            background: rgba(244, 63, 94, 0.15);
            border: 1px solid rgba(244, 63, 94, 0.3);
            border-radius: 12px;
            padding: 15px 20px;
            color: #fda4af;
            font-size: 0.9rem;
            margin-bottom: 20px;
            display: none;
            align-items: center;
            justify-content: space-between;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Responsive */
        @media(max-width: 600px) {
            .config-row {
                grid-template-columns: 1fr;
                gap: 15px;
            }
            .action-row {
                flex-direction: column;
            }
            .container {
                padding: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="ambient-glow-1"></div>
    <div class="ambient-glow-2"></div>

    <div class="container">
        <!-- Status Overlay -->
        <div class="status-overlay" id="statusOverlay">
            <div class="spinner"></div>
            <div class="status-text" id="statusText">Uploading files...</div>
            <div class="status-subtext" id="statusSubtext">Initializing parser engine...</div>
        </div>

        <header>
            <h1>COBOL Modern Analyst Dashboard</h1>
            <p>Static Analysis, PII Taint Propagation, and Premium Documentation PDF Generator</p>
        </header>

        <!-- Tabs -->
        <div class="tab-bar">
            <button class="tab-btn active" id="tabSingle" onclick="switchTab('single')">Single File Analysis</button>
            <button class="tab-btn" id="tabWorkspace" onclick="switchTab('workspace')">Workspace ZIP Analysis</button>
        </div>

        <!-- Error banner -->
        <div class="error-banner" id="errorBanner">
            <span id="errorText">An error occurred during analysis.</span>
            <span class="remove-file" onclick="hideError()">×</span>
        </div>

        <!-- Configuration -->
        <div class="config-row">
            <div class="form-group">
                <label for="modelInput">Ollama Model</label>
                <input type="text" id="modelInput" value="skip" placeholder="e.g. skip or llama3.2">
            </div>
            <div class="form-group">
                <label for="urlInput">Ollama URL Host</label>
                <input type="text" id="urlInput" value="http://localhost:11434" placeholder="e.g. http://localhost:11434">
            </div>
        </div>

        <!-- File Upload Section for Single File -->
        <div class="upload-section" id="sectionSingle">
            <div class="form-group">
                <label>Upload Source Code & Copybooks</label>
                <div class="drop-zone" id="dropZone" onclick="triggerFileInput()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <p>Drag and drop files here, or click to browse</p>
                    <span>Support .cbl, .cob, .cpy, and .txt files. First file will be treated as main source.</span>
                    <input type="file" id="fileInput" multiple style="display: none;" onchange="handleFileSelect(event)">
                </div>
                <div class="file-list" id="fileList"></div>
            </div>
        </div>

        <!-- File Upload Section for Workspace ZIP -->
        <div class="upload-section" id="sectionWorkspace" style="display: none;">
            <div class="form-group">
                <label>Upload Workspace ZIP Archive</label>
                <div class="drop-zone" id="dropZoneWorkspace" onclick="triggerWorkspaceFileInput()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                        <polyline points="17 8 12 3 7 8" />
                        <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <p>Drag and drop workspace ZIP here, or click to browse</p>
                    <span>Upload a single ZIP archive (.zip) containing folders of cobol, jcl, bms, asm, etc.</span>
                    <input type="file" id="workspaceFileInput" accept=".zip" style="display: none;" onchange="handleWorkspaceFileSelect(event)">
                </div>
                <div class="file-list" id="workspaceFileList"></div>
            </div>
        </div>

        <!-- Actions -->
        <div class="action-row">
            <button class="btn btn-teal" id="btnMd" onclick="submitAnalysis('markdown')">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                Download Markdown (.md)
            </button>
            <button class="btn" id="btnPdf" onclick="submitAnalysis('pdf')">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                Generate & Download PDF
            </button>
        </div>
    </div>

    <script>
        let activeTab = 'single';
        let mainSourceFile = null;
        let copybooksList = [];
        let workspaceZipFile = null;

        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        const dropZoneWorkspace = document.getElementById('dropZoneWorkspace');
        const workspaceFileInput = document.getElementById('workspaceFileInput');
        const workspaceFileList = document.getElementById('workspaceFileList');
        
        const statusOverlay = document.getElementById('statusOverlay');
        const statusText = document.getElementById('statusText');
        const statusSubtext = document.getElementById('statusSubtext');
        const errorBanner = document.getElementById('errorBanner');
        const errorText = document.getElementById('errorText');

        function switchTab(tab) {
            activeTab = tab;
            document.getElementById('tabSingle').classList.toggle('active', tab === 'single');
            document.getElementById('tabWorkspace').classList.toggle('active', tab === 'workspace');
            document.getElementById('sectionSingle').style.display = tab === 'single' ? 'block' : 'none';
            document.getElementById('sectionWorkspace').style.display = tab === 'workspace' ? 'block' : 'none';
            hideError();
        }

        // Drag and drop event handlers for single file
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        dropZone.addEventListener('drop', handleDrop, false);

        function highlight(e) {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }

        function unhighlight(e) {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }

        function triggerFileInput() {
            fileInput.click();
        }

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            processFiles(files);
        }

        function handleFileSelect(e) {
            const files = e.target.files;
            processFiles(files);
        }

        function processFiles(files) {
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const filename = file.filename || file.name;
                const ext = filename.split('.').pop().toLowerCase();
                
                if (ext === 'cpy' || (mainSourceFile !== null && ext === 'txt')) {
                    if (!copybooksList.some(f => f.name === file.name)) {
                        copybooksList.push(file);
                    }
                } else if (ext === 'cbl' || ext === 'cob' || mainSourceFile === null) {
                    mainSourceFile = file;
                }
            }
            updateFileListView();
        }

        function removeMainFile() {
            mainSourceFile = null;
            updateFileListView();
        }

        function removeCopybook(index) {
            copybooksList.splice(index, 1);
            updateFileListView();
        }

        function updateFileListView() {
            fileList.innerHTML = '';
            
            if (mainSourceFile) {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-item-left">
                        <span class="file-item-badge">SOURCE</span>
                        <strong>${mainSourceFile.name}</strong>
                        <span>(${(mainSourceFile.size/1024).toFixed(1)} KB)</span>
                    </div>
                    <span class="remove-file" onclick="removeMainFile()">×</span>
                `;
                fileList.appendChild(item);
            }

            copybooksList.forEach((file, index) => {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-item-left">
                        <span class="file-item-badge cpy">COPYBOOK</span>
                        <strong>${file.name}</strong>
                        <span>(${(file.size/1024).toFixed(1)} KB)</span>
                    </div>
                    <span class="remove-file" onclick="removeCopybook(${index})">×</span>
                `;
                fileList.appendChild(item);
            });
        }

        // Drag and drop event handlers for workspace zip
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZoneWorkspace.addEventListener(eventName, e => {
                e.preventDefault();
                dropZoneWorkspace.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZoneWorkspace.addEventListener(eventName, e => {
                e.preventDefault();
                dropZoneWorkspace.classList.remove('dragover');
            }, false);
        });

        dropZoneWorkspace.addEventListener('drop', e => {
            e.preventDefault();
            dropZoneWorkspace.classList.remove('dragover');
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                workspaceZipFile = files[0];
                updateWorkspaceFileListView();
            }
        }, false);

        function triggerWorkspaceFileInput() {
            workspaceFileInput.click();
        }

        function handleWorkspaceFileSelect(e) {
            const files = e.target.files;
            if (files.length > 0) {
                workspaceZipFile = files[0];
                updateWorkspaceFileListView();
            }
        }

        function removeWorkspaceFile() {
            workspaceZipFile = null;
            updateWorkspaceFileListView();
        }

        function updateWorkspaceFileListView() {
            workspaceFileList.innerHTML = '';
            if (workspaceZipFile) {
                const item = document.createElement('div');
                item.className = 'file-item';
                item.innerHTML = `
                    <div class="file-item-left">
                        <span class="file-item-badge">WORKSPACE ZIP</span>
                        <strong>${workspaceZipFile.name}</strong>
                        <span>(${(workspaceZipFile.size/1024).toFixed(1)} KB)</span>
                    </div>
                    <span class="remove-file" onclick="removeWorkspaceFile()">×</span>
                `;
                workspaceFileList.appendChild(item);
            }
        }

        function hideError() {
            errorBanner.style.display = 'none';
        }

        function showError(msg) {
            errorBanner.style.display = 'flex';
            errorText.textContent = msg;
        }

        async function submitAnalysis(formatType) {
            hideError();
            if (activeTab === 'single') {
                if (!mainSourceFile) {
                    showError("Please upload a main COBOL source file (.cbl, .cob) first.");
                    return;
                }
            } else {
                if (!workspaceZipFile) {
                    showError("Please upload a workspace ZIP archive (.zip) first.");
                    return;
                }
            }

            const model = document.getElementById('modelInput').value.trim();
            const hostUrl = document.getElementById('urlInput').value.trim();

            statusOverlay.classList.add('active');

            let url = "/analyze";
            const formData = new FormData();
            
            if (activeTab === 'single') {
                statusText.textContent = "Uploading source & copybooks...";
                statusSubtext.textContent = "Moving files to session workspace...";
                formData.append("source_file", mainSourceFile);
                copybooksList.forEach(file => {
                    formData.append("copybooks", file);
                });
                formData.append("ollama_model", model);
                formData.append("ollama_url", hostUrl);
                formData.append("format", formatType);
            } else {
                statusText.textContent = "Uploading workspace ZIP...";
                statusSubtext.textContent = "Extracting files to session workspace...";
                url = "/analyze-workspace";
                formData.append("zip_file", workspaceZipFile);
                formData.append("ollama_model", model);
                formData.append("ollama_url", hostUrl);
                formData.append("format", formatType);
            }

            let progressIndex = 0;
            const progressSteps = activeTab === 'single' ? [
                { text: "Parsing COBOL logic...", sub: "Expanding copybooks and identifying variables..." },
                { text: "Analyzing structures...", sub: "Detecting SQL queries, IMS calls, CICS commands, and VSAM..." },
                { text: "Taint Analysis...", sub: "Tracing PII elements and data flows across paragraphs..." },
                { text: "Querying Ollama...", sub: "Generating technical program narratives (this might take 30-90s)..." },
                { text: "Compiling Report...", sub: "Rendering HTML layouts and injecting premium print CSS..." },
                { text: "Generating PDF...", sub: "Writing PDF binary stream (almost ready)..." }
            ] : [
                { text: "Extracting Workspace ZIP...", sub: "Cataloging JCL, COBOL, BMS, CSD, and Assembler files..." },
                { text: "Parsing Source Components...", sub: "Parsing copybook copy statements and execution steps..." },
                { text: "Resolving Relationships...", sub: "Linking JCL jobs to COBOL program select statements..." },
                { text: "Querying Ollama...", sub: "Generating system documentation and algorithms (this might take 30-90s)..." },
                { text: "Compiling Workspace Report...", sub: "Rendering component & flow diagrams with print CSS..." },
                { text: "Generating PDF...", sub: "Writing workspace PDF binary stream (almost ready)..." }
            ];

            const progressInterval = setInterval(() => {
                if (progressIndex < progressSteps.length) {
                    statusText.textContent = progressSteps[progressIndex].text;
                    statusSubtext.textContent = progressSteps[progressIndex].sub;
                    progressIndex++;
                }
            }, 6000);

            try {
                const response = await fetch(url, {
                    method: "POST",
                    body: formData
                });

                clearInterval(progressInterval);

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || "Server error occurred during analysis.");
                }

                statusText.textContent = "Downloading report...";
                statusSubtext.textContent = "Completed successfully!";

                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = downloadUrl;
                
                const baseName = activeTab === 'single' ? 
                    (mainSourceFile.name.substring(0, mainSourceFile.name.lastIndexOf('.')) || "COBOL_Report") :
                    "Workspace_Comprehension";
                    
                a.download = `${baseName}.${formatType === 'pdf' ? 'pdf' : 'md'}`;
                
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

            } catch (err) {
                clearInterval(progressInterval);
                console.error(err);
                showError(err.message);
            } finally {
                statusOverlay.classList.remove('active');
            }
        }
    </script>
</body>
</html>
"""
    return html_content

if __name__ == '__main__':
    import uvicorn
    # Run server locally on port 8000
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=True)
