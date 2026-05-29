import os
import markdown
from xhtml2pdf import pisa

class COBOLPDFConverter:
    def __init__(self):
        pass

    def convert_markdown_to_pdf(self, markdown_text, output_pdf_path):
        """
        Converts a markdown string into a formatted PDF using markdown & xhtml2pdf.
        """
        # Convert Markdown to HTML
        # Enable tables and fenced code blocks extensions
        html_body = markdown.markdown(
            markdown_text, 
            extensions=['tables', 'fenced_code']
        )
        
        # Build full HTML document with styling
        html_document = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>COBOL Technical Analysis Documentation</title>
    <style>
        @page {{
            size: a4;
            margin: 2.5cm;
            @frame footer {{
                -pdf-frame-content: page-footer;
                bottom: 1.2cm;
                height: 1cm;
            }}
        }}
        body {{
            font-family: Helvetica, Arial, sans-serif;
            color: #1e293b;
            font-size: 10pt;
            line-height: 1.5;
        }}
        h1 {{
            font-size: 22pt;
            color: #0f172a;
            border-bottom: 2px solid #cbd5e1;
            padding-bottom: 6px;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-before: always;
        }}
        h1:first-of-type {{
            page-break-before: avoid;
        }}
        h2 {{
            font-size: 14pt;
            color: #1e293b;
            margin-top: 25px;
            margin-bottom: 10px;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 4px;
        }}
        h3 {{
            font-size: 11pt;
            color: #334155;
            margin-top: 18px;
            margin-bottom: 8px;
        }}
        p {{
            margin-top: 0;
            margin-bottom: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            margin-bottom: 15px;
            font-size: 9pt;
        }}
        th {{
            background-color: #f8fafc;
            color: #0f172a;
            font-weight: bold;
            text-align: left;
            border: 1px solid #cbd5e1;
            padding: 8px;
        }}
        td {{
            border: 1px solid #e2e8f0;
            padding: 8px;
            vertical-align: top;
        }}
        tr:nth-child(even) td {{
            background-color: #fafafa;
        }}
        pre {{
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 10px;
            font-family: Courier, monospace;
            font-size: 8.5pt;
            margin-top: 10px;
            margin-bottom: 12px;
            white-space: pre-wrap;
        }}
        code {{
            font-family: Courier, monospace;
            font-size: 9pt;
            background-color: #f1f5f9;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        ul, ol {{
            margin-top: 0;
            margin-bottom: 12px;
            padding-left: 20px;
        }}
        li {{
            margin-bottom: 4px;
        }}
        .footer {{
            text-align: center;
            font-size: 8pt;
            color: #64748b;
            border-top: 1px solid #cbd5e1;
            padding-top: 8px;
        }}
        /* Risk highlights styling */
        strong {{
            color: #0f172a;
        }}
        /* Custom highlight classes matching markdown structure */
        .risk-high {{
            color: #ef4444;
            font-weight: bold;
        }}
        .risk-medium {{
            color: #f59e0b;
            font-weight: bold;
        }}
        .risk-low {{
            color: #10b981;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    {html_body}
    <div id="page-footer" class="footer">
        COBOL Application Technical Documentation - Page <pdf:pagenumber> of <pdf:pagecount>
    </div>
</body>
</html>
"""

        # Custom link callback to resolve image paths on Windows
        def link_callback(uri, rel):
            import urllib.parse
            # Convert URI to local filename
            if uri.startswith("file:///"):
                decoded_uri = urllib.parse.unquote(uri[8:])
                path = os.path.normpath(decoded_uri)
            elif uri.startswith("file:/"):
                decoded_uri = urllib.parse.unquote(uri[6:])
                path = os.path.normpath(decoded_uri)
            else:
                decoded_uri = urllib.parse.unquote(uri)
                path = os.path.abspath(decoded_uri)
                if not os.path.exists(path):
                    path = os.path.abspath(os.path.join("output", decoded_uri))
            
            if os.path.exists(path):
                return path
            print(f"Warning: link_callback could not resolve path: {uri} (looked at: {path})")
            return uri

        # xhtml2pdf expects a destination file handle
        with open(output_pdf_path, "wb") as pdf_file:
            # Renders HTML to PDF with link_callback
            pisa_status = pisa.CreatePDF(html_document, dest=pdf_file, link_callback=link_callback)
            
        return not pisa_status.err
