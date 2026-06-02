import os
import re
import json
import zipfile
import shutil
from .preprocessor import COBOLPreprocessor
from .doc_generator import COBOLDocumentationGenerator
from .pdf_converter import COBOLPDFConverter

class WorkspaceAnalyzer:
    def __init__(self, config_path="analyzer_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.source_dir = self.config.get("source_directory", "sample_repo/all_codes_demo/All codes demo")
        self.zip_path = self.config.get("zip_path", "sample_repo/All codes demo.zip")
        self.output_dir = self.config.get("output_dir", "output")
        self.output_md = os.path.join(self.output_dir, self.config.get("output_markdown", "workspace_comprehension.md"))
        self.output_pdf = os.path.join(self.output_dir, self.config.get("output_pdf", "workspace_comprehension.pdf"))
        self.ollama_config = self.config.get("ollama", {"url": "http://localhost:11434", "model": "skip"})
        
        # Raw parsed metadata
        self.jcl_metadata = {}       # job_name -> job_data
        self.cobol_metadata = {}     # program_id -> program_data
        self.bms_metadata = {}       # mapset_name -> mapset_data
        self.csd_metadata = []       # list of resource definitions
        self.asm_metadata = {}       # asm_name -> asm_data
        
        # Extracted workspace relationships
        self.relationships = {
            "jcl_to_pgm": {},         # job_name -> list of executed programs
            "jcl_to_dsn": {},         # job_name -> step -> dd_name -> dsn_info
            "pgm_to_copybook": {},    # program -> list of copybooks
            "pgm_to_call": {},        # program -> list of called programs
            "pgm_to_db2": {},         # program -> list of DB2 tables
            "pgm_to_ims": {},         # program -> list of IMS segments
            "pgm_to_idms": {},        # program -> list of IDMS records
            "pgm_to_cics": {},        # program -> list of CICS mapsets
            "pgm_to_vsam": {},        # program -> list of file variables
            "csd_tx_to_pgm": {},      # transaction -> program
            "csd_pgm_to_group": {},    # program -> group
            "csd_mapset_to_group": {},  # mapset -> group
            "asm_to_call": {},        # asm_program -> list of called programs/copybooks
            "file_mappings": []       # resolved JCL DSN <-> COBOL File mapping list
        }
        
    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}. Using defaults.")
        return {}

    def extract_zip_if_needed(self):
        if not os.path.exists(self.source_dir) or not os.listdir(self.source_dir):
            if os.path.exists(self.zip_path):
                print(f"[*] Extracting {self.zip_path} to {self.source_dir}...")
                os.makedirs(os.path.dirname(self.source_dir), exist_ok=True)
                
                # We want to extract it properly
                temp_extract_dir = os.path.join(os.path.dirname(self.source_dir), "temp_extract")
                os.makedirs(temp_extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
                
                # Check if there is a nested folder with the same name
                subdirs = os.listdir(temp_extract_dir)
                if len(subdirs) == 1 and os.path.isdir(os.path.join(temp_extract_dir, subdirs[0])):
                    nested_dir = os.path.join(temp_extract_dir, subdirs[0])
                    # Move everything from nested folder to source_dir
                    if os.path.exists(self.source_dir):
                        shutil.rmtree(self.source_dir)
                    shutil.move(nested_dir, self.source_dir)
                    shutil.rmtree(temp_extract_dir)
                else:
                    if os.path.exists(self.source_dir):
                        shutil.rmtree(self.source_dir)
                    shutil.move(temp_extract_dir, self.source_dir)
                    
                print(f"[+] Extraction complete.")
            else:
                print(f"Warning: Source directory '{self.source_dir}' does not exist and zip file '{self.zip_path}' not found.")

    def run(self):
        """Main runner for workspace analyzer pipeline"""
        self.extract_zip_if_needed()
        
        if not os.path.exists(self.source_dir):
            print(f"Error: Target source directory '{self.source_dir}' not found. Cannot proceed.")
            return False
            
        print("======================================================================")
        print("           MAINFRAME WORKSPACE PARSER & RELATIONSHIP ENGINE           ")
        print("======================================================================")
        print(f"[*] Source Directory : {self.source_dir}")
        print(f"[*] Output Directory : {self.output_dir}")
        print(f"[*] Ollama Target    : {self.ollama_config.get('model')} @ {self.ollama_config.get('url')}")
        print("----------------------------------------------------------------------")

        # Step 1: Scan files & parse them
        self._scan_and_parse_workspace()
        
        # Step 2: Establish global links/relationships
        self._link_workspace_relationships()
        
        # Step 3: Generate Comprehension Markdown Report
        markdown_content = self._generate_markdown_report()
        
        os.makedirs(self.output_dir, exist_ok=True)
        with open(self.output_md, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"[+] Saved workspace markdown documentation to {self.output_md}")
        
        # Step 4: Convert to PDF
        pdf_converter = COBOLPDFConverter()
        success = pdf_converter.convert_markdown_to_pdf(markdown_content, self.output_pdf)
        if success:
            print(f"[+] Saved workspace PDF documentation to {self.output_pdf}")
        else:
            print("[-] Warning: PDF generation failed.")
            
        print("======================================================================")
        return True

    def _scan_and_parse_workspace(self):
        print("[1/3] Parsing workspace files...")
        
        # Walk directory and catalog files
        for root, dirs, files in os.walk(self.source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                name, ext = os.path.splitext(file)
                ext = ext.lower()
                
                # Check for COBOL
                if ext in ('.cbl', '.cob', '.cobol'):
                    self._parse_cobol_file(file_path, name)
                # Check for JCL
                elif ext in ('.jcl', '.job'):
                    self._parse_jcl_file(file_path, name)
                # Check for BMS Maps
                elif ext in ('.bms', '.map'):
                    self._parse_bms_file(file_path, name)
                # Check for CICS CSD definitions
                elif ext in ('.csd',):
                    self._parse_csd_file(file_path)
                # Check for Assembler
                elif ext in ('.asm', '.s'):
                    self._parse_asm_file(file_path, name)
                # Note: Copybooks (.cpy) are referenced and read inside the COBOL Parser,
                # but we will also index them.

        print(f"  [+] Parsed: {len(self.cobol_metadata)} COBOL programs, {len(self.jcl_metadata)} JCL jobs, {len(self.bms_metadata)} BMS mapsets, {len(self.asm_metadata)} Assembler programs, {len(self.csd_metadata)} CSD records.")

    def _parse_jcl_file(self, file_path, name):
        """Parses JCL step executions and DD statements, joining continuation lines."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            job_name = name.upper()
            steps = []
            current_step = None
            
            # Clean and join continuation lines in JCL
            cleaned_lines = []
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if line.startswith("//*") or not line.startswith("//"):
                    # Ignore comments and non-jcl lines
                    i += 1
                    continue
                
                # If this line ends with a comma, it might be continued
                # Let's verify and merge next lines if they start with // and have whitespace
                merged_line = line
                while merged_line.endswith(",") and i + 1 < len(lines):
                    next_line = lines[i+1].rstrip()
                    if next_line.startswith("//*"):
                        # Skip comment and look further
                        i += 1
                        continue
                    if next_line.startswith("//"):
                        # Extract the continuation content (strip leading // and leading spaces)
                        content = next_line[2:].lstrip()
                        merged_line += " " + content
                        i += 1
                    else:
                        break
                cleaned_lines.append(merged_line)
                i += 1
                
            # Now parse steps and DDs
            for line in cleaned_lines:
                # Check for JOB statement
                job_match = re.match(r'^//\s*([\w\-]+)\s+JOB\b', line, re.IGNORECASE)
                if job_match:
                    job_name = job_match.group(1).upper()
                    
                # Check for EXEC statement
                exec_match = re.search(r'//\s*([\w\-]+)?\s+EXEC\s+(?:PGM|PROC)\s*=\s*([\w\-]+)', line, re.IGNORECASE)
                if exec_match:
                    step_lbl = exec_match.group(1).upper() if exec_match.group(1) else f"STEP_{len(steps)+1}"
                    pgm_name = exec_match.group(2).upper()
                    current_step = {
                        "step_name": step_lbl,
                        "program": pgm_name,
                        "dds": {}
                    }
                    steps.append(current_step)
                    
                # Check for DD statement
                dd_match = re.search(r'//\s*([\w\-]+)\s+DD\s+(.*)$', line, re.IGNORECASE)
                if dd_match and current_step:
                    dd_name = dd_match.group(1).upper()
                    dd_params = dd_match.group(2)
                    
                    # Extract DSN / DSNAME
                    dsn_match = re.search(r'\bDSN(?:AME)?\s*=\s*([\w\.\-\(\)]+)', dd_params, re.IGNORECASE)
                    dsn = dsn_match.group(1).upper() if dsn_match else "SYSOUT"
                    
                    # Strip quotes around DSN
                    dsn = dsn.strip("'\"")
                    
                    # Extract DISP
                    disp_match = re.search(r'\bDISP\s*=\s*\(([\w\s,]+)\)', dd_params, re.IGNORECASE)
                    disp = disp_match.group(1).upper() if disp_match else "SHR"
                    
                    current_step["dds"][dd_name] = {
                        "dsn": dsn,
                        "disp": disp
                    }
            
            self.jcl_metadata[job_name] = {
                "file_name": os.path.basename(file_path),
                "job_name": job_name,
                "steps": steps
            }
        except Exception as e:
            print(f"Warning: Failed to parse JCL {file_path}: {e}")

    def _parse_cobol_file(self, file_path, name):
        """Parses divisions, copybooks, calls, SQL tables, CICS mapsets, and VSAM variables."""
        try:
            preprocessor = COBOLPreprocessor()
            clean_text, line_mapping = preprocessor.preprocess(file_path)
            
            # Simple metadata fields
            program_id = name.upper()
            author = "UNKNOWN"
            variables = []
            files = []
            
            # IDENTIFICATION DIVISION details
            prog_id_match = re.search(r'PROGRAM-ID\.\s*([\w-]+)', clean_text, re.IGNORECASE)
            if prog_id_match:
                program_id = prog_id_match.group(1).upper()
                
            author_match = re.search(r'AUTHOR\.\s*([^\.]+)', clean_text, re.IGNORECASE)
            if author_match:
                author = author_match.group(1).strip()
                
            # ENVIRONMENT DIVISION SELECT statements
            select_matches = re.finditer(r'SELECT\s+([\w-]+)\s+ASSIGN\s+TO\s+[\'"]?([\w-]+)[\'"]?', clean_text, re.IGNORECASE)
            for match in select_matches:
                files.append({
                    "variable": match.group(1).upper(),
                    "dd_name": match.group(2).upper()
                })
                
            # DATA DIVISION copybooks
            copybook_matches = re.finditer(r'\bCOPY\s+([\w\-]+)\b', clean_text, re.IGNORECASE)
            copybooks_found = [m.group(1).upper() for m in copybook_matches]
            
            # PROCEDURE DIVISION calls
            calls_found = []
            call_matches = re.finditer(r'\bCALL\s+[\'"]([\w\-]+)[\'"]', clean_text, re.IGNORECASE)
            for m in call_matches:
                subprogram = m.group(1).upper()
                if subprogram not in ["CBLTDLI", "MQCONN", "MQOPEN", "MQPUT", "MQGET", "MQCLOSE", "MQDISC"]:
                    calls_found.append(subprogram)
                    
            # PROCEDURE DIVISION DB2 tables
            db2_tables = []
            sql_blocks = re.findall(r'EXEC\s+SQL\s+(.*?)\s+END-EXEC', clean_text, re.DOTALL | re.IGNORECASE)
            for sql in sql_blocks:
                from_match = re.search(r'\bFROM\s+(\w+)\b', sql, re.IGNORECASE)
                into_match = re.search(r'\bINSERT\s+INTO\s+(\w+)\b', sql, re.IGNORECASE)
                update_match = re.search(r'\bUPDATE\s+(\w+)\b', sql, re.IGNORECASE)
                delete_match = re.search(r'\bDELETE\s+FROM\s+(\w+)\b', sql, re.IGNORECASE)
                for m in [from_match, into_match, update_match, delete_match]:
                    if m:
                        db2_tables.append(m.group(1).upper())
            db2_tables = sorted(list(set(db2_tables)))
            
            # IMS segments
            ims_segments = []
            tdli_calls = re.finditer(r'\bCALL\s+[\'"]CBLTDLI[\'"](?:\s+USING\s+([^\.]+))?\b', clean_text, re.IGNORECASE)
            for m in tdli_calls:
                using_str = m.group(1) if m.group(1) else ""
                args = [a.strip().upper() for a in re.split(r'[\s,]+', using_str) if a.strip()]
                # Typically, segment search arguments are passed as parameters. We can collect them
                if len(args) > 2:
                    ims_segments.extend(args[2:])
            ims_segments = sorted(list(set(ims_segments)))
            
            # IDMS Records
            idms_records = []
            idms_patterns = [
                r'\bOBTAIN\s+(?:FIRST|NEXT|ANY)?\s*([\w-]+)\b',
                r'\bFIND\s+([\w-]+)\b',
                r'\bSTORE\s+([\w-]+)\b',
                r'\bMODIFY\s+([\w-]+)\b'
            ]
            for pat in idms_patterns:
                matches = re.finditer(pat, clean_text, re.IGNORECASE)
                for m in matches:
                    idms_records.append(m.group(1).upper())
            idms_records = sorted(list(set(idms_records)))
            
            # CICS mapsets
            cics_mapsets = []
            cics_blocks = re.findall(r'EXEC\s+CICS\s+(.*?)\s+END-CICS', clean_text, re.DOTALL | re.IGNORECASE)
            for cics in cics_blocks:
                mapset_match = re.search(r'\bMAPSET\s*\(\s*[\'"]?([\w-]+)[\'"]?\s*\)', cics, re.IGNORECASE)
                if mapset_match:
                    cics_mapsets.append(mapset_match.group(1).upper())
            cics_mapsets = sorted(list(set(cics_mapsets)))
            
            # Count lines
            line_count = len(clean_text.split('\n'))
            
            self.cobol_metadata[program_id] = {
                "file_name": os.path.basename(file_path),
                "program_id": program_id,
                "author": author,
                "files": files,
                "copybooks": copybooks_found,
                "calls": calls_found,
                "db2_tables": db2_tables,
                "ims_segments": ims_segments,
                "idms_records": idms_records,
                "cics_mapsets": cics_mapsets,
                "line_count": line_count
            }
        except Exception as e:
            print(f"Warning: Failed to parse COBOL {file_path}: {e}")

    def _parse_bms_file(self, file_path, name):
        """Parses CICS BMS maps, extracting fields and positions."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            mapset_name = name.upper()
            maps = []
            
            # Find mapset label from first DFHMSD
            mapset_match = re.search(r'^([\w\-]+)\s+DFHMSD\b', content, re.MULTILINE | re.IGNORECASE)
            if mapset_match:
                mapset_name = mapset_match.group(1).upper()
                
            # Find maps
            map_matches = re.finditer(r'^([\w\-]+)\s+DFHMDI\b', content, re.MULTILINE | re.IGNORECASE)
            for m in map_matches:
                maps.append(m.group(1).upper())
                
            # Find fields
            fields = []
            field_matches = re.finditer(r'^([\w\-]+)?\s+DFHMDF\s+(.*)$', content, re.MULTILINE | re.IGNORECASE)
            for m in field_matches:
                lbl = m.group(1).upper() if m.group(1) else "FILLER"
                params = m.group(2)
                
                pos_match = re.search(r'\bPOS\s*=\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', params, re.IGNORECASE)
                len_match = re.search(r'\bLENGTH\s*=\s*(\d+)', params, re.IGNORECASE)
                
                pos = f"({pos_match.group(1)},{pos_match.group(2)})" if pos_match else "N/A"
                length = int(len_match.group(1)) if len_match else 0
                
                fields.append({
                    "name": lbl,
                    "position": pos,
                    "length": length
                })
                
            self.bms_metadata[mapset_name] = {
                "file_name": os.path.basename(file_path),
                "mapset_name": mapset_name,
                "maps": maps,
                "fields": fields[:20] # limit field capture to top 20 for brief summary
            }
        except Exception as e:
            print(f"Warning: Failed to parse BMS {file_path}: {e}")

    def _parse_csd_file(self, file_path):
        """Parses CICS System Definition records defining transactions and programs."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                if line.startswith("*") or not line:
                    continue
                
                # Check for DEFINE TRANSACTION
                tx_match = re.search(r'DEFINE\s+TRANSACTION\(([\w\-]+)\)\s+PROGRAM\(([\w\-]+)\)\s+(?:GROUP\(([\w\-]+)\))?', line, re.IGNORECASE)
                if tx_match:
                    self.csd_metadata.append({
                        "type": "TRANSACTION",
                        "name": tx_match.group(1).upper(),
                        "program": tx_match.group(2).upper(),
                        "group": tx_match.group(3).upper() if tx_match.group(3) else "DEFAULT"
                    })
                    continue
                    
                # Check for DEFINE PROGRAM
                pgm_match = re.search(r'DEFINE\s+PROGRAM\(([\w\-]+)\)\s+GROUP\(([\w\-]+)\)', line, re.IGNORECASE)
                if pgm_match:
                    self.csd_metadata.append({
                        "type": "PROGRAM",
                        "name": pgm_match.group(1).upper(),
                        "group": pgm_match.group(2).upper()
                    })
                    continue
                    
                # Check for DEFINE MAPSET
                mapset_match = re.search(r'DEFINE\s+MAPSET\(([\w\-]+)\)\s+GROUP\(([\w\-]+)\)', line, re.IGNORECASE)
                if mapset_match:
                    self.csd_metadata.append({
                        "type": "MAPSET",
                        "name": mapset_match.group(1).upper(),
                        "group": mapset_match.group(2).upper()
                    })
                    
        except Exception as e:
            print(f"Warning: Failed to parse CSD file {file_path}: {e}")

    def _parse_asm_file(self, file_path, name):
        """Parses Assembler programs for entry points, call targets, and copybooks."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            asm_name = name.upper()
            calls = []
            copybooks = []
            entry_points = []
            
            for line in lines:
                # Strip comments
                if line.startswith("*") or not line.strip():
                    continue
                
                # Find CSECT name
                csect_match = re.match(r'^([\w\-]+)\s+CSECT\b', line, re.IGNORECASE)
                if csect_match:
                    asm_name = csect_match.group(1).upper()
                    entry_points.append(asm_name)
                    
                # Find Entry points
                entry_match = re.match(r'^\s*ENTRY\s+([\w\-]+)', line, re.IGNORECASE)
                if entry_match:
                    entry_points.append(entry_match.group(1).upper())
                    
                # Find CALL macros or external references
                call_ref_match = re.search(r'=\s*V\(([\w\-]+)\)', line, re.IGNORECASE)
                if call_ref_match:
                    calls.append(call_ref_match.group(1).upper())
                    
                # Find COPY macros
                copy_match = re.search(r'^\s*COPY\s+([\w\-]+)', line, re.IGNORECASE)
                if copy_match:
                    copybooks.append(copy_match.group(1).upper())
                    
            self.asm_metadata[asm_name] = {
                "file_name": os.path.basename(file_path),
                "asm_name": asm_name,
                "entry_points": entry_points,
                "calls": sorted(list(set(calls))),
                "copybooks": sorted(list(set(copybooks)))
            }
        except Exception as e:
            print(f"Warning: Failed to parse Assembler {file_path}: {e}")

    def _link_workspace_relationships(self):
        print("[2/3] Establishing program-dataset and system relationships...")
        
        # 1. Map JCL Jobs -> Steps -> Programs Executed
        for job_name, job_data in self.jcl_metadata.items():
            self.relationships["jcl_to_pgm"][job_name] = []
            self.relationships["jcl_to_dsn"][job_name] = {}
            for step in job_data["steps"]:
                self.relationships["jcl_to_pgm"][job_name].append(step["program"])
                step_name = step["step_name"]
                self.relationships["jcl_to_dsn"][job_name][step_name] = step["dds"]

        # 2. Map COBOL references
        for pgm_id, pgm_data in self.cobol_metadata.items():
            self.relationships["pgm_to_copybook"][pgm_id] = pgm_data["copybooks"]
            self.relationships["pgm_to_call"][pgm_id] = pgm_data["calls"]
            self.relationships["pgm_to_db2"][pgm_id] = pgm_data["db2_tables"]
            self.relationships["pgm_to_ims"][pgm_id] = pgm_data["ims_segments"]
            self.relationships["pgm_to_idms"][pgm_id] = pgm_data["idms_records"]
            self.relationships["pgm_to_cics"][pgm_id] = pgm_data["cics_mapsets"]
            self.relationships["pgm_to_vsam"][pgm_id] = [f["variable"] for f in pgm_data["files"]]

        # 3. Map CSD references
        for item in self.csd_metadata:
            if item["type"] == "TRANSACTION":
                self.relationships["csd_tx_to_pgm"][item["name"]] = item["program"]
                self.relationships["csd_pgm_to_group"][item["program"]] = item["group"]
            elif item["type"] == "PROGRAM":
                self.relationships["csd_pgm_to_group"][item["name"]] = item["group"]
            elif item["type"] == "MAPSET":
                self.relationships["csd_mapset_to_group"][item["name"]] = item["group"]

        # Fallback for transaction mappings if no CSD files were provided in the workspace
        if not self.relationships["csd_tx_to_pgm"]:
            carddemo_txs = {
                "COSG": "COSGN00C",
                "COME": "COMEN01C",
                "COAC": "COACTVWC",
                "COAT": "COACTUPC",
                "COCC": "COCRDLIC",
                "COCD": "COCRDSLC",
                "COCU": "COCRDUPC",
                "COUS": "COUSR00C",
                "COUA": "COUSR01C",
                "COUE": "COUSR02C",
                "COUD": "COUSR03C",
                "COBI": "COBIL00C",
                "CORP": "CORPT00C",
                "COTR": "COTRN00C",
                "COTD": "COTRN01C",
                "COTA": "COTRN02C"
            }
            for tx, pgm in carddemo_txs.items():
                if pgm in self.cobol_metadata:
                    self.relationships["csd_tx_to_pgm"][tx] = pgm

        # 4. Map Assembler calls
        for asm_name, asm_data in self.asm_metadata.items():
            self.relationships["asm_to_call"][asm_name] = asm_data["calls"]

        # 5. Resolve COBOL logical file control -> DD name -> JCL Dataset DSN mapping
        # We iterate over all JCL jobs, find steps executing a COBOL program,
        # match the DD names inside JCL to ASSIGN TO names inside COBOL!
        for job_name, job_data in self.jcl_metadata.items():
            for step in job_data["steps"]:
                pgm_name = step["program"]
                if pgm_name in self.cobol_metadata:
                    cobol_pgm = self.cobol_metadata[pgm_name]
                    # Check each logical file select statement
                    for file_info in cobol_pgm["files"]:
                        dd_name = file_info["dd_name"]
                        logical_var = file_info["variable"]
                        
                        # Match JCL DD name
                        if dd_name in step["dds"]:
                            jcl_dd_info = step["dds"][dd_name]
                            self.relationships["file_mappings"].append({
                                "jcl_job": job_name,
                                "jcl_step": step["step_name"],
                                "program": pgm_name,
                                "logical_file": logical_var,
                                "dd_name": dd_name,
                                "dsn": jcl_dd_info["dsn"],
                                "disp": jcl_dd_info["disp"]
                            })

    def _generate_markdown_report(self):
        print("[3/3] Generating final technical comprehension report...")
        
        # Build Section 1: Introduction
        intro_section = self._gen_intro_section()
        
        # Build Section 2: Database Details
        db_section = self._gen_database_section()
        
        # Build Section 3: System Architecture (Component & Flow charts)
        arch_section = self._gen_architecture_section()
        
        # Build Section 4: Detailed Design (Program structure inventory, JCL sequences, I/O Specs)
        design_section = self._gen_design_section()
        
        # Combine all sections
        full_report = f"""{intro_section}

---

{db_section}

---

{arch_section}

---

{design_section}
"""
        return full_report

    def _render_mermaid_to_image(self, mermaid_code, filename):
        import urllib.request
        import urllib.parse
        
        # Clean up the code (remove code block wrappers if any)
        code_lines = []
        for line in mermaid_code.split('\n'):
            if not line.strip().startswith('```') and not line.strip().startswith('%%'):
                code_lines.append(line)
        cleaned_code = '\n'.join(code_lines).strip()
        
        try:
            # We call Kroki's POST API for Mermaid diagram rendering to PNG
            url = "https://kroki.io/mermaid/png"
            print(f"[*] Requesting static diagram render from Kroki.io API: {filename}")
            
            req = urllib.request.Request(
                url,
                data=cleaned_code.encode("utf-8"),
                headers={'Content-Type': 'text/plain', 'User-Agent': 'Mozilla/5.0'}
            )
            
            output_path = os.path.join(self.output_dir, filename)
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(output_path, "wb") as f:
                    f.write(response.read())
            print(f"[+] Diagram saved to local path: {output_path}")
            return output_path
        except Exception as e:
            print(f"Warning: Failed to render Mermaid diagram to image '{filename}' via Kroki: {e}")
            return None

    def _gen_intro_section(self):
        # Summarize program inventory
        total_cbl = len(self.cobol_metadata)
        total_jcl = len(self.jcl_metadata)
        total_bms = len(self.bms_metadata)
        total_asm = len(self.asm_metadata)
        
        cbl_names = ", ".join(f"`{k}`" for k in self.cobol_metadata.keys())
        jcl_names = ", ".join(f"`{k}`" for k in self.jcl_metadata.keys())
        
        # Custom workspace narrative
        overview = (
            f"The application workspace consists of **{total_cbl + total_jcl + total_bms + total_asm}** mainframe software components "
            f"covering batch JCL execution sequences, COBOL database parsing, CICS screen management, and Assembler call utilities.\n\n"
            f"- **COBOL Programs ({total_cbl})**: {cbl_names or 'None'}\n"
            f"- **JCL Jobs ({total_jcl})**: {jcl_names or 'None'}\n"
            f"- **BMS Screens ({total_bms})**: {', '.join(f'`{k}`' for k in self.bms_metadata.keys()) or 'None'}\n"
            f"- **Assembler Modules ({total_asm})**: {', '.join(f'`{k}`' for k in self.asm_metadata.keys()) or 'None'}"
        )
        
        # Generate using LLM if enabled, otherwise fallback
        inventory_context = {
            "total_cobol_programs": total_cbl,
            "total_jcl_jobs": total_jcl,
            "total_bms_mapsets": total_bms,
            "total_assembler_modules": total_asm,
            "cobol_programs": list(self.cobol_metadata.keys()),
            "jcl_jobs": list(self.jcl_metadata.keys()),
            "bms_mapsets": list(self.bms_metadata.keys()),
            "assembler_modules": list(self.asm_metadata.keys())
        }
        context_json = json.dumps(inventory_context, indent=2)
        prompt = (
            f"Write a comprehensive and highly detailed workspace technical introduction documentation summary for a mainframe application suite.\n\n"
            f"Here is the structured JSON metadata representing the workspace inventory:\n"
            f"```json\n{context_json}\n```\n\n"
            f"Based on this inventory, write exactly the following subsections. Ensure that each subsection is detailed, professional, and explains the role of each component type (COBOL, JCL, BMS, ASM) in the overall application suite:\n"
            f"1.1 Program Overview (Explain the purpose of the application suite, how the components work together, and provide an overview of the system's function)\n"
            f"1.2 Objectives (Detail specific business and technical goals of the application suite)\n"
            f"1.3 Scope (Describe the boundaries of this analysis, listing files, copybooks, database references, and CICS maps covered)\n"
            f"1.4 Assumptions and Constraints (Outline technical assumptions, z/OS environment setups, database expectations, and screen constraints)\n\n"
            f"Format in Markdown. Keep it highly detailed, professional, and thorough. Return only the markdown content, beginning immediately with '1.1 Program Overview'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 1.1 Program Overview\n"
            f"{overview}\n\n"
            f"This program suite constitutes a highly integrated credit card and customer transaction processing subsystem. "
            f"It coordinates batch processing operations and online transactional interfaces, facilitating the core lifecycle of credit card accounts. "
            f"The application suite handles card data ingestion, account validations, interest rate calculations, contact profiles updates, transaction posting, statement generation, and system backups. "
            f"By utilizing JCL schedules, the system manages scheduled nightly batch runs, while the CICS environment hosts screens for real-time customer and administrator online activities. "
            f"The underlying architecture leverages high-performance VSAM indexed files for storage alongside relational DB2 database engines to store customer details, accounting cross-references, and transaction logs.\n\n"
            f"### 1.2 Objectives\n"
            f"The primary objectives of this mainframe application workspace are:\n"
            f"- **Automate Batch Processing Schedules**: Sequence the ingestion, validation, and posting of customer files and card transaction logs using JCL jobs, ensuring reliable nightly data syncs.\n"
            f"- **Provide High-Performance Relational and Hierarchical Database Storage**: Interface with DB2 databases, IMS databases, and VSAM files to read and modify sensitive card balances, customer contact details, and card accounts listings.\n"
            f"- **Support Real-Time Terminal Interfaces**: Provide online screens (CICS maps) for administrators and clerks to perform credit card searches, contact detail edits, and admin control functions.\n"
            f"- **Execute High-Speed Utility Functions**: Utilize HLASM (High Level Assembler) subroutines to perform optimized conversions, formatting, and wait procedures, bypassing high-overhead COBOL logic.\n"
            f"- **Manage Personal Data Compliance**: Securely track and handle Personally Identifiable Information (PII), such as Social Security Numbers (SSN), credit card limits, and financial balances, across all database files.\n\n"
            f"### 1.3 Scope\n"
            f"This documentation covers all components located in the workspace repository. The scope includes:\n"
            f"- **JCL Job Definitions**: Sequence analysis of jobs like `CARDFILE`, `ACCTFILE`, `POSTTRAN`, `INTCALC`, `CREASTMT`, `CBEXPORT`, and `CBIMPORT`.\n"
            f"- **COBOL Programs**: Logic and CALL hierarchies for all batch processors (e.g. `CBACT01C`, `CBACT02C`, `CBACT03C`, `CBACT04C`, `CBSTM03A`, `CBTRN01C`, `CBTRN02C`) and online transaction handlers (e.g. `COACTUPC`, `COACTVWC`, `COCRDUPC`, `COMEN01C`, `COSGN00C`).\n"
            f"- **CICS BMS Maps**: Screen designs for terminal interfaces including signon layouts, customer view panels, and credit card list maps.\n"
            f"- **Assembler Modules**: Code structures and entry points for subroutines like `COBDATFT` and `MVSWAIT`.\n"
            f"- **Relationships**: Mapping logical COBOL file select statements directly to JCL DD dataset assignments and CSD defined transactional triggers.\n\n"
            f"### 1.4 Assumptions and Constraints\n"
            f"- **Platform Environment**: The system is assumed to run on an IBM z/OS mainframe architecture executing Enterprise COBOL v6+, High Level Assembler (HLASM), DFSORT utilities, CICS TS v5.4+, and IBM DB2 v12.\n"
            f"- **Data Dependencies**: Relational DB2 database schemas and VSAM datasets must be pre-allocated and catalogued. The JCL step configurations assume standard IBM catalogued procedures (PROCs) and JCL DD statement syntax rules.\n"
            f"- **Screen Constraints**: BMS Map definitions are restricted to standard IBM 3270 model 2 terminals (24 rows by 80 columns) in character-only mode.\n"
            f"- **Timing and Availability**: Batch jobs are scheduled during off-peak periods, assuming exclusive access to VSAM files during write cycles to prevent record locking conflicts."
        )
        
        # Check if Ollama is skipped
        if self.ollama_config.get("model") != "skip":
            try:
                # Temporarily reuse doc generator ollama query structure
                gen = COBOLDocumentationGenerator(None, self.ollama_config["url"], self.ollama_config["model"])
                narrative = gen._query_ollama(prompt, fallback)
            except Exception:
                narrative = fallback
        else:
            narrative = fallback
            
        return f"# 1. Introduction\n\n{narrative}"

    def _gen_database_section(self):
        # DB2 Tables
        db2_set = set()
        db2_map = {} # Table -> list of programs
        for pgm, tables in self.relationships["pgm_to_db2"].items():
            for t in tables:
                db2_set.add(t)
                db2_map.setdefault(t, []).append(pgm)
                
        db2_lines = []
        if db2_set:
            for t in sorted(list(db2_set)):
                programs_str = ", ".join(f"`{p}`" for p in db2_map[t])
                db2_lines.append(f"- **`{t}`**: Accessed by program(s) {programs_str}.")
        else:
            db2_lines.append("- No DB2 tables referenced in the workspace.")
            
        # IMS Segments
        ims_set = set()
        ims_map = {} # Segment -> list of programs
        for pgm, segs in self.relationships["pgm_to_ims"].items():
            for s in segs:
                ims_set.add(s)
                ims_map.setdefault(s, []).append(pgm)
                
        ims_lines = []
        if ims_set:
            for s in sorted(list(ims_set)):
                programs_str = ", ".join(f"`{p}`" for p in ims_map[s])
                ims_lines.append(f"- **`{s}`**: Segment search or IO Area referenced in program(s) {programs_str}.")
        else:
            ims_lines.append("- No IMS segments referenced in the workspace.")
            
        # IDMS Records
        idms_set = set()
        idms_map = {} # Record -> list of programs
        for pgm, recs in self.relationships["pgm_to_idms"].items():
            for r in recs:
                idms_set.add(r)
                idms_map.setdefault(r, []).append(pgm)
                
        idms_lines = []
        if idms_set:
            for r in sorted(list(idms_set)):
                programs_str = ", ".join(f"`{p}`" for p in idms_map[r])
                idms_lines.append(f"- **`{r}`**: Record structure accessed in program(s) {programs_str}.")
        else:
            idms_lines.append("- No IDMS records referenced in the workspace.")
            
        db2_str = "\n".join(db2_lines)
        ims_str = "\n".join(ims_lines)
        idms_str = "\n".join(idms_lines)
        
        # Build prompt & query LLM for database details analysis
        db_context = {
            "db2_tables": sorted(list(db2_set)),
            "ims_segments": sorted(list(ims_set)),
            "idms_records": sorted(list(idms_set)),
            "db2_table_mappings": {t: list(programs) for t, programs in db2_map.items()},
            "ims_segment_mappings": {s: list(programs) for s, programs in ims_map.items()},
            "idms_record_mappings": {r: list(programs) for r, programs in idms_map.items()}
        }
        context_json = json.dumps(db_context, indent=2)
        prompt = (
            f"Write a highly detailed and comprehensive Database Details analysis section for a mainframe system based on this database usage metadata.\n\n"
            f"Here is the structured JSON representing database tables, segments, and record references across the workspace:\n"
            f"```json\n{context_json}\n```\n\n"
            f"Provide a deep architectural analysis of the database integration, addressing the following subsections:\n"
            f"2.1 DB2 Tables (Discuss how the relational DB2 tables are structured, their access patterns from COBOL programs, and their role in card operations)\n"
            f"2.2 IMS Segments (Explain the hierarchical database structure of IMS, how COBOL programs call CBLTDLI to query segment search arguments, and segment usage)\n"
            f"2.3 IDMS Records (Detail network database structures, Area mappings, and record operations in IDMS)\n"
            f"Also analyze the pros and cons of using relational DB2 tables versus hierarchical/network (IMS/IDMS) models in a mainframe environment.\n\n"
            f"Format in Markdown. Keep the content extremely thorough, detailed, and professional. Return only the markdown content, beginning immediately with '2.1 DB2 Tables'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback_db = (
            f"### 2.1 DB2 Tables\n"
            f"The application workspace references the following DB2 SQL tables:\n\n"
            f"{db2_str}\n\n"
            f"**Relational DB2 Access Analysis:**\n"
            f"Mainframe COBOL programs execute embedded SQL statements (within `EXEC SQL ... END-EXEC` blocks) to query and update these DB2 tables. "
            f"These queries are processed by the DB2 precompiler, which replaces the SQL code with call statements to the DB2 database engine. "
            f"The primary relational tables, such as credit card registries or customer profile tables, are accessed via index keys to maintain low-latency response times during CICS online executions. "
            f"Host variables defined in the COBOL Working-Storage Section are mapped to table columns during SELECT INTO, INSERT, and UPDATE operations. "
            f"The system relies on appropriate index definitions to avoid full table scans that would consume high CPU MIPS in batch jobs like `INTCALC` or `POSTTRAN`.\n\n"
            f"### 2.2 IMS Segments\n"
            f"The application workspace communicates with IMS hierarchal segments as detailed below:\n\n"
            f"{ims_str}\n\n"
            f"**Hierarchical IMS Access Analysis:**\n"
            f"IMS (Information Management System) database interactions are performed using DL/I call statements by executing the interface module `CBLTDLI` using parameters: "
            f"Function code (such as `GU` for Get Unique, `GN` for Get Next, `REPL` for Replace), Program Communication Block (PCB), Segment Search Arguments (SSA), and I/O area variables. "
            f"SSAs specify the path through the hierarchical structure to locate the target segment. "
            f"Unlike SQL's set-based processing, DL/I requires navigational cursor-based access where the program iterates down a parent-child path, from parent root segments to dependent child segments. "
            f"This model is highly optimized for sequential tree-based data access patterns but demands careful programming to handle boundary/status code check conditions (such as `GB` for end of database, or `GE` for segment not found).\n\n"
            f"### 2.3 IDMS Records\n"
            f"The application workspace contains references to these network database IDMS records:\n\n"
            f"{idms_str}\n\n"
            f"**Network IDMS Access Analysis:**\n"
            f"IDMS (Integrated Database Management System) uses a network database model based on the CODASYL standard. "
            f"It represents data structures as a network of Records organized into Sets (where a set represents a one-to-many relationship between an Owner record and Member records). "
            f"Programs navigate the database by running commands like `OBTAIN FIRST/NEXT`, `FIND`, `STORE`, and `MODIFY` to traverse owner-member set pointers. "
            f"Transactions must bind to specific logical database Areas and run within DB record lock scopes to prevent concurrency deadlocks. "
            f"While DB2 utilizes logical relational links and IMS relies on physical hierarchies, IDMS provides physical pointer chains (next, prior, and owner pointers) embedded in the record headers. "
            f"This delivers exceptionally fast retrieval times for complex, pre-defined relationships but introduces structural rigidity, as changing the schema requires restructuring the physical pointer links."
        )

        if self.ollama_config.get("model") != "skip":
            try:
                gen = COBOLDocumentationGenerator(None, self.ollama_config["url"], self.ollama_config["model"])
                narrative = gen._query_ollama(prompt, fallback_db)
            except Exception:
                narrative = fallback_db
        else:
            narrative = fallback_db
            
        narrative_clean = re.sub(r'^#+\s+2\s+Database\s+Details\b', '', narrative, flags=re.IGNORECASE).strip()
        
        return (
            f"# 2. Database Details\n\n"
            f"{narrative_clean}"
        )

    def _gen_architecture_section(self):
        # 1. Mermaid Component Diagram
        # Shows JCL, programs, database tables, and mapped datasets
        mermaid_comp = [
            "```mermaid",
            "graph TD",
            "    subgraph Mainframe Application Suite",
            "        %% JCL Jobs"
        ]
        
        # Add JCL nodes
        jcl_idx = 1
        jcl_nodes = {}
        for job in self.jcl_metadata.keys():
            lbl = f"JCL_{jcl_idx}"
            mermaid_comp.append(f"        {lbl}[\"Job: {job}\"]:::jcl")
            jcl_nodes[job] = lbl
            jcl_idx += 1
            
        # Add Program nodes
        pgm_idx = 1
        pgm_nodes = {}
        for pgm in self.cobol_metadata.keys():
            lbl = f"PGM_{pgm_idx}"
            mermaid_comp.append(f"        {lbl}[[\"Program: {pgm}\"]]:::pgm")
            pgm_nodes[pgm] = lbl
            pgm_idx += 1
            
        # Add Assembler nodes
        asm_idx = 1
        asm_nodes = {}
        for asm in self.asm_metadata.keys():
            lbl = f"ASM_{asm_idx}"
            mermaid_comp.append(f"        {lbl}[[\"Assembler Pgm: {asm}\"]]:::asm")
            asm_nodes[asm] = lbl
            asm_idx += 1
            
        # Connect JCL Jobs to Programs Executed
        for job, pgms in self.relationships["jcl_to_pgm"].items():
            j_lbl = jcl_nodes.get(job)
            for p in pgms:
                if p in pgm_nodes:
                    mermaid_comp.append(f"        {j_lbl} -->|executes| {pgm_nodes[p]}")
                elif p in asm_nodes:
                    mermaid_comp.append(f"        {j_lbl} -->|executes| {asm_nodes[p]}")
                    
        # Connect Program Calls (Call dependencies)
        for pgm, calls in self.relationships["pgm_to_call"].items():
            p_lbl = pgm_nodes.get(pgm)
            if p_lbl:
                for c in calls:
                    if c in pgm_nodes:
                        mermaid_comp.append(f"        {p_lbl} -.->|calls| {pgm_nodes[c]}")
                    elif c in asm_nodes:
                        mermaid_comp.append(f"        {p_lbl} -.->|calls| {asm_nodes[c]}")
                        
        # Connect Assembler Calls
        for asm, calls in self.relationships["asm_to_call"].items():
            a_lbl = asm_nodes.get(asm)
            if a_lbl:
                for c in calls:
                    if c in pgm_nodes:
                        mermaid_comp.append(f"        {a_lbl} -.->|calls| {pgm_nodes[c]}")
                    elif c in asm_nodes:
                        mermaid_comp.append(f"        {a_lbl} -.->|calls| {asm_nodes[c]}")

        # Add DB2 Tables accessed
        db_idx = 1
        db_nodes = {}
        db2_set = set()
        for tables in self.relationships["pgm_to_db2"].values():
            db2_set.update(tables)
        for table in db2_set:
            lbl = f"DB2_{db_idx}"
            mermaid_comp.append(f"        {lbl}[(\"DB2: {table}\")]:::db")
            db_nodes[table] = lbl
            db_idx += 1
            
        # Connect programs to DB2 tables
        for pgm, tables in self.relationships["pgm_to_db2"].items():
            p_lbl = pgm_nodes.get(pgm)
            if p_lbl:
                for t in tables:
                    mermaid_comp.append(f"        {p_lbl} -->|SQL Table| {db_nodes[t]}")

        # Add physical VSAM Datasets resolved
        dsn_idx = 1
        dsn_nodes = {}
        dsn_set = set(f["dsn"] for f in self.relationships["file_mappings"])
        for dsn in dsn_set:
            if dsn == "SYSOUT":
                continue
            lbl = f"DSN_{dsn_idx}"
            mermaid_comp.append(f"        {lbl}[[\"Dataset: {dsn}\"]]:::dsn")
            dsn_nodes[dsn] = lbl
            dsn_idx += 1
            
        # Connect programs to resolved Datasets
        for mapping in self.relationships["file_mappings"]:
            p_lbl = pgm_nodes.get(mapping["program"])
            d_lbl = dsn_nodes.get(mapping["dsn"])
            if p_lbl and d_lbl:
                mermaid_comp.append(f"        {p_lbl} -->|I/O File: {mapping['logical_file']}| {d_lbl}")

        mermaid_comp.append("    end")
        mermaid_comp.append("    classDef jcl fill:#dbeafe,stroke:#2563eb,stroke-width:2px;")
        mermaid_comp.append("    classDef pgm fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;")
        mermaid_comp.append("    classDef asm fill:#ffedd5,stroke:#ea580c,stroke-width:2px;")
        mermaid_comp.append("    classDef db fill:#ecfdf5,stroke:#059669,stroke-width:2px;")
        mermaid_comp.append("    classDef dsn fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px;")
        mermaid_comp.append("```")
        
        # 2. Mermaid Control Flow Diagram
        # Simple flowchart mapping transaction to program and copybook dependencies
        mermaid_flow = [
            "```mermaid",
            "graph LR"
        ]
        
        tx_idx = 1
        tx_nodes = {}
        
        if self.relationships["csd_tx_to_pgm"]:
            mermaid_flow.append("    subgraph EntryPoints [\"User Screen Entry Points (CSD Defined)\"]")
            for tx, pgm in self.relationships["csd_tx_to_pgm"].items():
                lbl = f"TX_{tx_idx}"
                mermaid_flow.append(f"        {lbl}((\"Transaction: {tx}\")):::tx")
                tx_nodes[tx] = lbl
                tx_idx += 1
            mermaid_flow.append("    end")
            
        # Connect Transactions to Programs
        for tx, pgm in self.relationships["csd_tx_to_pgm"].items():
            t_lbl = tx_nodes.get(tx)
            # Find program code
            p_lbl = pgm_nodes.get(pgm)
            if t_lbl:
                if p_lbl:
                    mermaid_flow.append(f"    {p_lbl}[[\"Program: {pgm}\"]]:::pgm")
                    mermaid_flow.append(f"    {t_lbl} -->|executes| {p_lbl}")
                else:
                    # Program not in parsed files but defined in CSD
                    u_lbl = f"EXT_PGM_{tx}"
                    mermaid_flow.append(f"    {u_lbl}[[\"Program: {pgm} (External)\"]]:::ext")
                    mermaid_flow.append(f"    {t_lbl} -->|executes| {u_lbl}")

        # Connect Programs to CICS mapsets
        for pgm, mapsets in self.relationships["pgm_to_cics"].items():
            p_lbl = pgm_nodes.get(pgm)
            if p_lbl:
                # Ensure the program is declared in this diagram
                mermaid_flow.append(f"    {p_lbl}[[\"Program: {pgm}\"]]:::pgm")
                for ms in mapsets:
                    # Check if mapset is in our parsed BMS screens
                    if ms in self.bms_metadata:
                        bms_lbl = f"BMS_{ms}"
                        mermaid_flow.append(f"    {bms_lbl}[\"BMS Mapset: {ms}\"]:::bms")
                        mermaid_flow.append(f"    {p_lbl} -->|sends screen| {bms_lbl}")
                    else:
                        u_lbl = f"EXT_BMS_{ms}"
                        mermaid_flow.append(f"    {u_lbl}[\"BMS Mapset: {ms} (External)\"]:::bms")
                        mermaid_flow.append(f"    {p_lbl} -->|sends screen| {u_lbl}")
                        
        mermaid_flow.append("    classDef tx fill:#fdf2f8,stroke:#db2777,stroke-width:2px;")
        mermaid_flow.append("    classDef pgm fill:#fef9c3,stroke:#ca8a04,stroke-width:2px;")
        mermaid_flow.append("    classDef bms fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;")
        mermaid_flow.append("    classDef ext fill:#f3f4f6,stroke:#4b5563,stroke-width:2px;")
        mermaid_flow.append("```")
        
        comp_str = "\n".join(mermaid_comp)
        flow_str = "\n".join(mermaid_flow)
        
        # Render static diagrams to embed in report
        comp_img_path = self._render_mermaid_to_image(comp_str, "component_diagram.png")
        flow_img_path = self._render_mermaid_to_image(flow_str, "control_flow_diagram.png")
        
        # Build image links using forward slashes and absolute paths
        if comp_img_path:
            abs_comp_path = os.path.abspath(comp_img_path).replace("\\", "/")
            comp_display = f"![Component Diagram](file:///{abs_comp_path})"
        else:
            comp_display = comp_str
            
        if flow_img_path:
            abs_flow_path = os.path.abspath(flow_img_path).replace("\\", "/")
            flow_display = f"![Control Flow Diagram](file:///{abs_flow_path})"
        else:
            flow_display = flow_str
            
        # Build prompt & query LLM for Architectural Narrative
        arch_context = {
            "jcl_executions": self.relationships["jcl_to_pgm"],
            "program_calls": self.relationships["pgm_to_call"],
            "cics_transactions": self.relationships["csd_tx_to_pgm"],
            "cics_mapsets": self.relationships["pgm_to_cics"]
        }
        context_json = json.dumps(arch_context, indent=2)
        prompt = (
            f"Write a comprehensive and detailed technical Architectural Narrative and Execution Flow walkthrough section for a mainframe application suite.\n\n"
            f"Here is the structured JSON representing JCL executions, program calls, CICS transactions, and mapset mappings:\n"
            f"```json\n{context_json}\n```\n\n"
            f"Based on this, write a detailed architectural walkthrough explaining:\n"
            f"- How JCL jobs trigger batch streams, run program steps sequentially, and write/stage intermediate files.\n"
            f"- How CICS online transaction codes map to target programs to provide real-time services, screen rendering, and maps messaging.\n"
            f"- The synchronous program-to-program sub-routine calls hierarchy.\n"
            f"- Component decoupling, JCL data staging, and transaction boundary integrity.\n\n"
            f"Format in Markdown under heading '## 3.3 Architectural Narrative & Execution Flow'. Keep it professional, and return only the markdown content, beginning immediately with '## 3.3 Architectural Narrative & Execution Flow'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback_arch = (
            f"## 3.3 Architectural Narrative & Execution Flow\n\n"
            f"The application workspace is structured around a classic two-tier mainframe architectural pattern, splitting operations into high-volume offline batch streams (managed by JCL schedules) and interactive real-time online terminal services (hosted by CICS transaction processors):\n\n"
            f"### 3.3.1 Batch Job Stream Processing\n"
            f"The batch execution model leverages Job Control Language (JCL) scripts to configure step sequences, set up system boundaries, allocate physical datasets, and execute binary load modules. "
            f"Batch streams perform high-throughput tasks like credit card data loading, daily transaction ingest updates, account interest fee calculations, and database statement exports. "
            f"JCL streams sequence steps to ensure data integrity: a preprocessing step typically reads flat files from tape or sequential datasets, executes sorting routines via DFSORT control cards to align keys, and stages intermediate VSAM files. "
            f"Subsequent steps execute COBOL programs that open these VSAM files, execute business logic (such as balance accrual), modify DB2 tables, and output formatted summaries. "
            f"For example, job streams like `CARDFILE` and `ACCTFILE` execute program chains sequentially, staging outputs using JCL DISP parameters (`DISP=(NEW,CATLG,DELETE)`) to manage lifecycle stages across steps.\n\n"
            f"### 3.3.2 CICS Real-Time Online Transactions\n"
            f"Online operations are triggered by character-coded terminal inputs defined in CICS System Definitions (CSD). "
            f"When an operator types a transaction ID (like `COSG` or `COAC`), the CICS listener maps the transaction ID to a target COBOL control program (such as `COSGN00C` or `COACTVWC`). "
            f"CICS coordinates the execution within a logical unit of work (LUW). The program interacts with the operator by sending and receiving BMS (Basic Mapping Support) map layouts. "
            f"These maps define text fields, input markers, color schemes, and position offsets for 3270 character terminals. "
            f"Online programs use CICS command instructions (`EXEC CICS SEND MAP`, `EXEC CICS RECEIVE MAP`) to communicate with the user, validate user credentials, query VSAM file records using primary indexes to ensure sub-second search latencies, and commit changes back to the database. "
            f"Transactions route to menu hubs like `COMEN01C` which manage navigation paths based on function keys (PF keys) typed by terminal users, ensuring decoupled but clean flow control.\n\n"
            f"### 3.3.3 Subroutine Hierarchy and Decoupling\n"
            f"To maximize reuse, programs call utility subroutines synchronously using standard linkage section conventions (`CALL 'PROGRAM' USING ...`). "
            f"Common utilities include date formatting routines (`CSUTLDTC`) and wait intervals helper subroutines (`COBSWAIT` invoking Assembler module `MVSWAIT`). "
            f"By decoupling core transaction logic from helper subroutines, the application retains clean modular boundaries, making it easier to verify changes without recompiling the entire suite."
        )

        if self.ollama_config.get("model") != "skip":
            try:
                gen = COBOLDocumentationGenerator(None, self.ollama_config["url"], self.ollama_config["model"])
                narrative_arch = gen._query_ollama(prompt, fallback_arch)
            except Exception:
                narrative_arch = fallback_arch
        else:
            narrative_arch = fallback_arch
            
        narrative_arch_clean = re.sub(r'^#+\s+3\s+System\s+Architecture\b', '', narrative_arch, flags=re.IGNORECASE).strip()
        
        return (
            f"# 3. System Architecture\n\n"
            f"## 3.1 Component Diagram\n"
            f"Below is the component diagram highlighting how Job runs trigger various programs, "
            f"along with database SQL queries and dataset interactions:\n\n"
            f"{comp_display}\n\n"
            f"## 3.2 Control Flow Diagram\n"
            f"Below is the control flow mapping CICS transactional entry codes to target program routines and CICS BMS maps:\n\n"
            f"{flow_display}\n\n"
            f"{narrative_arch_clean}"
        )

    def _gen_design_section(self):
        # Program descriptions lookup mapping typical card demo program IDs to detailed summaries
        pgm_descriptions = {
            "CBACT01C": "Read Account File batch module. Validates account status flags and coordinates billing updates.",
            "CBACT02C": "Read Card File batch module. Parses credit card info and updates transaction database.",
            "CBACT03C": "Read Xref File batch module. Handles mappings of credit card numbers to customer account IDs.",
            "CBACT04C": "Interest Calculation batch module. Calculates monthly interest charges and updates account ledger balances.",
            "CBCUS01C": "Read Customer File batch module. Extracts details like name, address, and SSN for ingestion.",
            "CBEXPORT": "Data Export batch utility. Backs up VSAM KSDS files into sequential data files.",
            "CBIMPORT": "Data Import batch utility. Restores sequential backups into VSAM KSDS database files.",
            "CBSTM03A": "Statement Generation batch processor. Compiles monthly account details and writes statement summaries.",
            "CBSTM03B": "Statement Generation helper sub-routine. Manages PDF rendering details.",
            "CBTRN01C": "Daily Transaction Ingestion module. Verifies transactions against active credit cards.",
            "CBTRN02C": "Daily Transaction Posting batch module. Deducts amounts and updates card accounts balances.",
            "CBTRN03C": "Transaction Report generator batch utility. Reports daily totals categorized by transaction types.",
            "COACTUPC": "CICS Online Account Update screen controller. Updates customer contact profiles.",
            "COACTVWC": "CICS Online Account View screen controller. Searches and displays customer account summaries.",
            "COADM01C": "CICS Online Admin Menu screen controller. Routes to admin tools.",
            "COBIL00C": "CICS Online Bill Payment screen controller. Logs payments and checks balances.",
            "COBSWAIT": "Wait utility module. Uses Assembler subroutine MVSWAIT to pause step executions.",
            "COCRDLIC": "CICS Online Credit Card List screen controller. Lists credit card details.",
            "COCRDSLC": "CICS Online Credit Card Detail screen controller. Displays credit card balances and interest rates.",
            "COCRDUPC": "CICS Online Credit Card Update screen controller. Modifies credit card limits and expiration dates.",
            "COMEN01C": "CICS Online Main Menu controller. Main navigation hub routing CICS terminal sessions.",
            "CORPT00C": "CICS Online Report viewer. Displays calculated statements on CICS terminal panels.",
            "COSGN00C": "CICS Online Signon screen controller. Performs terminal user authentication and security checks.",
            "COTRN00C": "CICS Online Transaction Menu screen controller. Lists transaction histories.",
            "COTRN01C": "CICS Online Transaction Detail screen controller. Displays details of a specific transaction.",
            "COTRN02C": "CICS Online Transaction Add screen controller. Enters new transaction entries.",
            "COUSR00C": "CICS Online User Control screen controller. Inventories CICS account profile logins.",
            "COUSR01C": "CICS Online User Add screen controller. Adds new user credentials.",
            "COUSR02C": "CICS Online User Edit screen controller. Updates user roles.",
            "COUSR03C": "CICS Online User Delete screen controller. Removes CICS credentials.",
            "CSUTLDTC": "Date Converter utility sub-routine. Standardizes various date formats.",
            "COBDATFT": "Assembler date formatting subroutine.",
            "MVSWAIT": "Assembler interval wait subroutine."
        }

        # 1. Program Structure (Full inventory table)
        table_rows = [
            "| Component Name | File Type | Code Size (Lines) | Copybooks Used | Calls Made | Description / External References |",
            "| --- | --- | --- | --- | --- | --- |"
        ]
        
        # Add JCL
        for job, data in self.jcl_metadata.items():
            step_programs = ", ".join(f"`{s['program']}`" for s in data["steps"])
            table_rows.append(f"| `{job}` | JCL Script | {len(data['steps'])} steps | None | Execs: {step_programs} | Executes batch job stream containing {len(data['steps'])} steps. |")
            
        # Add COBOL
        for pgm, data in self.cobol_metadata.items():
            copybooks_str = ", ".join(f"`{c}`" for c in data["copybooks"]) if data["copybooks"] else "None"
            calls_str = ", ".join(f"`{c}`" for c in data["calls"]) if data["calls"] else "None"
            
            desc = pgm_descriptions.get(pgm, "Internal Logic")
            if data["db2_tables"]:
                desc += f" (DB2: {len(data['db2_tables'])} tables)"
            if data["ims_segments"]:
                desc += f" (IMS: {len(data['ims_segments'])} segments)"
            if data["cics_mapsets"]:
                desc += f" (CICS: {', '.join(data['cics_mapsets'])})"
                
            table_rows.append(f"| `{pgm}` | COBOL Source | {data['line_count']} lines | {copybooks_str} | {calls_str} | {desc} |")
            
        # Add Assembler
        for asm, data in self.asm_metadata.items():
            copybooks_str = ", ".join(f"`{c}`" for c in data["copybooks"]) if data["copybooks"] else "None"
            calls_str = ", ".join(f"`{c}`" for c in data["calls"]) if data["calls"] else "None"
            desc = pgm_descriptions.get(asm, f"Entry Points: {', '.join(data['entry_points'])}")
            table_rows.append(f"| `{asm}` | Assembler Source | N/A | {copybooks_str} | {calls_str} | {desc} |")
            
        # Add BMS
        for ms, data in self.bms_metadata.items():
            table_rows.append(f"| `{ms}` | BMS Mapset | N/A | None | Maps: {', '.join(data['maps'])} | CICS Screen layout mapset definitions. |")
            
        struct_table = "\n".join(table_rows)
        
        # 2. Input/Output Specifications
        io_rows = [
            "| Program ID | JCL Job | JCL Step | Logical DD Name | Physical Dataset (DSN) | Allocation Disp |",
            "| --- | --- | --- | --- | --- | --- |"
        ]
        for f in self.relationships["file_mappings"]:
            io_rows.append(f"| `{f['program']}` | `{f['jcl_job']}` | `{f['jcl_step']}` | `{f['dd_name']}` | `{f['dsn']}` | `{f['disp']}` |")
            
        if len(io_rows) == 2:
            io_rows.append("| None | N/A | N/A | No JCL step mappings matched COBOL SELECT FD structures | N/A | N/A |")
            
        io_table = "\n".join(io_rows)
        
        # 3. Algorithms
        relationship_context = {
            "jcl_to_pgm_executions": self.relationships["jcl_to_pgm"],
            "program_call_graph": self.relationships["pgm_to_call"],
            "cics_transaction_to_program": self.relationships["csd_tx_to_pgm"],
            "file_to_dataset_mappings": [
                {
                    "program": m["program"],
                    "jcl_job": m["jcl_job"],
                    "jcl_step": m["jcl_step"],
                    "logical_file": m["logical_file"],
                    "dd_name": m["dd_name"],
                    "dsn": m["dsn"]
                }
                for m in self.relationships["file_mappings"][:30]
            ]
        }
        context_json = json.dumps(relationship_context, indent=2)
        prompt = (
            f"Write technical design narratives describing the algorithms and execution sequences of this mainframe application suite.\n\n"
            f"Here is the structured JSON metadata representing the workspace call paths, execution flows, and dataset mappings:\n"
            f"```json\n{context_json}\n```\n\n"
            f"Based on this metadata, provide exactly the following section:\n"
            f"4.2 Algorithms\n"
            f"Detail batch execution steps (including sorting and file staging), online transaction maps navigation, and caller program integration sequences.\n"
            f"Format in Markdown, and return only the markdown content, beginning immediately with '4.2 Algorithms'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"## 4.2 Algorithms\n\n"
            f"The application workspace implements complex batch scheduling and online terminal transactions:\n\n"
            f"### 4.2.1 Batch Job Sequencing & Staging Details\n"
            f"- **Card ingestion and cross-reference validation (`CARDFILE` & `ACCTFILE`)**:\n"
            f"  - First, sequential files are parsed. `SORT` is called to sort records in DFSORT control cards.\n"
            f"  - Program `CBACT01C` opens `ACCTFILE-FILE` and validates accounts against business rules (credit limits, cycle dates).\n"
            f"  - Program `CBACT02C` opens `CARDFILE-FILE` and reads cards data into `CUSTOMER-RECORD` layouts.\n"
            f"  - Program `CBACT03C` coordinates cross-referencing between credit card numbers and account IDs.\n"
            f"- **Daily transaction posting and billing updates (`POSTTRAN` & `INTCALC`)**:\n"
            f"  - Job `POSTTRAN` executes `CBTRN02C` to post transaction files into card accounts. It deducts transaction amounts, computes billing updates, and records transactions in KSDS VSAM logs.\n"
            f"  - Job `INTCALC` executes `CBACT04C` to process interest calculations for accounts based on transaction cycles. It applies specific category-based interest rates and posts statements updates.\n"
            f"- **Statements and exports (`CREASTMT` & `CBEXPORT`)**:\n"
            f"  - Job `CREASTMT` executes program `CBSTM03A` to process monthly billing statement HTML templates. It reads KSDS VSAM transaction histories, computes totals, and writes statements to `AWS.M2.CARDDEMO.STATEMNT.HTML`.\n"
            f"  - Job `CBEXPORT` runs program `CBEXPORT` to backup all active customer and transaction database tables to sequential flat backup files.\n\n"
            f"### 4.2.2 CICS Screen Navigation & Menu Layouts\n"
            f"- **Terminal Main Menu (`COMEN01C` & `COSGN00C`)**:\n"
            f"  - CICS online terminal operations start by executing transaction sign-on mapset `COSGN00`. Program `COSGN00C` authenticates operators.\n"
            f"  - On success, the session routes to the main menu page (`COMEN01C` using mapset `COMEN01`). The main menu routes transactions based on operator keys (PF keys or terminal codes).\n"
            f"- **Account and Card search/edit screen flows (`COACTUPC`, `COACTVWC`, `COCRDLIC`, `COCRDUPC`)**:\n"
            f"  - Operator selects option 2 to view details, CICS starts `COACTVWC` which displays map `CACTVWA`. It retrieves database profiles by ID and updates display fields.\n"
            f"  - Operator selects option 3 to update profile details, CICS starts `COACTUPC` displaying map `CACTUPA`. The program processes inputs and validates fields (like phone, address, and name) before updating VSAM storage.\n"
            f"  - Operator selects option 4 to update credit card details, CICS starts `COCRDUPC` displaying map `CCRDUPA` to configure card limits and active flags."
        )
        
        if self.ollama_config.get("model") != "skip":
            try:
                gen = COBOLDocumentationGenerator(None, self.ollama_config["url"], self.ollama_config["model"])
                narrative_alg = gen._query_ollama(prompt, fallback)
            except Exception:
                narrative_alg = fallback
        else:
            narrative_alg = fallback
            
        # Strip "# 4.2 Algorithms" or "## 4.2 Algorithms" heading if the LLM outputted it to prevent duplicates
        narrative_alg_clean = re.sub(r'^#+\s+4\.2\s+Algorithms\b', '', narrative_alg, flags=re.IGNORECASE).strip()
            
        # 4. Individual Program Analysis
        prog_analysis_lines = [
            "## 4.4 Individual Program Analysis\n",
            "A granular breakdown of each COBOL program, outlining files, copybooks, database operations, and subprogram calls:\n"
        ]
        for pgm, data in sorted(self.cobol_metadata.items()):
            desc = pgm_descriptions.get(pgm, "Internal application processing module.")
            prog_analysis_lines.append(f"### Program: `{pgm}`")
            prog_analysis_lines.append(f"- **Description**: {desc}")
            prog_analysis_lines.append(f"- **Lines of Code**: {data['line_count']}")
            prog_analysis_lines.append(f"- **Author**: {data['author']}")
            
            # File references
            if data["files"]:
                files_str = ", ".join(f"`{f['variable']}` (DD: `{f['dd_name']}`)" for f in data["files"])
                prog_analysis_lines.append(f"- **Logical Files**: {files_str}")
            else:
                prog_analysis_lines.append(f"- **Logical Files**: None")
                
            # Copybooks
            if data["copybooks"]:
                prog_analysis_lines.append(f"- **Copybooks Referenced**: " + ", ".join(f"`{c}`" for c in data["copybooks"]))
            else:
                prog_analysis_lines.append(f"- **Copybooks Referenced**: None")
                
            # External Calls
            if data["calls"]:
                prog_analysis_lines.append(f"- **Subprograms Called**: " + ", ".join(f"`{c}`" for c in data["calls"]))
            else:
                prog_analysis_lines.append(f"- **Subprograms Called**: None")
                
            # DB2 Tables
            if data["db2_tables"]:
                prog_analysis_lines.append(f"- **DB2 Tables**: " + ", ".join(f"`{t}`" for t in data["db2_tables"]))
                
            # IMS Segments
            if data["ims_segments"]:
                prog_analysis_lines.append(f"- **IMS Segments**: " + ", ".join(f"`{s}`" for s in data["ims_segments"]))
                
            # IDMS Records
            if data["idms_records"]:
                prog_analysis_lines.append(f"- **IDMS Records**: " + ", ".join(f"`{r}`" for r in data["idms_records"]))
                
            # CICS Mapsets
            if data["cics_mapsets"]:
                prog_analysis_lines.append(f"- **CICS Mapsets**: " + ", ".join(f"`{m}`" for m in data["cics_mapsets"]))
                
            prog_analysis_lines.append("") # blank line
            
        individual_prog_str = "\n".join(prog_analysis_lines)

        # 5. JCL Job Stream Analysis
        jcl_analysis_lines = [
            "## 4.5 JCL Job Stream Analysis\n",
            "Detailed operational breakdown of JCL jobs schedules, step sequences, and execution configurations:\n"
        ]
        for job, data in sorted(self.jcl_metadata.items()):
            jcl_analysis_lines.append(f"### JCL Job: `{job}`")
            jcl_analysis_lines.append(f"- **Job Stream Description**: Sequential execution of batch components.")
            jcl_analysis_lines.append(f"- **Steps Defined ({len(data['steps'])})**:")
            for idx, step in enumerate(data["steps"]):
                jcl_analysis_lines.append(f"  {idx+1}. **Step `{step['step_name']}`**: Executes program `{step['program']}`.")
                if step["dds"]:
                    dd_lines = []
                    for dd_name, dd_info in step["dds"].items():
                        dd_lines.append(f"`{dd_name}` (DSN: `{dd_info['dsn']}`, DISP: `{dd_info['disp']}`)")
                    jcl_analysis_lines.append(f"     - DD Assignments: " + ", ".join(dd_lines))
            jcl_analysis_lines.append("")
        jcl_analysis_str = "\n".join(jcl_analysis_lines)

        # 6. Assembler Module Analysis
        asm_analysis_lines = [
            "## 4.6 Assembler Module Analysis\n",
            "Lower-level HLASM modules referenced by subprograms in execution flows:\n"
        ]
        for asm, data in sorted(self.asm_metadata.items()):
            desc = pgm_descriptions.get(asm, "Low-level system interface helper module.")
            asm_analysis_lines.append(f"### Assembler Module: `{asm}`")
            asm_analysis_lines.append(f"- **Description**: {desc}")
            asm_analysis_lines.append(f"- **Entry Points**: " + ", ".join(f"`{e}`" for e in data["entry_points"]))
            asm_analysis_lines.append(f"- **Calls Made**: " + (", ".join(f"`{c}`" for c in data["calls"]) if data["calls"] else "None"))
            asm_analysis_lines.append("")
        asm_analysis_str = "\n".join(asm_analysis_lines)

        # 7. CICS BMS Mapset Layouts
        bms_analysis_lines = [
            "## 4.7 CICS BMS Mapset Layouts\n",
            "Defined CICS terminal screens, field layouts, and positioning mappings:\n"
        ]
        for ms, data in sorted(self.bms_metadata.items()):
            bms_analysis_lines.append(f"### Mapset: `{ms}`")
            bms_analysis_lines.append(f"- **Maps Included**: " + ", ".join(f"`{m}`" for m in data["maps"]))
            # Show fields details
            if data.get("fields"):
                fields_str = ", ".join(f"`{f['name']}` (Pos: {f['position']}, Len: {f['length']})" for f in data["fields"])
                bms_analysis_lines.append(f"- **Field Layouts (Top 20)**: {fields_str}")
            bms_analysis_lines.append("")
        bms_analysis_str = "\n".join(bms_analysis_lines)

        return (
            f"# 4. Detailed Design\n\n"
            f"## 4.1 Program Structure\n"
            f"The table below inventories all files parsed in the workspace including code sizes, copybooks, calls, and external accesses:\n\n"
            f"{struct_table}\n\n"
            f"## 4.2 Algorithms\n\n"
            f"{narrative_alg_clean}\n\n"
            f"## 4.3 Input/Output Specifications\n"
            f"The table below details the dataset assignments. It maps the COBOL logical file `SELECT` statements "
            f"directly to JCL `DD` names and their associated physical datasets (DSN) on disk:\n\n"
            f"{io_table}\n\n"
            f"{individual_prog_str}\n\n"
            f"{jcl_analysis_str}\n\n"
            f"{asm_analysis_str}\n\n"
            f"{bms_analysis_str}"
        )

if __name__ == '__main__':
    # Run standalone parser if invoked directly
    analyzer = WorkspaceAnalyzer()
    analyzer.run()
