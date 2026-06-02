import json
import urllib.request
import urllib.error
import urllib.parse
import re
import os

class JCLDocumentationGenerator:
    def __init__(self, metadata, ollama_url="http://localhost:11434", ollama_model="skip", output_dir=None):
        self.metadata = metadata
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.output_dir = output_dir or os.getcwd()

    def _render_mermaid_to_image(self, mermaid_code, filename):
        code_lines = []
        for line in mermaid_code.split('\n'):
            if not line.strip().startswith('```') and not line.strip().startswith('%%'):
                code_lines.append(line)
        cleaned_code = '\n'.join(code_lines).strip()
        
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                url = "https://kroki.io/mermaid/png"
                print(f"[*] Requesting static diagram render from Kroki.io API: {filename} (attempt {attempt + 1})")
                
                req = urllib.request.Request(
                    url,
                    data=cleaned_code.encode("utf-8"),
                    headers={'Content-Type': 'text/plain', 'User-Agent': 'Mozilla/5.0'}
                )
                
                os.makedirs(self.output_dir, exist_ok=True)
                output_path = os.path.join(self.output_dir, filename)
                
                with urllib.request.urlopen(req, timeout=8) as response:
                    with open(output_path, "wb") as f:
                        f.write(response.read())
                print(f"[+] Diagram saved to local path: {output_path}")
                return output_path
            except Exception as e:
                print(f"Warning: Failed to render Mermaid diagram to image '{filename}' via Kroki (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        return None

    def _query_ollama(self, prompt, fallback_text):
        if not self.ollama_model or self.ollama_model.lower() in ("skip", "mock", "none", ""):
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
            print(f"Querying Ollama model '{self.ollama_model}' for JCL modernization section...")
            with urllib.request.urlopen(req, timeout=120) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data.get("response", fallback_text).strip()
        except Exception as e:
            print(f"  Ollama request failed or timed out: {e}. Using fallback narrative.")
            return fallback_text.strip()

    def generate_documentation(self):
        doc = []
        doc.append(self._gen_section_1())
        doc.append(self._gen_section_2())
        doc.append(self._gen_section_3())
        doc.append(self._gen_section_4())
        doc.append(self._gen_section_5())
        return "\n\n".join(doc)

    def _gen_section_1(self):
        job_name = self.metadata["job_name"]
        file_name = self.metadata["file_name"]
        num_steps = len(self.metadata["steps"])
        
        prompt = (
            f"Write a professional executive overview for a mainframe JCL batch job named '{job_name}' (Source: '{file_name}'). "
            f"It runs {num_steps} distinct steps. The report should focus on modernization and cloud migration readiness.\n"
            f"Write exactly the following subsections:\n"
            f"1.1 Batch Job Overview\n"
            f"1.2 Modernization Objectives\n"
            f"1.3 Assumptions & Migration Scope\n"
            f"Output only the markdown text of these subsections, starting directly with '1.1 Batch Job Overview'."
        )
        
        fallback = (
            f"### 1.1 Batch Job Overview\n"
            f"The batch execution sequence `{job_name}` (loaded from source file `{file_name}`) orchestrates mainframe batch workflows "
            f"comprising {num_steps} steps. It handles file preparation, program executions, database cursor refreshes, and resource routing.\n\n"
            f"### 1.2 Modernization Objectives\n"
            f"The primary migration goals include:\n"
            f"- Decoupling step dependency chains into cloud-native scheduled workflows (e.g. Apache Airflow DAGs).\n"
            f"- Replacing manual JCL dataset allocations with automated cloud storage operations.\n"
            f"- Isolating custom programs from utility steps to translate and migrate them to modern application stacks.\n\n"
            f"### 1.3 Assumptions & Migration Scope\n"
            f"- **Assumptions**: Physical files reference cataloged storage partitions. Target environment runs comparable Python or Bash container executors.\n"
            f"- **Scope**: Includes step execution triggers, DD data mappings, utility steps replacements, and DAG orchestration structure mappings."
        )
        
        narrative = self._query_ollama(prompt, fallback)
        return f"# 1. JCL Modernization Executive Summary\n\n{narrative}"

    def _gen_section_2(self):
        job_name = self.metadata["job_name"]
        utilities = ["DFSORT", "SORT", "IEBGENER", "IEFBR14", "IDCAMS", "IKJEFT01", "ADRDSSU", "IEBCOPY", "ICEGENER", "AMBXSDR", "BPXBATCH", "DSNUTILB"]
        
        table_lines = [
            "| Step Order | Step Label | Executed Program | Classification | Modernization Target / Rule |",
            "| --- | --- | --- | --- | --- |"
        ]
        
        for idx, s in enumerate(self.metadata["steps"]):
            step_lbl = s["step_name"]
            pgm = s["program"]
            is_util = pgm in utilities
            
            if is_util:
                classification = "Mainframe System Utility"
                if pgm in ["SORT", "DFSORT"]:
                    target = "Replace with Spark/SQL Sorting or Python Pandas script"
                elif pgm == "IEFBR14":
                    target = "Remove step (dataset allocations handled natively by target orchestrator)"
                elif pgm == "IDCAMS":
                    target = "Replace with storage CLI or bucket lifecycle management tools"
                else:
                    target = "Replace with native shell command or Cloud storage utility"
            else:
                classification = "Custom Business Program"
                target = "Migrate source logic (e.g., translate COBOL/Assembler binary to Java/Python)"
                
            table_lines.append(f"| {idx+1} | `{step_lbl}` | `{pgm}` | **{classification}** | {target} |")
            
        table_str = "\n".join(table_lines)

        dep_lines = []
        dep_lines.append("## 2.3 Library & Included Module Dependencies")
        dep_lines.append("The JCL batch stream defines search paths, load libraries, and include member structures as follows:")
        
        jcllibs = self.metadata.get("jcllibs", [])
        steplibs = self.metadata.get("steplibs", [])
        includes = self.metadata.get("includes", [])
        
        if jcllibs:
            dep_lines.append("\n### JCLLIB Library Search Paths")
            for j in jcllibs:
                dep_lines.append(f"- Search Directory: `{j}`")
        else:
            dep_lines.append("\n- No external JCLLIB library searches declared.")
            
        if steplibs:
            dep_lines.append("\n### JOBLIB and STEPLIB Load Libraries")
            for s in sorted(list(set(steplibs))):
                dep_lines.append(f"- Partitioned Load Library: `{s}` (contains executed program binaries)")
        else:
            dep_lines.append("\n- No specific step STEPLIB load libraries defined.")
            
        if includes:
            dep_lines.append("\n### JCL INCLUDE Members")
            for inc in includes:
                dep_lines.append(f"- Include Member: `{inc}` (reusable parameter/step layouts included at runtime)")
        else:
            dep_lines.append("\n- No include blocks or JCL member structures referenced.")
            
        dep_str = "\n".join(dep_lines)

        return (
            f"# 2. Step Execution Sequence & Classification\n\n"
            f"## 2.1 Step Execution Sequence\n"
            f"The following table inventories and categorizes the execution steps of the `{job_name}` job, providing clear target modernization recommendations:\n\n"
            f"{table_str}\n\n"
            f"{dep_str}"
        )

    def _gen_section_3(self):
        job_name = self.metadata["job_name"]
        
        table_lines = [
            "| Step Label | DD Name | Dataset DSN | Access Pattern | Allocation / Disposition |",
            "| --- | --- | --- | --- | --- |"
        ]
        
        for s in self.metadata["steps"]:
            step_lbl = s["step_name"]
            for dd in s["dds"]:
                dd_name = dd["dd_name"]
                dsn = dd["dsn"]
                disp = dd["disp"]
                
                # Assess access pattern based on DD name and disposition
                if dsn == "SYSOUT" or dd_name in ["SYSPRINT", "SYSUDUMP", "SYSOUT"]:
                    access = "System Print Log"
                elif "NEW" in disp:
                    access = "Write (Output Store)"
                else:
                    access = "Read (Input Store)"
                    
                table_lines.append(f"| `{step_lbl}` | `{dd_name}` | `{dsn}` | {access} | `{disp}` |")
                
        table_str = "\n".join(table_lines) if len(table_lines) > 2 else "| N/A | N/A | No files or datasets parsed | N/A | N/A |"
        return (
            f"# 3. Data & Resource Bindings\n\n"
            f"The physical files and datasets accessed by `{job_name}` steps are detailed below:\n\n"
            f"{table_str}"
        )

    def _gen_section_4(self):
        job_name = self.metadata["job_name"]
        utilities = ["DFSORT", "SORT", "IEBGENER", "IEFBR14", "IDCAMS", "IKJEFT01", "ADRDSSU", "IEBCOPY", "ICEGENER", "AMBXSDR", "BPXBATCH", "DSNUTILB"]
        
        mermaid_lines = [
            "```mermaid",
            "graph TD",
            "    %% Styles",
            "    classDef custom fill:#dcfce7,stroke:#16a34a,stroke-width:2px;",
            "    classDef utility fill:#e0f2fe,stroke:#0284c7,stroke-width:2px;",
            "    classDef file fill:#fef9c3,stroke:#ca8a04,stroke-width:1px;",
            ""
        ]
        
        # Render steps
        step_nodes = []
        for s in self.metadata["steps"]:
            step_name = s["step_name"]
            pgm = s["program"]
            is_util = pgm in utilities
            style = ":::utility" if is_util else ":::custom"
            type_lbl = "Utility" if is_util else "Custom"
            mermaid_lines.append(f"    {step_name}[\"Step: {step_name} ({pgm} - {type_lbl})\"]{style}")
            step_nodes.append(step_name)
            
        mermaid_lines.append("")
        # Connect steps sequentially
        for i in range(len(step_nodes) - 1):
            mermaid_lines.append(f"    {step_nodes[i]} --> {step_nodes[i+1]}")
            
        mermaid_lines.append("")
        # Render and link unique datasets
        dsn_idx = 1
        rendered_dsns = {}
        for s in self.metadata["steps"]:
            step_name = s["step_name"]
            for dd in s["dds"]:
                dsn = dd["dsn"]
                dd_name = dd["dd_name"]
                if dsn == "SYSOUT" or dsn.startswith("&&") or dd_name in ["SYSPRINT", "SYSUDUMP", "SYSOUT"]:
                    continue
                    
                if dsn not in rendered_dsns:
                    node_id = f"DSN_{dsn_idx}"
                    rendered_dsns[dsn] = node_id
                    # Truncate DSN for graph display if too long
                    display_dsn = dsn[-30:] if len(dsn) > 30 else dsn
                    mermaid_lines.append(f"    {node_id}[[\"DSN: {display_dsn}\"]]:::file")
                    dsn_idx += 1
                else:
                    node_id = rendered_dsns[dsn]
                    
                disp = dd["disp"].upper()
                if "NEW" in disp or "MOD" in disp:
                    mermaid_lines.append(f"    {step_name} -->|writes {dd_name}| {node_id}")
                else:
                    mermaid_lines.append(f"    {node_id} -->|reads {dd_name}| {step_name}")
                    
        mermaid_lines.append("```")
        mermaid_code = "\n".join(mermaid_lines)
        
        # Render static diagram to PNG
        img_path = self._render_mermaid_to_image(mermaid_code, "jcl_execution_flow.png")
        if img_path:
            abs_path = os.path.abspath(img_path).replace("\\", "/")
            flow_display = f"![JCL Execution Flow](file:///{abs_path})"
        else:
            flow_display = mermaid_code
            
        # Build 4.2 Step Structure & Parameters Table
        table_lines = [
            "| Step Label | Executed Program | Classification | Step-Level COND | DD Configurations |",
            "| --- | --- | --- | --- | --- |"
        ]
        for s in self.metadata["steps"]:
            step_lbl = s["step_name"]
            pgm = s["program"]
            is_util = pgm in utilities
            classification = "System Utility" if is_util else "Custom Program"
            step_cond = s.get("cond") or "None"
            
            dd_infos = []
            for dd in s["dds"]:
                dd_infos.append(f"`{dd['dd_name']}` -> `{dd['dsn']}` ({dd['disp']})")
            dd_str = "<br>".join(dd_infos) if dd_infos else "None"
            
            table_lines.append(f"| `{step_lbl}` | `{pgm}` | {classification} | `{step_cond}` | {dd_str} |")
        table_str = "\n".join(table_lines)

        # Build 4.3 Logic and Control Flow Description
        job_cond = self.metadata.get("job_cond") or "None"
        conditionals = self.metadata.get("conditionals", [])
        
        cond_lines = []
        cond_lines.append(f"- **Job-Level Conditional Check**: `{job_cond}`")
        if job_cond != "None":
            cond_lines.append(f"  - *Behavior*: If the job-level condition is met, subsequent execution steps are bypassed.")
            
        step_conds_found = False
        cond_lines.append("\n- **Step-Level Condition Checks**:")
        for s in self.metadata["steps"]:
            if s.get("cond"):
                cond_lines.append(f"  - Step `{s['step_name']}` executes only if condition `{s['cond']}` is NOT met.")
                step_conds_found = True
        if not step_conds_found:
            cond_lines.append("  - No step-level `COND` parameters defined.")
            
        cond_lines.append("\n- **Logical Block Control Structure**:")
        if conditionals:
            for cond in conditionals:
                cond_lines.append(f"  - `{cond}`")
            cond_lines.append("  - *Analysis*: These statements represent dynamic branching logic. During modernization, these blocks should be translated to Airflow conditional task groups (e.g., using `@task.branch` or `BranchPythonOperator`).")
        else:
            cond_lines.append("  - No structured `IF-THEN-ELSE` or `ENDIF` blocks parsed.")
        logic_str = "\n".join(cond_lines)

        prompt = (
            f"Write a comprehensive structure and execution logic guide for the mainframe JCL batch job '{job_name}' being modernized to the cloud.\n"
            f"Focus on explaining how the job and step level condition codes, as well as the JCL IF/THEN/ELSE control blocks, influence execution, and how to implement this control flow in Apache Airflow or AWS Step Functions.\n"
            f"Write exactly the following subsections:\n"
            f"4.2 JCL Step Structure & Parameters\n"
            f"4.3 Execution Logic and Control Flow\n\n"
            f"Metadata to reference:\n"
            f"- Job-level condition check: {job_cond}\n"
            f"- Step-level configurations: {json.dumps(self.metadata['steps'], indent=2)}\n"
            f"- Parsing-derived control flow blocks: {json.dumps(self.metadata['conditionals'], indent=2)}\n\n"
            f"Output only the markdown text of these subsections, starting directly with '### 4.2 JCL Step Structure & Parameters'."
        )
        
        fallback_narrative = (
            f"### 4.2 JCL Step Structure & Parameters\n"
            f"The table below details the execution target, type classification, step-level conditions, and dataset resource mapping for each step:\n\n"
            f"{table_str}\n\n"
            f"### 4.3 Execution Logic and Control Flow\n"
            f"Modernizing mainframe job control logic requires translating traditional return/condition code checking to cloud orchestration logic:\n\n"
            f"{logic_str}"
        )
        
        narrative = self._query_ollama(prompt, fallback_narrative)

        return (
            f"# 4. Program Structure & Execution Logic\n\n"
            f"## 4.1 JCL Flow Sequence Diagram\n"
            f"The diagram below outlines the sequential flow of execution steps and their corresponding dataset interactions:\n\n"
            f"{flow_display}\n\n"
            f"{narrative}"
        )


    def _gen_section_5(self):
        job_name = self.metadata["job_name"]
        
        # Generate tasks list for DAG
        task_nodes = []
        for s in self.metadata["steps"]:
            step_name = s["step_name"]
            pgm = s["program"]
            task_nodes.append(f"    {step_name.lower()} = BashOperator(\n        task_id='{step_name.lower()}',\n        bash_command='python run_program.py --program {pgm}',\n        dag=dag,\n    )")
            
        dag_connections = []
        for i in range(len(self.metadata["steps"]) - 1):
            curr_step = self.metadata["steps"][i]["step_name"].lower()
            next_step = self.metadata["steps"][i+1]["step_name"].lower()
            dag_connections.append(f"    {curr_step} >> {next_step}")
            
        tasks_str = "\n\n".join(task_nodes)
        connections_str = "\n".join(dag_connections)
        
        fallback_blueprint = (
            f"```python\n"
            f"from airflow import DAG\n"
            f"from airflow.operators.bash import BashOperator\n"
            f"from datetime import datetime, timedelta\n\n"
            f"default_args = {{\n"
            f"    'owner': 'migration_team',\n"
            f"    'start_date': datetime(2026, 1, 1),\n"
            f"    'retries': 1,\n"
            f"    'retry_delay': timedelta(minutes=5),\n"
            f"}}\n\n"
            f"with DAG(\n"
            f"    dag_id='{job_name.lower()}_migration_dag',\n"
            f"    default_args=default_args,\n"
            f"    schedule_interval=None,\n"
            f"    catchup=False,\n"
            f"    description='Migrated orchestrations for JCL {job_name}',\n"
            f") as dag:\n\n"
            f"{tasks_str}\n\n"
            f"    # Dependencies\n"
            f"{connections_str}\n"
            f"```"
        )
        
        prompt = (
            f"Write a migration plan guide for a mainframe JCL batch job '{job_name}' being modernized to AWS Cloud and Apache Airflow.\n"
            f"Include advice on converting VSAM catalogued datasets to cloud storage buckets (S3/Blob). "
            f"Output exactly the following subsections:\n"
            f"5.1 Target Orchestrator Mapping (Apache Airflow DAG)\n"
            f"5.2 Cloud Storage and Target Data Schema mapping\n"
            f"In 5.1, provide the Python Airflow DAG code block representing the steps sequence: {list(s['step_name'] for s in self.metadata['steps'])}.\n"
            f"Output only the markdown text of these subsections, starting directly with '5.1 Target Orchestrator Mapping (Apache Airflow DAG)'."
        )
        
        blueprint = self._query_ollama(prompt, fallback_blueprint)
        
        return (
            f"# 5. Modern Cloud Migration Blueprint\n\n"
            f"{blueprint}"
        )
