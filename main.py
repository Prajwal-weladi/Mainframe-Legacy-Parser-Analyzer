import argparse
import json
import os
from cobol_parser import COBOLParser
from analyzer import COBOLAnalyzer
from doc_generator import COBOLDocumentationGenerator

def main():
    parser = argparse.ArgumentParser(description="COBOL Source Parser, Taint Analyzer, and Technical Document Generator")
    parser.add_argument("--source", required=True, help="Path to the COBOL source file (.cbl, .cob)")
    parser.add_argument("--copybook-dir", help="Directory containing referenced Copybooks (.cpy)")
    parser.add_argument("--output-doc", default="documentation.md", help="Output path for generated markdown documentation")
    parser.add_argument("--output-json", default="analysis.json", help="Output path for raw analysis JSON metadata")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API base URL")
    parser.add_argument("--ollama-model", default="llama3:latest", help="Local Ollama model name to use")

    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found.")
        return

    print("   COBOL PARSER, RELATIONSHIP & TAINT ENGINE    ")
    print(f"[*] Target COBOL Source : {args.source}")
    print(f"[*] Copybook Directory  : {args.copybook_dir or 'None (Working Storage only)'}")
    print(f"[*] Output Documentation : {args.output_doc}")
    print(f"[*] Output Metadata JSON: {args.output_json}")
    print(f"[*] Ollama API Endpoint : {args.ollama_url}")
    print(f"[*] Ollama Model Target : {args.ollama_model}")

    # Step 1: Parse
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
    doc_gen = COBOLDocumentationGenerator(
        metadata=analyzed_metadata,
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model
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
