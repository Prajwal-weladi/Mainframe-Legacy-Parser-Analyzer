import re
import os

class JCLParser:
    def __init__(self):
        self.metadata = {
            "file_name": "UNKNOWN",
            "job_name": "UNKNOWN",
            "steps": [],
            "includes": [],
            "jcllibs": [],
            "steplibs": [],
            "job_cond": None,
            "conditionals": []
        }

    def parse(self, file_path):
        """
        Parses steps, parameters, library paths, conditionals, and data definition (DD) cards from a JCL file.
        """
        self.metadata["file_name"] = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                
            job_name = os.path.splitext(os.path.basename(file_path))[0].upper()
            steps = []
            current_step = None
            
            # Clean comments and merge continuation lines
            cleaned_lines = []
            i = 0
            while i < len(lines):
                line = lines[i].rstrip()
                if line.startswith("//*") or not line.startswith("//"):
                    # Ignore comments and non-jcl lines
                    i += 1
                    continue
                
                # JCL lines ending with a comma are continuation lines
                merged_line = line
                while merged_line.endswith(",") and i + 1 < len(lines):
                    next_line = lines[i+1].rstrip()
                    if next_line.startswith("//*"):
                        i += 1
                        continue
                    if next_line.startswith("//"):
                        # Extract the continuation parameters
                        content = next_line[2:].lstrip()
                        merged_line += " " + content
                        i += 1
                    else:
                        break
                cleaned_lines.append(merged_line)
                i += 1
                
            # Parse Job cards, EXEC steps, and DD datasets
            for line in cleaned_lines:
                # JOB Name card
                job_match = re.match(r'^//\s*([\w\-]+)\s+JOB\b(.*)', line, re.IGNORECASE)
                if job_match:
                    job_name = job_match.group(1).upper()
                    job_rest = job_match.group(2)
                    # Extract COND parameter on JOB
                    cond_match = re.search(r'\bCOND\s*=\s*(\([^)]+\)|[\w\-]+)', job_rest, re.IGNORECASE)
                    if cond_match:
                        self.metadata["job_cond"] = cond_match.group(1).upper()
                    continue

                # JCLLIB Search Order card
                jcllib_match = re.search(r'//\s*JCLLIB\s+ORDER\s*=\s*(.*)', line, re.IGNORECASE)
                if jcllib_match:
                    order_val = jcllib_match.group(1).strip("() '\"")
                    self.metadata["jcllibs"].append(order_val.upper())
                    continue

                # INCLUDE member card
                include_match = re.search(r'//\s*([\w\-]+)?\s*INCLUDE\s+MEMBER\s*=\s*([\w\-]+)', line, re.IGNORECASE)
                if include_match:
                    member = include_match.group(2).upper()
                    self.metadata["includes"].append(member)
                    continue

                # Logical Control Block checks
                if_match = re.search(r'//\s*IF\s+(.*)\s+THEN', line, re.IGNORECASE)
                if if_match:
                    self.metadata["conditionals"].append(f"IF {if_match.group(1).strip()}")
                    continue
                else_match = re.search(r'//\s*ELSE\b', line, re.IGNORECASE)
                if else_match:
                    self.metadata["conditionals"].append("ELSE")
                    continue
                endif_match = re.search(r'//\s*ENDIF\b', line, re.IGNORECASE)
                if endif_match:
                    self.metadata["conditionals"].append("ENDIF")
                    continue
                    
                # EXEC statement cards
                exec_match = re.search(r'//\s*([\w\-]+)?\s+EXEC\s+(?:PGM|PROC)\s*=\s*([\w\-]+)(.*)', line, re.IGNORECASE)
                if not exec_match:
                    # Alternative direct exec call (e.g. //STEP1 EXEC MYPROC)
                    exec_match = re.search(r'//\s*([\w\-]+)?\s+EXEC\s+([\w\-]+)(.*)', line, re.IGNORECASE)
                    
                if exec_match:
                    step_lbl = exec_match.group(1).upper() if exec_match.group(1) else f"STEP_{len(steps)+1}"
                    exec_target = exec_match.group(2).upper()
                    exec_rest = exec_match.group(3) or ""
                    
                    if exec_target in ["COND", "PARM", "ACCT"]:
                        continue  # skip execution parameter matches
                    
                    # Extract COND parameter on Step
                    step_cond = None
                    cond_match = re.search(r'\bCOND\s*=\s*(\([^)]+\)|[\w\-]+)', exec_rest, re.IGNORECASE)
                    if cond_match:
                        step_cond = cond_match.group(1).upper()
                        
                    current_step = {
                        "step_name": step_lbl,
                        "program": exec_target,
                        "dds": [],
                        "cond": step_cond
                    }
                    steps.append(current_step)
                    continue
                    
                # DD resource cards
                dd_match = re.search(r'//\s*([\w\-]+)\s+DD\s+(.*)$', line, re.IGNORECASE)
                if dd_match and current_step:
                    dd_name = dd_match.group(1).upper()
                    dd_params = dd_match.group(2)
                    
                    # Dataset Name
                    dsn_match = re.search(r'\bDSN(?:AME)?\s*=\s*([\w\.\-\(\)]+)', dd_params, re.IGNORECASE)
                    dsn = dsn_match.group(1).upper() if dsn_match else "SYSOUT"
                    dsn = dsn.strip("'\"")
                    
                    # Disposition
                    disp_match = re.search(r'\bDISP\s*=\s*\(([\w\s,]+)\)', dd_params, re.IGNORECASE)
                    if not disp_match:
                        disp_match = re.search(r'\bDISP\s*=\s*([\w\-]+)', dd_params, re.IGNORECASE)
                    disp = disp_match.group(1).upper() if disp_match else "SHR"
                    
                    # Collect JOBLIB/STEPLIB libraries
                    if dd_name in ["STEPLIB", "JOBLIB"]:
                        self.metadata["steplibs"].append(dsn)
                        
                    current_step["dds"].append({
                        "dd_name": dd_name,
                        "dsn": dsn,
                        "disp": disp,
                        "raw_params": dd_params.strip()
                    })
            
            self.metadata["job_name"] = job_name
            self.metadata["steps"] = steps
        except Exception as e:
            print(f"Warning: Failed to parse JCL {file_path}: {e}")
            
        return self.metadata
