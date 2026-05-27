import os

class COBOLPreprocessor:
    def __init__(self):
        self.line_mapping = {}  # Map from processed line index to original 1-based line number
        self.original_lines = []

    def preprocess(self, file_path):
        """
        Preprocesses a COBOL file to handle margins, comments, and continuation lines.
        Returns a single preprocessed string and sets up the line mapping.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"COBOL file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.original_lines = f.readlines()

        processed_lines = []
        original_line_num = 0

        for line in self.original_lines:
            original_line_num += 1
            # Pad line if it is shorter than 7 characters
            padded_line = line.rstrip('\r\n')
            if len(padded_line) < 7:
                padded_line = padded_line.ljust(7)

            indicator = padded_line[6] # Column 7 (0-indexed 6)
            
            # Extract program text (Cols 8-72, which is index 7 to 72)
            content = padded_line[7:72]
            content_stripped = content.rstrip()

            # Identify comments: column 7 indicator, or first char of content is '*'
            if indicator in ('*', '/') or content_stripped.lstrip().startswith('*'):
                # Ignore comments
                continue

            # Handle continuation lines
            if indicator == '-':
                # This line continues the previous line
                if processed_lines:
                    # Check if continuation is a string literal (starts with a quote)
                    temp = content_stripped.lstrip()
                    if temp.startswith("'") or temp.startswith('"'):
                        # String continuation: strip the quote and append
                        quote_char = temp[0]
                        # Find the first quote and append everything after it
                        quote_idx = temp.find(quote_char)
                        content_stripped = temp[quote_idx+1:]
                    
                    # Append to previous line
                    processed_lines[-1] = processed_lines[-1] + content_stripped
                else:
                    # No previous line, treat as normal
                    processed_lines.append(content_stripped)
                    self.line_mapping[len(processed_lines) - 1] = original_line_num
            else:
                # Normal line
                processed_lines.append(content_stripped)
                self.line_mapping[len(processed_lines) - 1] = original_line_num

        return "\n".join(processed_lines), self.line_mapping
