import json
import urllib.request
import urllib.error
import re

class COBOLDocumentationGenerator:
    def __init__(self, metadata, ollama_url="http://localhost:11434", ollama_model="llama3:latest"):
        self.metadata = metadata
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model

    def _query_ollama(self, prompt, fallback_text):
        """
        Sends a query to local Ollama API and retrieves the response.
        Falls back to provided text if Ollama is unreachable or errors.
        """
        if not self.ollama_model or self.ollama_model.lower() in ("skip", "mock", "none", ""):
            print("  Skipping Ollama query (mock mode active). Using fallback narrative.")
            return fallback_text.strip()

        data = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False
        }
        url = f"{self.ollama_url.rstrip('/')}/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            print(f"Querying Ollama model '{self.ollama_model}' for documentation section...")
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data.get("response", fallback_text).strip()
        except Exception as e:
            print(f"  Ollama request failed or timed out: {e}. Using fallback narrative.")
            return fallback_text.strip()

    def generate_documentation(self):
        doc = []
        
        # Build document sections
        doc.append(self._gen_section_1())
        doc.append(self._gen_section_2())
        doc.append(self._gen_section_3())
        doc.append(self._gen_section_4())
        doc.append(self._gen_section_5())
        doc.append(self._gen_section_6())
        doc.append(self._gen_section_7())
        doc.append(self._gen_section_8())
        doc.append(self._gen_section_9())
        doc.append(self._gen_section_10())
        
        return "\n\n".join(doc)

    def _gen_section_1(self):
        prog_id = self.metadata["program_id"]
        author = self.metadata["author"]
        num_vars = len(self.metadata["variables"])
        num_paras = len(self.metadata["paragraphs"])
        
        prompt = (
            f"Write a technical software documentation introduction section for a mainframe COBOL program named '{prog_id}' written by '{author}'. "
            f"It has {num_vars} variables and {num_paras} paragraphs. It interacts with DB2 tables, IMS database, VSAM files, IBM MQ queues, and CICS screens.\n"
            f"Write exactly the following subsections:\n"
            f"1.1 Program Overview\n"
            f"1.2 Objectives\n"
            f"1.3 Scope\n"
            f"1.4 Assumptions and Constraints\n"
            f"Keep the tone professional and technical. Output only the markdown text of these subsections, starting directly with '1.1 Program Overview'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 1.1 Program Overview\n"
            f"The program `{prog_id}` is a mainframe COBOL batch/online program designed to perform core customer business processing. "
            f"It handles data ingestion, variable preparation, validation, and communicates with various backend services. "
            f"It was authored by {author}.\n\n"
            f"### 1.2 Objectives\n"
            f"The primary objectives of `{prog_id}` are:\n"
            f"- Retrieve customer profile information from DB2 databases and IMS databases.\n"
            f"- Validate transactions and perform formatting on sensitive customer fields.\n"
            f"- Log status messages and transfer buffers to external message queues via IBM MQ.\n"
            f"- Present processed details on user screens via CICS interfaces.\n\n"
            f"### 1.3 Scope\n"
            f"This program serves as a processing module within the Customer Management subsystem. "
            f"It manages VSAM database files, processes inbound linkage section parameters, and performs data staging.\n\n"
            f"### 1.4 Assumptions and Constraints\n"
            f"- **Assumptions**: DB2 tables and IMS databases are online and accessible. CICS transaction manager and MQ series queues are operational.\n"
            f"- **Constraints**: Fixed-length processing windows, strictly typed variable schemas defined in copybooks, and compliance with mainframe memory layouts."
        )
        
        narrative = self._query_ollama(prompt, fallback)
        
        return f"# 1. Introduction\n\n{narrative}"

    def _gen_section_2(self):
        db2_tables = sorted(list(set(db["table"] for p in self.metadata["paragraphs"].values() for db in p["db2"])))
        ims_segs = sorted(list(set(arg for p in self.metadata["paragraphs"].values() for ims in p["ims"] for arg in ims["arguments"])))
        idms_recs = sorted(list(set(idms["record"] for p in self.metadata["paragraphs"].values() for idms in p["idms"])))
        
        db2_str = "\n".join(f"- `{t}`" for t in db2_tables) if db2_tables else "- No DB2 tables referenced."
        ims_str = "\n".join(f"- Segment/IO Area: `{s}`" for s in ims_segs) if ims_segs else "- No IMS segments referenced."
        idms_str = "\n".join(f"- Record: `{r}`" for r in idms_recs) if idms_recs else "- No IDMS records referenced."
        
        return (
            f"# 2. Database Details\n\n"
            f"## 2.1 DB2 Tables\n"
            f"The program queries or updates the following database tables:\n"
            f"{db2_str}\n\n"
            f"## 2.2 IMS Segments\n"
            f"The program interfaces with IMS databases using the following segment search arguments (SSAs) or IO areas:\n"
            f"{ims_str}\n\n"
            f"## 2.3 IDMS Records\n"
            f"The program retrieves or modifies the following IDMS database records:\n"
            f"{idms_str}"
        )

    def _gen_section_3(self):
        prog_id = self.metadata["program_id"]
        
        db2_tables = sorted(list(set(db["table"] for p in self.metadata["paragraphs"].values() for db in p["db2"])))
        mq_calls = sorted(list(set(mq["call_type"] for p in self.metadata["paragraphs"].values() for mq in p["mq"])))
        cics_maps = sorted(list(set(cics["map"] for p in self.metadata["paragraphs"].values() for cics in p["cics"])))
        files = self.metadata["files"]
        ext_calls = sorted(list(set(ext["program"] for p in self.metadata["paragraphs"].values() for ext in p["external_calls"])))
        
        mermaid_comp = [
            f"```mermaid",
            f"graph TD",
            f"    subgraph Mainframe System",
            f"        PROG[{prog_id} Program]"
        ]
        
        comp_id = 1
        for table in db2_tables:
            mermaid_comp.append(f"        PROG -->|DB2 SQL| DB2_{comp_id}[({table} Table)]")
            comp_id += 1
            
        for file in files:
            mermaid_comp.append(f"        PROG -->|VSAM I/O| FILE_{comp_id}[[\"{file['variable']} ({file['dataset']})\"]]")
            comp_id += 1
            
        if mq_calls:
            mermaid_comp.append(f"        PROG -->|MQ Messaging| MQ[IBM MQ Queue Manager]")
            
        for cmap in cics_maps:
            if cmap:
                mermaid_comp.append(f"        PROG -->|CICS Map| CICS_{comp_id}[(\"Screen: {cmap}\")]")
                comp_id += 1
                
        for ext in ext_calls:
            mermaid_comp.append(f"        PROG -->|Subroutine Call| EXT_{comp_id}[[\"Program: {ext}\"]]")
            comp_id += 1
            
        mermaid_comp.append(f"    end")
        mermaid_comp.append(f"```")
        
        call_graph = self.metadata["analysis"]["call_graph"]
        unreachable = self.metadata["analysis"]["unreachable_paragraphs"]
        
        mermaid_flow = [
            f"```mermaid",
            f"graph TD"
        ]
        
        for para in self.metadata["paragraph_order"]:
            if para in unreachable:
                mermaid_flow.append(f"    {para}[\"{para} (Dead Code)\"]:::dead")
            else:
                mermaid_flow.append(f"    {para}[\"{para}\"]")
                
        for caller, callees in call_graph.items():
            for callee in callees:
                mermaid_flow.append(f"    {caller} --> {callee}")
                
        mermaid_flow.append(f"    classDef dead fill:#fbcfe8,stroke:#f43f5e,stroke-width:2px;")
        mermaid_flow.append(f"```")
        
        comp_diagram = "\n".join(mermaid_comp)
        flow_diagram = "\n".join(mermaid_flow)
        
        return (
            f"# 3. System Architecture\n\n"
            f"## 3.1 Component Diagram\n"
            f"The diagram below outlines the external interfaces and components interfacing with the `{prog_id}` program:\n\n"
            f"{comp_diagram}\n\n"
            f"## 3.2 Control Flow Diagram\n"
            f"The diagram below shows the control flow and call relationships between the internal paragraphs of the program:\n\n"
            f"{flow_diagram}"
        )

    def _gen_section_4(self):
        struct_table = [
            "| Paragraph / Section | Start Line | End Line | Section Group | Description |",
            "| --- | --- | --- | --- | --- |"
        ]
        for para_name in self.metadata["paragraph_order"]:
            p = self.metadata["paragraphs"][para_name]
            desc_parts = []
            if p["db2"]: desc_parts.append("Queries DB2")
            if p["ims"]: desc_parts.append("Calls IMS")
            if p["mq"]: desc_parts.append("Outputs to IBM MQ")
            if p["cics"]: desc_parts.append("Invokes CICS Maps")
            if p["vsam"]: desc_parts.append("Accesses VSAM files")
            if p["external_calls"]: desc_parts.append("Calls external modules")
            desc = ", ".join(desc_parts) if desc_parts else "Internal processing logic"
            
            struct_table.append(f"| `{para_name}` | {p['start_line']} | {p['end_line']} | {p['section']} | {desc} |")
        
        struct_str = "\n".join(struct_table)
        
        paragraphs_summary = []
        for name in self.metadata["paragraph_order"]:
            p = self.metadata["paragraphs"][name]
            paragraphs_summary.append(f"Paragraph {name} (Lines {p['start_line']}-{p['end_line']}): calls={list(c['target'] for c in p['calls'])}. Contains: {len(p['db2'])} DB2 calls, {len(p['ims'])} IMS calls, {len(p['mq'])} MQ calls, {len(p['cics'])} CICS calls, {len(p['vsam'])} VSAM calls.")
            
        summary_str = "\n".join(paragraphs_summary)
        
        prompt = (
            f"Based on the following paragraph structural details of the COBOL program '{self.metadata['program_id']}':\n"
            f"{summary_str}\n\n"
            f"Write exactly the following subsections:\n"
            f"4.2.1 Overall Program Logic\n"
            f"4.2.2 Key Algorithmic Details\n"
            f"Explain how the program initializes, processes files/databases, executes conditional loops, and handles shutdown. "
            f"Output only the markdown text of these subsections, starting directly with '4.2.1 Overall Program Logic'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 4.2.1 Overall Program Logic\n"
            f"The program follows a standard mainframe control logic: initialization, sequential data processing, and termination. "
            f"It first reads configuration arguments, initializes internal variables, opens VSAM files, and loops through customer records. "
            f"If queries succeed, it executes business logic and stages variables. If errors occur, it logs them and exits.\n\n"
            f"### 4.2.2 Key Algorithmic Details\n"
            f"- **Flow branching**: An `IF` evaluation on `SQL-CODE-VAL` decides if the program routes through PII processing (`D000-PROCESS-PII-DATA`), queue transmitting (`E000-LOG-TO-MQ`), and map transmission (`F000-SEND-CICS-MAP`), or immediately triggers error logging (`G000-HANDLE-ERROR`).\n"
            f"- **Taint Propagation**: It maps data from DB2/IMS records to layout records and pushes them through a formatted MQ buffer buffer sequentially."
        )
        
        narrative_alg = self._query_ollama(prompt, fallback)
        
        io_table = [
            "| Interface Channel | Technical Resource / DD Name | Description | Data Format | Direction |",
            "| --- | --- | --- | --- | --- |"
        ]
        for f in self.metadata["files"]:
            io_table.append(f"| VSAM File | `{f['dataset']}` | File variable `{f['variable']}` | Index Keyed Record | In/Out |")
        
        mq_present = False
        for name, p in self.metadata["paragraphs"].items():
            if p["mq"]:
                mq_present = True
                break
        if mq_present:
            io_table.append("| IBM MQ | `MQ Series Queue` | Buffer message transmission | MQ Descriptor Block | Output |")
            
        cics_present = False
        for name, p in self.metadata["paragraphs"].items():
            if p["cics"]:
                cics_present = True
                break
        if cics_present:
            io_table.append("| CICS Terminal | `CUSTMAP Screen` | Terminal user-interface map | Screen Layout Fields | Output |")

        if len(io_table) == 2:
            io_table.append("| None | N/A | No file/device interfaces detected | N/A | N/A |")
            
        io_str = "\n".join(io_table)
        
        db2_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for db in p["db2"]:
                db2_details.append(f"- **Paragraph `{p_name}`**: Executes `{db['command']}` on table `{db['table']}`. SQL Query:\n  ```sql\n  {db['raw_sql']}\n  ```")
        db2_details_str = "\n".join(db2_details) if db2_details else "No DB2 operations executed in procedure division."

        ims_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for ims in p["ims"]:
                ims_details.append(f"- **Paragraph `{p_name}`**: Invokes IMS command `{ims['function']}` using parameters: " + ", ".join(f"`{a}`" for a in ims["arguments"]))
        ims_details_str = "\n".join(ims_details) if ims_details else "No IMS operations executed in procedure division."

        idms_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for idms in p["idms"]:
                area_part = f" within Area `{idms['area']}`" if idms["area"] else ""
                idms_details.append(f"- **Paragraph `{p_name}`**: Executes IDMS `{idms['verb']}` on record `{idms['record']}`{area_part}")
        idms_details_str = "\n".join(idms_details) if idms_details else "No IDMS operations executed in procedure division."

        copybooks_referenced = sorted(list(set(v["source_copybook"] for v in self.metadata["variables"] if v["source_copybook"])))
        ext_calls = []
        for p_name, p in self.metadata["paragraphs"].items():
            for ext in p["external_calls"]:
                ext_calls.append(f"- **Paragraph `{p_name}`**: Calls program `{ext['program']}` passing arguments: " + ", ".join(f"`{a}`" for a in ext["arguments"]))
        
        called_details = []
        if copybooks_referenced:
            called_details.append("**Included Copybooks:**")
            for cp in copybooks_referenced:
                called_details.append(f"- `{cp}`: Pulled into DATA DIVISION structures.")
        if ext_calls:
            called_details.append("\n**External Calls:**")
            called_details.extend(ext_calls)
        called_details_str = "\n".join(called_details) if called_details else "No copybooks or external subprograms referenced."

        vsam_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for vsam in p["vsam"]:
                dataset = next((f["dataset"] for f in self.metadata["files"] if f["variable"] == vsam["file_variable"]), "UNKNOWN")
                vsam_details.append(f"- **Paragraph `{p_name}`**: Performs `{vsam['operation']}` on file variable `{vsam['file_variable']}` (Dataset/DD: `{dataset}`)")
        vsam_details_str = "\n".join(vsam_details) if vsam_details else "No VSAM operations executed in procedure division."

        mq_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for mq in p["mq"]:
                mq_details.append(f"- **Paragraph `{p_name}`**: Executes IBM MQ function `{mq['call_type']}` with argument trace: " + ", ".join(f"`{a}`" for a in mq["arguments"]))
        mq_details_str = "\n".join(mq_details) if mq_details else "No IBM MQ operations executed in procedure division."

        cics_details = []
        for p_name, p in self.metadata["paragraphs"].items():
            for cics in p["cics"]:
                cics_details.append(f"- **Paragraph `{p_name}`**: Runs `{cics['verb']}` on map `{cics['map']}` (Mapset: `{cics['mapset']}`). CICS details: `{cics['raw_cics']}`")
        cics_details_str = "\n".join(cics_details) if cics_details else "No CICS operations executed in procedure division."

        err_handlers = []
        for p_name, p in self.metadata["paragraphs"].items():
            if "ERR" in p_name or "ERROR" in p_name:
                err_handlers.append(f"- **Error Paragraph `{p_name}`**: Handles faults by logging or displaying errors. Code snippet:\n  ```cobol\n  {p['content']}\n  ```")
        err_handlers_str = "\n".join(err_handlers) if err_handlers else "No dedicated error-handling paragraphs identified. General conditional checks used."

        return (
            f"# 4. Detailed Design\n\n"
            f"## 4.1 Program Structure\n"
            f"The following table details all sections and paragraphs defined in the program:\n\n"
            f"{struct_str}\n\n"
            f"## 4.2 Algorithms\n"
            f"{narrative_alg}\n\n"
            f"## 4.3 Input/Output Specifications\n"
            f"The primary files and UI interfaces are defined below:\n\n"
            f"{io_str}\n\n"
            f"## 4.4 DB2 Database Details\n"
            f"{db2_details_str}\n\n"
            f"## 4.5 IMS Database Details\n"
            f"{ims_details_str}\n\n"
            f"## 4.6 IDMS Database Details\n"
            f"{idms_details_str}\n\n"
            f"## 4.7 Called Sub-routine/Program Details/Copybook\n"
            f"{called_details_str}\n\n"
            f"## 4.8 VSAM File Details\n"
            f"{vsam_details_str}\n\n"
            f"## 4.9 IBM MQ Details\n"
            f"{mq_details_str}\n\n"
            f"## 4.10 CICS Details\n"
            f"{cics_details_str}\n\n"
            f"## 4.11 Error Handling\n"
            f"{err_handlers_str}"
        )

    def _gen_section_5(self):
        db2_tables = sorted(list(set(db["table"] for p in self.metadata["paragraphs"].values() for db in p["db2"])))
        files = self.metadata["files"]
        cics_maps = sorted(list(set(cics["map"] for p in self.metadata["paragraphs"].values() for cics in p["cics"])))
        
        prompt = (
            f"Based on the following external references of the COBOL program:\n"
            f"- DB2 Tables: {db2_tables}\n"
            f"- VSAM Files: {files}\n"
            f"- CICS Screen Maps: {cics_maps}\n\n"
            f"Write exactly the following subsections:\n"
            f"5.1 External Interfaces\n"
            f"5.2 User Interface\n"
            f"Explain how these components interface with other systems, protocols, and the CICS user screen. "
            f"Output only the markdown text of these subsections, starting directly with '5.1 External Interfaces'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 5.1 External Interfaces\n"
            f"The program exposes external interfaces through data transfer protocols and database links:\n"
            f"- **DB2 Database Link**: Communicates using embedded SQL over the mainframe SQL engine.\n"
            f"- **VSAM File Access**: Interfaces with datasets on disk through the operating system's Virtual Storage Access Method.\n"
            f"- **IBM MQ Queue Manager**: Exchanges messages asynchronously with downstream applications.\n\n"
            f"### 5.2 User Interface\n"
            f"The user interface is a CICS character-mode screen designed using CUSTMAP. "
            f"It displays formatted customer fields, allows basic input parameters, and outputs system alerts on completion."
        )
        
        narrative = self._query_ollama(prompt, fallback)
        return f"# 5. Interface Design\n\n{narrative}"

    def _gen_section_6(self):
        prompt = (
            f"Write a testing strategy for a mainframe COBOL program named '{self.metadata['program_id']}'. "
            f"The program uses DB2 SQL, IMS databases, VSAM files, MQ queues, and CICS MAP interfaces.\n"
            f"Write exactly the following subsections:\n"
            f"6.1 Test Plan\n"
            f"6.2 Testing Environment\n"
            f"Describe how to perform unit testing, database stubbing/mocking, online CICS transaction testing, and list required tools. "
            f"Output only the markdown text of these subsections, starting directly with '6.1 Test Plan'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 6.1 Test Plan\n"
            f"To verify correct behavior, the test plan includes:\n"
            f"1. **Unit Testing**: Stub out external database queries. Verify that paragraphs are performed in the correct sequence.\n"
            f"2. **DB2 Integration Testing**: Verify database query syntax and error codes (such as SQLCODE = -811, 0, or 100).\n"
            f"3. **VSAM File Verification**: Validate VSAM file read operations and handling of 'record not found' exceptions.\n"
            f"4. **CICS Screen Verification**: Test terminal displays through CICS transaction simulators.\n\n"
            f"### 6.2 Testing Environment\n"
            f"The test environment requires standard IBM z/OS development environments. This includes:\n"
            f"- IBM Developer for z/OS (IDz) or similar IDE.\n"
            f"- IBM MQ simulator or test queue managers.\n"
            f"- CICS testing region equipped with the compiled map set (`CUSTSET`).\n"
            f"- DB2 test tables mirroring production schemas with masked/synthesized test data."
        )
        
        narrative = self._query_ollama(prompt, fallback)
        return f"# 6. Testing Strategy\n\n{narrative}"

    def _gen_section_7(self):
        prompt = (
            f"Write a performance considerations assessment for a mainframe COBOL program named '{self.metadata['program_id']}'. "
            f"It performs DB2 SQL SELECT statements, IMS database reads, and VSAM index file reads.\n"
            f"Write exactly the following subsections:\n"
            f"7.1 Performance Analysis\n"
            f"7.2 Optimization Recommendations\n"
            f"Explain latency, CPU utilization (MIPS), database indexing, buffer sizes, and optimal host variable patterns. "
            f"Output only the markdown text of these subsections, starting directly with '7.1 Performance Analysis'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 7.1 Performance Analysis\n"
            f"The program's performance is dominated by external input/output operations:\n"
            f"- **DB2 Access**: SQL query execution uses CPU MIPS. Lack of indexes can trigger table scans.\n"
            f"- **IMS & VSAM Reads**: Accessing files/segments causes disk I/O wait states.\n"
            f"- **MQ Messaging**: Network/queue synchronization calls introduce thread-blocking latencies.\n\n"
            f"### 7.2 Optimization Recommendations\n"
            f"- Ensure the `DB2_CUST_TABLE` has a primary index on `CUST_ID` to avoid costly full table scans.\n"
            f"- Optimize VSAM buffer sizes (BUFND/BUFNI) in JCL definitions to cache file index nodes.\n"
            f"- Replace repetitive queries with bulk SELECT cursors where feasible.\n"
            f"- Ensure MQ calls are performed asynchronously (`MQPMO-NO-SYNCPOINT`) if transactional guarantees are not required."
        )
        
        narrative = self._query_ollama(prompt, fallback)
        return f"# 7. Performance Considerations\n\n{narrative}"

    def _gen_section_8(self):
        unreachable = self.metadata["analysis"]["unreachable_paragraphs"]
        if unreachable:
            unreachable_str = "\n".join(f"- `{para}`" for para in unreachable)
            analysis = (
                f"The control flow reachability analysis has identified **{len(unreachable)}** unreachable paragraphs:\n\n"
                f"{unreachable_str}\n\n"
                f"**Risk/Impact:** These paragraphs represent dead code. Having dead code increases maintenance overhead, "
                f"confuses developer comprehension, and can indicate orphaned logical blocks or legacy routines that are no longer in use. "
                f"It is recommended to safely comment out or delete these blocks after verifying no dynamic/computed performance routes (e.g. dynamic CALLs) target them."
            )
        else:
            analysis = "No dead code or unreachable paragraphs were identified. All paragraphs are reachable from the main program entry point."
            
        return (
            f"# 8. Dead Code Analysis\n\n"
            f"{analysis}"
        )

    def _gen_section_9(self):
        pii_vars = self.metadata["analysis"]["pii_variables"]
        pii_flows = self.metadata["analysis"]["pii_flows"]
        egress = self.metadata["analysis"]["pii_egress_points"]
        
        vars_table = [
            "| Variable Name | Level | PIC Clause | PII Classification Reason |",
            "| --- | --- | --- | --- |"
        ]
        
        for name, reason in pii_vars.items():
            v_meta = next((v for v in self.metadata["variables"] if v["name"] == name), None)
            level = v_meta["level"] if v_meta else "N/A"
            pic = v_meta["pic"] if v_meta and v_meta["pic"] else "N/A"
            vars_table.append(f"| `{name}` | {level} | `{pic}` | {reason} |")
            
        vars_str = "\n".join(vars_table) if len(vars_table) > 2 else "| None | N/A | N/A | No PII variables identified |"
        
        flows_table = [
            "| Step | Source Variable | Destination Variable | Code Location (Paragraph) | Instruction Statement |",
            "| --- | --- | --- | --- | --- |"
        ]
        for idx, step in enumerate(pii_flows):
            flows_table.append(f"| {idx+1} | `{step['source']}` | `{step['destination']}` | `{step['paragraph']}` | `{step['statement']}` |")
            
        flows_str = "\n".join(flows_table) if len(flows_table) > 2 else "| N/A | None | None | N/A | No PII flows observed |"
        
        egress_summary = []
        for idx, eg in enumerate(egress):
            egress_summary.append(f"Egress {idx+1}: Var {eg['variable']} output to {eg['type']} ({eg['destination']}) in paragraph {eg['paragraph']}. Detail: {eg['details']}.")
        egress_summary_str = "\n".join(egress_summary) if egress_summary else "No external PII egress points detected."

        prompt = (
            f"Based on the following security details of the program '{self.metadata['program_id']}':\n"
            f"Tainted PII Variables: {list(pii_vars.keys())}\n"
            f"Egress Points:\n{egress_summary_str}\n\n"
            f"Write a security analysis report section detailing:\n"
            f"9.1.3 PII Security Analysis\n"
            f"Discuss encryption, data masking, logs exposure (e.g. logging SSN to terminal or files), and MQ transmission risks. Suggest standard mainframe security practices like RACF or cryptography. "
            f"Output only the markdown text of this section, starting directly with '9.1.3 PII Security Analysis'. Do not include wrapping comments or markdown block wrappers."
        )
        
        fallback = (
            f"### 9.1.3 PII Security Analysis\n"
            f"The analysis revealed critical exposures regarding Personally Identifiable Information (PII):\n"
            f"- **Unencrypted Transmission**: PII data elements like `CUST-ACCOUNT-NUM` are copied to the MQ buffer and sent over queues without field-level encryption.\n"
            f"- **Log Exposure Risk**: Staging PII records in general logging blocks (e.g. `WS-PII-LOG-SSN` or displays) can leak sensitive data into system spools (SDSF) where unauthorized users can view them.\n"
            f"- **Mitigation Recommendations**: Use IBM InfoSphere Guardium or DFSMS/RACF file encryption. Mask fields (e.g. XXX-XX-1234) before writing to message buffers or system logs."
        )
        
        narrative_sec = self._query_ollama(prompt, fallback)
        
        inventory_table = [
            "| Egress Channel | Data Element | Risk Level | Mitigation Strategy |",
            "| --- | --- | --- | --- |"
        ]
        for eg in egress:
            risk = "HIGH" if eg["type"] in ["IBM MQ", "External Call"] else "MEDIUM"
            mitigation = "Encrypt before transmission" if risk == "HIGH" else "Apply field masking"
            inventory_table.append(f"| {eg['type']} ({eg['destination']}) | `{eg['variable']}` | **{risk}** | {mitigation} |")
            
        inventory_str = "\n".join(inventory_table) if len(inventory_table) > 2 else "| N/A | None | Low | No PII transmission detected |"

        return (
            f"# 9. Security Risk Assessment\n\n"
            f"## 9.1 PII (Personally Identifiable Information) Analysis\n\n"
            f"### 9.1.1 PII Data Elements Identification\n"
            f"The following variables contain or handle PII based on name pattern rules:\n\n"
            f"{vars_str}\n\n"
            f"### 9.1.2 PII Data Flow Analysis\n"
            f"Static taint tracking shows the propagation of PII data across variable reassignments:\n\n"
            f"{flows_str}\n\n"
            f"{narrative_sec}\n\n"
            f"### 9.1.4 PII Inventory Summary\n"
            f"A summary of PII egress points and risk classifications:\n\n"
            f"{inventory_str}"
        )

    def _gen_section_10(self):
        glossary = (
            "| Term | Definition |\n"
            "| --- | --- |\n"
            "| **Copybook** | A reusable source file that contains data structures or declarations in COBOL. |\n"
            "| **DB2** | IBM's relational database management system for z/OS mainframe environments. |\n"
            "| **IMS** | Information Management System, a database and transaction management system. |\n"
            "| **VSAM** | Virtual Storage Access Method, a high-performance file management system on IBM mainframes. |\n"
            "| **IBM MQ** | Message queue middleware facilitating secure, asynchronous system-to-system communications. |\n"
            "| **CICS** | Customer Information Control System, an online transaction manager for mainframe systems. |\n"
            "| **PII** | Personally Identifiable Information; sensitive data elements that can identify individuals. |\n"
            "| **Dead Code** | Program blocks or paragraphs that cannot be reached or executed under any conditions. |"
        )
        
        struct_lines = []
        for cp in sorted(list(set(v["source_copybook"] for v in self.metadata["variables"] if v["source_copybook"]))):
            struct_lines.append(f"#### Copybook `{cp}` Layout")
            struct_lines.append("```cobol")
            for v in self.metadata["variables"]:
                if v["source_copybook"] == cp:
                    pic_part = f" PIC {v['pic']}" if v["pic"] else ""
                    val_part = f" VALUE '{v['value']}'" if v["value"] else ""
                    struct_lines.append(f"  {v['level']:02d}  {v['name']}{pic_part}{val_part}.")
            struct_lines.append("```")
            
        structs_str = "\n".join(struct_lines) if struct_lines else "No complex layouts or copybooks imported."

        references = (
            "- IBM Enterprise COBOL for z/OS Language Reference\n"
            "- DB2 SQL Reference Guide\n"
            "- CICS Application Programming Guide\n"
            "- IBM MQ Application Programming Reference"
        )

        return (
            f"# 10. Appendices\n\n"
            f"## 10.1 Glossary\n\n"
            f"{glossary}\n\n"
            f"## 10.2 Data Structures\n\n"
            f"{structs_str}\n\n"
            f"## 10.3 References\n\n"
            f"{references}"
        )
