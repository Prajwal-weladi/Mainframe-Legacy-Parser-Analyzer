import re
import os
from preprocessor import COBOLPreprocessor

class COBOLParser:
    def __init__(self, copybook_dir=None):
        self.copybook_dir = copybook_dir
        self.preprocessor = COBOLPreprocessor()
        self.metadata = {
            "program_id": "UNKNOWN",
            "author": "UNKNOWN",
            "files": [],       # {variable, dataset}
            "variables": [],   # {name, level, pic, section, is_pii, source_copybook}
            "paragraphs": {},   # paragraph_name -> paragraph_data
            "paragraph_order": [] # List of paragraph names in order of appearance
        }
        self.var_value_map = {} # Maps variable name -> value (useful for constants)

    def parse(self, file_path):
        """
        Main entry point to parse a COBOL file and return extracted metadata.
        """
        clean_text, line_mapping = self.preprocessor.preprocess(file_path)
        self._parse_divisions(clean_text, line_mapping)
        return self.metadata

    def _parse_divisions(self, text, line_mapping):
        divisions = ["IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE"]
        lines = text.split('\n')
        
        current_division = None
        division_lines = {div: [] for div in divisions}
        division_line_mappings = {div: {} for div in divisions}
        
        for idx, line in enumerate(lines):
            orig_line = line_mapping.get(idx, idx + 1)
            match_div = re.match(r'^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION\b', line, re.IGNORECASE)
            if match_div:
                current_division = match_div.group(1).upper()
            elif current_division:
                division_lines[current_division].append(line)
                division_line_mappings[current_division][len(division_lines[current_division]) - 1] = orig_line

        self._parse_identification_division(division_lines["IDENTIFICATION"])
        self._parse_environment_division(division_lines["ENVIRONMENT"])
        self._parse_data_division(division_lines["DATA"], division_line_mappings["DATA"])
        self._parse_procedure_division(division_lines["PROCEDURE"], division_line_mappings["PROCEDURE"])

    def _parse_identification_division(self, lines):
        text = "\n".join(lines)
        prog_id_match = re.search(r'PROGRAM-ID\.\s*([\w-]+)', text, re.IGNORECASE)
        if prog_id_match:
            self.metadata["program_id"] = prog_id_match.group(1).upper()
        
        author_match = re.search(r'AUTHOR\.\s*([^\.]+)', text, re.IGNORECASE)
        if author_match:
            self.metadata["author"] = author_match.group(1).strip()

    def _parse_environment_division(self, lines):
        text = "\n".join(lines)
        select_matches = re.finditer(r'SELECT\s+([\w-]+)\s+ASSIGN\s+TO\s+[\'"]?([\w-]+)[\'"]?', text, re.IGNORECASE)
        for match in select_matches:
            self.metadata["files"].append({
                "variable": match.group(1).upper(),
                "dataset": match.group(2).upper()
            })

    def _parse_data_division(self, lines, line_map):
        sections = ["FILE", "WORKING-STORAGE", "LINKAGE"]
        section_lines = {sec: [] for sec in sections}
        
        current_section = None
        for idx, line in enumerate(lines):
            match_sec = re.match(r'^\s*(FILE|WORKING-STORAGE|LINKAGE)\s+SECTION\b', line, re.IGNORECASE)
            if match_sec:
                current_section = match_sec.group(1).upper()
            elif current_section:
                section_lines[current_section].append((line, line_map[idx]))

        for sec in sections:
            self._parse_data_section(sec, section_lines[sec])

    def _parse_data_section(self, section_name, lines_with_nums, copybook_name=None):
        i = 0
        while i < len(lines_with_nums):
            line, orig_line = lines_with_nums[i]
            
            copy_match = re.match(r'^\s*COPY\s+([\w-]+)\b', line.strip(), re.IGNORECASE)
            if copy_match:
                cp_name = copy_match.group(1).upper()
                self._resolve_copybook(cp_name, section_name)
                i += 1
                continue

            var_match = re.match(r'^\s*(0[1-9]|[1-4][0-9]|77|88)\s+([\w-]+)\b', line.strip(), re.IGNORECASE)
            if var_match:
                level = int(var_match.group(1))
                var_name = var_match.group(2).upper()
                
                if var_name in ["SELECT", "FD", "COPY"]:
                    i += 1
                    continue

                pic = None
                value = None
                
                pic_match = re.search(r'\b(PIC|PICTURE)\s+(IS\s+)?([^\s\.\,]+)', line, re.IGNORECASE)
                if pic_match:
                    pic = pic_match.group(3).rstrip('.')
                
                val_match = re.search(r'\bVALUE\s+(IS\s+)?[\'"]?([^\'\"\.\,]+)[\'"]?', line, re.IGNORECASE)
                if val_match:
                    value = val_match.group(2).strip()
                    self.var_value_map[var_name] = value

                is_pii = self._check_pii_keywords(var_name)

                self.metadata["variables"].append({
                    "name": var_name,
                    "level": level,
                    "pic": pic,
                    "value": value,
                    "section": section_name,
                    "is_pii": is_pii,
                    "source_copybook": copybook_name
                })

            i += 1

    def _resolve_copybook(self, copybook_name, section_name):
        if not self.copybook_dir:
            return

        extensions = [".cpy", ".cbl", ".cop", "", ".txt"]
        found_path = None
        for ext in extensions:
            path = os.path.join(self.copybook_dir, f"{copybook_name}{ext}")
            if os.path.exists(path):
                found_path = path
                break
            path = os.path.join(self.copybook_dir, f"{copybook_name.lower()}{ext}")
            if os.path.exists(path):
                found_path = path
                break

        if not found_path:
            try:
                for f in os.listdir(self.copybook_dir):
                    base, ext = os.path.splitext(f)
                    if base.upper() == copybook_name.upper() and ext.lower() in [".cpy", ".cbl", ".cop", ".txt", ""]:
                        found_path = os.path.join(self.copybook_dir, f)
                        break
            except Exception:
                pass

        if found_path:
            try:
                cp_preprocessor = COBOLPreprocessor()
                clean_cp, cp_line_map = cp_preprocessor.preprocess(found_path)
                cp_lines = clean_cp.split('\n')
                cp_lines_with_nums = [(line, cp_line_map.get(idx, idx+1)) for idx, line in enumerate(cp_lines)]
                self._parse_data_section(section_name, cp_lines_with_nums, copybook_name=copybook_name)
            except Exception as e:
                print(f"Warning: Failed to parse copybook {copybook_name}: {e}")
        else:
            print(f"Warning: Copybook {copybook_name} not found in {self.copybook_dir}")

    def _check_pii_keywords(self, name):
        pii_keywords = ["SSN", "SOCIAL", "ACC", "NAME", "BIRTH", "DOB", "ADDR", "PHONE", "EMAIL", "TAX", "SAL", "CREDIT", "CARD", "CVV"]
        for kw in pii_keywords:
            if kw in name:
                return True
        return False

    def _parse_procedure_division(self, lines, line_map):
        current_section = "GENERAL"
        current_paragraph = None
        
        paragraph_statements = []
        paragraph_start_line = 1
        
        def commit_paragraph(name, end_line):
            if name:
                content_text = "\n".join(paragraph_statements)
                self.metadata["paragraphs"][name] = {
                    "section": current_section,
                    "start_line": paragraph_start_line,
                    "end_line": end_line,
                    "content": content_text,
                    "calls": [],
                    "external_calls": [],
                    "db2": [],
                    "ims": [],
                    "idms": [],
                    "mq": [],
                    "cics": [],
                    "vsam": [],
                    "moves": []
                }
                if name not in self.metadata["paragraph_order"]:
                    self.metadata["paragraph_order"].append(name)
        
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            orig_line = line_map.get(idx, idx + 1)
            
            sec_match = re.match(r'^ {0,3}([\w-]+)\s+SECTION\s*\.', line, re.IGNORECASE)
            if sec_match:
                commit_paragraph(current_paragraph, orig_line - 1)
                current_section = sec_match.group(1).upper()
                current_paragraph = None
                paragraph_statements = []
                idx += 1
                continue

            para_match = re.match(r'^ {0,3}([\w-]+)\s*\.\s*$', line, re.IGNORECASE)
            para_match_inline = re.match(r'^ {0,3}([\w-]+)\s*\.\s+(.+)$', line, re.IGNORECASE)
            
            if para_match:
                p_name = para_match.group(1).upper()
                if p_name not in ["EXIT", "GOBACK", "STOP", "ELSE", "END-IF", "END-PERFORM", "END-READ", "END-WRITE", "END-EXEC", "EXEC", "CICS", "SQL"]:
                    commit_paragraph(current_paragraph, orig_line - 1)
                    current_paragraph = p_name
                    paragraph_statements = []
                    paragraph_start_line = orig_line
                    idx += 1
                    continue
            elif para_match_inline:
                p_name = para_match_inline.group(1).upper()
                if p_name not in ["EXIT", "GOBACK", "STOP", "ELSE", "END-IF", "END-PERFORM", "END-READ", "END-WRITE", "END-EXEC", "EXEC", "CICS", "SQL"]:
                    commit_paragraph(current_paragraph, orig_line - 1)
                    current_paragraph = p_name
                    paragraph_statements = [para_match_inline.group(2)]
                    paragraph_start_line = orig_line
                    idx += 1
                    continue

            if current_paragraph:
                paragraph_statements.append(line)
            else:
                current_paragraph = "PROC-ENTRY"
                paragraph_start_line = orig_line
                paragraph_statements.append(line)
                
            idx += 1

        if current_paragraph:
            last_line = line_map.get(len(lines) - 1, len(lines))
            commit_paragraph(current_paragraph, last_line)

        self._analyze_paragraph_statements()

    def _analyze_paragraph_statements(self):
        for para_name, para_data in self.metadata["paragraphs"].items():
            content = para_data["content"]

            sql_blocks = re.findall(r'EXEC\s+SQL\s+(.*?)\s+END-EXEC', content, re.DOTALL | re.IGNORECASE)
            for sql in sql_blocks:
                select_match = re.search(r'\bFROM\s+(\w+)\b', sql, re.IGNORECASE)
                insert_match = re.search(r'\bINSERT\s+INTO\s+(\w+)\b', sql, re.IGNORECASE)
                update_match = re.search(r'\bUPDATE\s+(\w+)\b', sql, re.IGNORECASE)
                delete_match = re.search(r'\bDELETE\s+FROM\s+(\w+)\b', sql, re.IGNORECASE)
                
                cmd_type = "UNKNOWN"
                table = "UNKNOWN"
                
                if select_match:
                    cmd_type = "SELECT"
                    table = select_match.group(1).upper()
                elif insert_match:
                    cmd_type = "INSERT"
                    table = insert_match.group(1).upper()
                elif update_match:
                    cmd_type = "UPDATE"
                    table = update_match.group(1).upper()
                elif delete_match:
                    cmd_type = "DELETE"
                    table = delete_match.group(1).upper()
                else:
                    first_word = sql.strip().split()[0].upper() if sql.strip() else "SQL"
                    cmd_type = first_word
                
                para_data["db2"].append({
                    "command": cmd_type,
                    "table": table,
                    "raw_sql": sql.strip()
                })

            cics_blocks = re.findall(r'EXEC\s+CICS\s+(.*?)\s+END-CICS', content, re.DOTALL | re.IGNORECASE)
            for cics in cics_blocks:
                cics_clean = re.sub(r'\s+', ' ', cics.strip())
                verb = "CICS"
                map_name = None
                mapset = None
                
                map_match = re.search(r'\bMAP\s*\(\s*[\'"]?([\w-]+)[\'"]?\s*\)', cics_clean, re.IGNORECASE)
                mapset_match = re.search(r'\bMAPSET\s*\(\s*[\'"]?([\w-]+)[\'"]?\s*\)', cics_clean, re.IGNORECASE)
                
                if map_match:
                    map_name = map_match.group(1).upper()
                if mapset_match:
                    mapset = mapset_match.group(1).upper()
                
                first_words = cics_clean.split()
                if len(first_words) > 1:
                    verb = f"{first_words[0].upper()} {first_words[1].upper()}"
                elif len(first_words) > 0:
                    verb = first_words[0].upper()
                    
                para_data["cics"].append({
                    "verb": verb,
                    "map": map_name,
                    "mapset": mapset,
                    "raw_cics": cics_clean
                })

            clean_content = content
            clean_content = re.sub(r'EXEC\s+SQL\s+.*?\s+END-EXEC', '', clean_content, flags=re.DOTALL | re.IGNORECASE)
            clean_content = re.sub(r'EXEC\s+CICS\s+.*?\s+END-CICS', '', clean_content, flags=re.DOTALL | re.IGNORECASE)

            perform_matches = re.finditer(r'\bPERFORM\s+([\w-]+)(?:\s+THRU\s+([\w-]+))?\b', clean_content, re.IGNORECASE)
            for match in perform_matches:
                target = match.group(1).upper()
                thru_target = match.group(2).upper() if match.group(2) else None
                para_data["calls"].append({
                    "type": "PERFORM",
                    "target": target,
                    "thru": thru_target
                })

            goto_matches = re.finditer(r'\bGO\s+TO\s+([\w-]+)\b', clean_content, re.IGNORECASE)
            for match in goto_matches:
                para_data["calls"].append({
                    "type": "GOTO",
                    "target": match.group(1).upper(),
                    "thru": None
                })

            call_matches = re.finditer(r'\bCALL\s+[\'"]([\w-]+)[\'"](?:\s+USING\s+([^\.]+))?\b', clean_content, re.IGNORECASE)
            for match in call_matches:
                subprogram = match.group(1).upper()
                using_args_str = match.group(2).strip() if match.group(2) else ""
                
                if subprogram == "CBLTDLI":
                    args = [a.strip().upper() for a in using_args_str.split(',') or using_args_str.split()]
                    if len(args) == 1 and ' ' in using_args_str:
                        args = [a.strip().upper() for a in re.split(r'\s+', using_args_str)]
                        
                    func_code = args[0] if len(args) > 0 else "UNKNOWN"
                    resolved_func = self.var_value_map.get(func_code, func_code).strip("'\" ")
                    
                    para_data["ims"].append({
                        "function": resolved_func,
                        "arguments": args[1:]
                    })
                elif subprogram in ["MQCONN", "MQOPEN", "MQPUT", "MQGET", "MQCLOSE", "MQDISC"]:
                    para_data["mq"].append({
                        "call_type": subprogram,
                        "arguments": [a.strip().upper() for a in re.split(r'[\s,]+', using_args_str) if a.strip()]
                    })
                else:
                    para_data["external_calls"].append({
                        "program": subprogram,
                        "arguments": [a.strip().upper() for a in re.split(r'[\s,]+', using_args_str) if a.strip()]
                    })

            idms_patterns = [
                r'\bOBTAIN\s+(?:FIRST|NEXT|ANY)?\s*([\w-]+)\s+(?:WITHIN\s+([\w-]+))?',
                r'\bFIND\s+([\w-]+)',
                r'\bSTORE\s+([\w-]+)',
                r'\bMODIFY\s+([\w-]+)',
                r'\bERASE\s+([\w-]+)'
            ]
            for pattern in idms_patterns:
                idms_matches = re.finditer(pattern, clean_content, re.IGNORECASE)
                for match in idms_matches:
                    verb = re.match(r'\\b([A-Za-z]+)', pattern).group(1).upper()
                    record = match.group(1).upper()
                    area = match.group(2).upper() if len(match.groups()) > 1 and match.group(2) else None
                    para_data["idms"].append({
                        "verb": verb,
                        "record": record,
                        "area": area
                    })

            vsam_patterns = [
                r'\bREAD\s+([\w-]+)\b',
                r'\bWRITE\s+([\w-]+)\b',
                r'\bREWRITE\s+([\w-]+)\b',
                r'\bDELETE\s+([\w-]+)\b',
                r'\bSTART\s+([\w-]+)\b'
            ]
            for pattern in vsam_patterns:
                matches = re.finditer(pattern, clean_content, re.IGNORECASE)
                for match in matches:
                    verb = re.match(r'\\b([A-Za-z]+)', pattern).group(1).upper()
                    file_var = match.group(1).upper()
                    
                    para_data["vsam"].append({
                        "operation": verb,
                        "file_variable": file_var
                    })

            move_matches = re.finditer(r'\bMOVE\s+([\w-]+(?:\([\w\d:]+\))?)\s+TO\s+([\w\s-]+(?:\([\w\d:]+\))?)\b', clean_content, re.IGNORECASE)
            for match in move_matches:
                source = match.group(1).upper()
                dest_str = match.group(2).upper()
                destinations = [d.strip() for d in re.split(r'\s+', dest_str) if d.strip() and d.strip() != "TO"]
                for dest in destinations:
                    para_data["moves"].append({
                        "source": source,
                        "destination": dest
                    })
