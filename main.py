import argparse
import json
import os
from src.cobol_parser import COBOLParser
from src.analyzer import COBOLAnalyzer
from src.doc_generator import COBOLDocumentationGenerator
from src.jcl_parser import JCLParser
from src.jcl_doc_generator import JCLDocumentationGenerator

def main():
    parser = argparse.ArgumentParser(description="Mainframe COBOL & JCL Source Parser, Taint Analyzer, and Technical Document Generator")
    parser.add_argument("--source", required=True, help="Path to the COBOL or JCL source file")
    parser.add_argument("--copybook-dir", help="Directory containing referenced Copybooks (.cpy) (COBOL mode only)")
    parser.add_argument("--output-doc", default="documentation.md", help="Output path for generated markdown documentation")
    parser.add_argument("--output-json", default="analysis.json", help="Output path for raw analysis JSON metadata")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--ollama-model", default="skip", help="Local Ollama model name to use (use 'skip' to bypass LLM queries)")
    parser.add_argument("--mode", default="auto", choices=["cobol", "jcl", "auto"], help="Processing mode: 'cobol', 'jcl', or 'auto' (detect from extension)")

    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found.")
        return

    # Auto detect mode if set to auto
    mode = args.mode.lower()
    if mode == "auto":
        ext = os.path.splitext(args.source)[1].lower()
        if ext in [".jcl", ".job"]:
            mode = "jcl"
        else:
            mode = "cobol"

    print("======================================================================")
    print("           MAINFRAME ANALYSER, RELATIONSHIP & TAINT ENGINE            ")
    print("======================================================================")
    print(f"[*] Target Source File  : {args.source}")
    print(f"[*] Processing Mode     : {mode.upper()}")
    print(f"[*] Output Documentation: {args.output_doc}")
    print(f"[*] Output Metadata JSON: {args.output_json}")
    print(f"[*] Ollama API Endpoint : {args.ollama_url}")
    print(f"[*] Ollama Model Target : {args.ollama_model}")
    if mode == "cobol":
        print(f"[*] Copybook Directory  : {args.copybook_dir or 'None (Local Working Storage only)'}")
    print("----------------------------------------------------------------------")

    if mode == "jcl":
        # Run JCL modernization pipeline
        print("[1/3] Parsing JCL sequence and extracting step allocations...")
        jcl_parser = JCLParser()
        metadata = jcl_parser.parse(args.source)
        print(f"  [+] Job Name identified: {metadata['job_name']}")
        print(f"  [+] Total steps found  : {len(metadata['steps'])}")

        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        print(f"  [+] Saved parsed metadata JSON to {args.output_json}")

        print("[2/3] Generating JCL modernization report...")
        output_dir = os.path.dirname(os.path.abspath(args.output_doc))
        jcl_doc_gen = JCLDocumentationGenerator(
            metadata=metadata,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
            output_dir=output_dir
        )
        documentation = jcl_doc_gen.generate_documentation()

        with open(args.output_doc, 'w', encoding='utf-8') as f:
            f.write(documentation)
        print(f"  [+] Saved JCL modernization documentation to {args.output_doc}")

        # Output JCL Summary
        print("\n----------------------------------------------------------------------")
        print("                     JCL BATCH STREAM SUMMARY                         ")
        print("----------------------------------------------------------------------")
        print(f"Job Name  : {metadata['job_name']}")
        print(f"File Name : {metadata['file_name']}")
        print("\n[Step Execution Order]")
        utilities = ["DFSORT", "SORT", "IEBGENER", "IEFBR14", "IDCAMS", "IKJEFT01", "ADRDSSU", "IEBCOPY", "ICEGENER"]
        for idx, s in enumerate(metadata["steps"]):
            is_util = s["program"] in utilities
            classification = "System Utility" if is_util else "Custom Program"
            print(f"  {idx+1}. Step: {s['step_name']} | Runs: {s['program']} ({classification})")

        print("\n[Data Dependencies]")
        dsns = set()
        for s in metadata["steps"]:
            for dd in s["dds"]:
                dsns.add(dd["dsn"])
        if dsns:
            for d in sorted(list(dsns)):
                print(f"  * {d}")
        else:
            print("  * None")
        print("======================================================================")

    else:
        # Run COBOL pipeline
        print("[1/4] Parsing source code and resolving copybook expansions...")
        cobol_parser = COBOLParser(copybook_dir=args.copybook_dir)
        metadata = cobol_parser.parse(args.source)
        print(f"  [+] Program ID identified: {metadata['program_id']}")
        print(f"  [+] Author identified    : {metadata['author']}")
        print(f"  [+] Total variables found : {len(metadata['variables'])}")
        print(f"  [+] Total paragraphs found: {len(metadata['paragraphs'])}")

        # Step 2: Analyze
        print("[2/4] Executing reachability and static PII data-flow taint analysis...")
        analyzer = COBOLAnalyzer(metadata)
        analyzed_metadata = analyzer.analyze()
        analysis = analyzed_metadata["analysis"]

        print(f"  [+] Call Graph constructed (edges: {sum(len(c) for c in analysis['call_graph'].values())})")
        print(f"  [+] Dead code blocks: {len(analysis['unreachable_paragraphs'])} unreachable paragraphs")
        print(f"  [+] PII fields tracked: {len(analysis['pii_variables'])} variables")
        print(f"  [+] PII flows identified: {len(analysis['pii_flows'])} propagation movements")
        print(f"  [+] Sensitive egresses  : {len(analysis['pii_egress_points'])} data exposure risks")

        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(analyzed_metadata, f, indent=2)
        print(f"  [+] Saved analysis metadata JSON to {args.output_json}")

        # Step 3: Generate Document
        print("[3/4] Running documentation generator using local Ollama model...")
        output_dir = os.path.dirname(os.path.abspath(args.output_doc))
        doc_gen = COBOLDocumentationGenerator(
            metadata=analyzed_metadata,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
            output_dir=output_dir
        )
        documentation = doc_gen.generate_documentation()

        with open(args.output_doc, 'w', encoding='utf-8') as f:
            f.write(documentation)
        print(f"  [+] Saved technical documentation to {args.output_doc}")

        # Step 4: Output Program Comprehension Report
        print("\n----------------------------------------------------------------------")
        print("                     PROGRAM COMPREHENSION SUMMARY                    ")
        print("----------------------------------------------------------------------")
        print(f"Program ID: {analyzed_metadata['program_id']}")
        print(f"Author    : {analyzed_metadata['author']}")
        print("\n[Structure & Control Flow]")
        print(f"  * Entry Point: {analyzed_metadata['paragraph_order'][0] if analyzed_metadata['paragraph_order'] else 'None'}")
        print(f"  * Total Paragraphs: {len(analyzed_metadata['paragraphs'])}")
        print(f"  * Dead Code (Unreachable Paragraphs):")
        if analysis["unreachable_paragraphs"]:
            for p in analysis["unreachable_paragraphs"]:
                print(f"    - {p} (WARNING: Dead Code block)")
        else:
            print("    - None (All paragraphs are reachable)")

        print("\n[Copybooks Imported]")
        copybooks = sorted(list(set(v["source_copybook"] for v in analyzed_metadata["variables"] if v["source_copybook"])))
        if copybooks:
            for cp in copybooks:
                print(f"  * {cp}")
        else:
            print("  * None")

        print("\n[External Interfaces & Database References]")
        db2_tables = sorted(list(set(db["table"] for p in analyzed_metadata["paragraphs"].values() for db in p["db2"])))
        ims_segs = sorted(list(set(arg for p in analyzed_metadata["paragraphs"].values() for ims in p["ims"] for arg in ims["arguments"])))
        idms_recs = sorted(list(set(idms["record"] for p in analyzed_metadata["paragraphs"].values() for idms in p["idms"])))
        files = [f["dataset"] for f in analyzed_metadata["files"]]
        
        print(f"  * DB2 Tables: {', '.join(db2_tables) if db2_tables else 'None'}")
        print(f"  * IMS Segments: {', '.join(ims_segs) if ims_segs else 'None'}")
        print(f"  * IDMS Records: {', '.join(idms_recs) if idms_recs else 'None'}")
        print(f"  * VSAM Files: {', '.join(files) if files else 'None'}")
        
        cics_maps = sorted(list(set(cics["map"] for p in analyzed_metadata["paragraphs"].values() for cics in p["cics"] if cics["map"])))
        mq_calls = sorted(list(set(mq["call_type"] for p in analyzed_metadata["paragraphs"].values() for mq in p["mq"])))
        print(f"  * CICS Maps : {', '.join(cics_maps) if cics_maps else 'None'}")
        print(f"  * IBM MQ    : {', '.join(mq_calls) if mq_calls else 'None'}")

        print("\n[Security & PII Risk Profile]")
        print(f"  * Tracked PII Fields: {', '.join(list(analysis['pii_variables'].keys())[:10])}...")
        print(f"  * Active PII Flows (Taint Path):")
        if analysis["pii_flows"]:
            for flow in analysis["pii_flows"]:
                print(f"    - {flow['statement']} in paragraph `{flow['paragraph']}`")
        else:
            print("    - None")
            
        print(f"  * Sensitive Egress Points (Data Leak Risks):")
        if analysis["pii_egress_points"]:
            for eg in analysis["pii_egress_points"]:
                print(f"    - [{eg['type']}] PII field `{eg['variable']}` -> {eg['destination']} (Location: `{eg['paragraph']}`)")
        else:
            print("    - None (No exposures detected)")
        print("======================================================================")

if __name__ == '__main__':
    main()
