import re

class COBOLAnalyzer:
    def __init__(self, metadata):
        self.metadata = metadata
        self.call_graph = {}       # caller -> list of callees
        self.reachable = set()
        self.unreachable = set()
        self.pii_vars = set()      # set of variables that are PII
        self.pii_origins = {}      # var -> origin reason
        self.pii_flows = []        # list of flow steps
        self.egress_points = []    # list of egress points

    def analyze(self):
        """
        Executes all analysis tasks: call graph, dead code, PII flows, and egresses.
        """
        self._build_call_graph()
        self._analyze_reachability()
        self._analyze_pii_flows()
        self._analyze_egress_points()
        
        analysis_results = {
            "call_graph": self.call_graph,
            "unreachable_paragraphs": list(self.unreachable),
            "pii_variables": {var: self.pii_origins[var] for var in self.pii_vars},
            "pii_flows": self.pii_flows,
            "pii_egress_points": self.egress_points
        }
        
        self.metadata["analysis"] = analysis_results
        return self.metadata

    def _build_call_graph(self):
        paragraphs = self.metadata["paragraphs"]
        order = self.metadata["paragraph_order"]
        
        for para_name in order:
            self.call_graph[para_name] = []
            para_data = paragraphs[para_name]
            
            for call in para_data["calls"]:
                target = call["target"]
                thru = call["thru"]
                
                if thru:
                    if target in order and thru in order:
                        idx_start = order.index(target)
                        idx_end = order.index(thru)
                        if idx_start <= idx_end:
                            for i in range(idx_start, idx_end + 1):
                                p_to_add = order[i]
                                if p_to_add not in self.call_graph[para_name]:
                                    self.call_graph[para_name].append(p_to_add)
                else:
                    if target in order:
                        if target not in self.call_graph[para_name]:
                            self.call_graph[para_name].append(target)

    def _analyze_reachability(self):
        order = self.metadata["paragraph_order"]
        if not order:
            return

        entry_point = order[0]
        visited = set()

        def dfs(node):
            if node in visited:
                return
            visited.add(node)
            for callee in self.call_graph.get(node, []):
                dfs(callee)

        dfs(entry_point)
        self.reachable = visited
        self.unreachable = set(order) - self.reachable

    def _analyze_pii_flows(self):
        for var in self.metadata["variables"]:
            if var["is_pii"]:
                self.pii_vars.add(var["name"])
                origin = "Declared definition"
                if var["source_copybook"]:
                    origin += f" (from copybook {var['source_copybook']})"
                self.pii_origins[var["name"]] = origin

        paragraphs = self.metadata["paragraphs"]
        order = self.metadata["paragraph_order"]
        
        changed = True
        iterations = 0
        max_iterations = 20
        
        while changed and iterations < max_iterations:
            changed = False
            iterations += 1
            
            for para_name in order:
                para_data = paragraphs[para_name]
                for move in para_data["moves"]:
                    src = move["source"]
                    dst = move["destination"]
                    
                    clean_src = re.sub(r'\(.*\)', '', src).strip()
                    clean_dst = re.sub(r'\(.*\)', '', dst).strip()
                    
                    if clean_src in self.pii_vars and clean_dst not in self.pii_vars:
                        self.pii_vars.add(clean_dst)
                        self.pii_origins[clean_dst] = f"Tainted in {para_name} from {clean_src}"
                        self.pii_flows.append({
                            "source": clean_src,
                            "destination": clean_dst,
                            "paragraph": para_name,
                            "statement": f"MOVE {src} TO {dst}"
                        })
                        changed = True

    def _analyze_egress_points(self):
        paragraphs = self.metadata["paragraphs"]
        order = self.metadata["paragraph_order"]
        
        for para_name in order:
            para_data = paragraphs[para_name]
            
            for sql in para_data["db2"]:
                for pii_var in self.pii_vars:
                    colon_var = f":{pii_var}"
                    if colon_var in sql["raw_sql"].upper():
                        self.egress_points.append({
                            "paragraph": para_name,
                            "type": "DB2 SQL",
                            "destination": f"Table: {sql['table']} ({sql['command']})",
                            "variable": pii_var,
                            "details": f"PII variable {pii_var} passed to SQL: {sql['raw_sql']}"
                        })

            for mq in para_data["mq"]:
                if mq["call_type"] in ["MQPUT"]:
                    for arg in mq["arguments"]:
                        clean_arg = re.sub(r'\(.*\)', '', arg).strip()
                        if clean_arg in self.pii_vars:
                            self.egress_points.append({
                                "paragraph": para_name,
                                "type": "IBM MQ",
                                "destination": f"MQ queue via {mq['call_type']}",
                                "variable": clean_arg,
                                "details": f"PII buffer {arg} transmitted to MQ"
                            })

            for cics in para_data["cics"]:
                for pii_var in self.pii_vars:
                    if pii_var in cics["raw_cics"].upper():
                        self.egress_points.append({
                            "paragraph": para_name,
                            "type": "CICS",
                            "destination": f"CICS Terminal Map: {cics['map']}",
                            "variable": pii_var,
                            "details": f"PII data output to terminal map in statement: {cics['raw_cics']}"
                        })

            for vsam in para_data["vsam"]:
                if vsam["operation"] in ["WRITE", "REWRITE"]:
                    file_var = vsam["file_variable"]
                    dataset_name = next((f["dataset"] for f in self.metadata["files"] if f["variable"] == file_var), file_var)
                    
                    for pii_var in self.pii_vars:
                        if pii_var == file_var or pii_var.startswith(file_var):
                            self.egress_points.append({
                                "paragraph": para_name,
                                "type": "VSAM File",
                                "destination": f"Dataset: {dataset_name}",
                                "variable": pii_var,
                                "details": f"PII variable {pii_var} written to VSAM file {file_var}"
                            })

            for ext in para_data["external_calls"]:
                for arg in ext["arguments"]:
                    clean_arg = re.sub(r'\(.*\)', '', arg).strip()
                    if clean_arg in self.pii_vars:
                        self.egress_points.append({
                            "paragraph": para_name,
                            "type": "External Call",
                            "destination": f"Subprogram: {ext['program']}",
                            "variable": clean_arg,
                            "details": f"PII argument {arg} passed to program {ext['program']}"
                        })
