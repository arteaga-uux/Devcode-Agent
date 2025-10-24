# code_splitter.py

import re
from typing import List
from langchain.schema import Document


def split_c_code_by_function(doc: Document) -> List[Document]:
    """
    Splits C/C++ code into function-level chunks.
    
    Args:
        doc: A Document containing C/C++ source code.
        
    Returns:
        List of Document chunks, each containing roughly one function.
    """
    content = doc.page_content
    chunks = []
    
    # Simple regex to detect function definitions
    # Matches patterns like: return_type function_name(params) {
    function_pattern = re.compile(
        r'^[\w\s\*]+\s+[\w_]+\s*\([^)]*\)\s*\{',
        re.MULTILINE
    )
    
    matches = list(function_pattern.finditer(content))
    
    if not matches:
        # No functions found, return whole document as one chunk
        return [doc]
    
    # Extract functions with their bodies
    for i, match in enumerate(matches):
        start_pos = match.start()
        
        # Find the end of the function by counting braces
        brace_count = 0
        in_function = False
        end_pos = start_pos
        
        for j in range(start_pos, len(content)):
            char = content[j]
            if char == '{':
                brace_count += 1
                in_function = True
            elif char == '}':
                brace_count -= 1
                if in_function and brace_count == 0:
                    end_pos = j + 1
                    break
        
        # Extract function code
        function_code = content[start_pos:end_pos].strip()
        
        if function_code:
            chunk_metadata = doc.metadata.copy()
            chunk_metadata["chunk_type"] = "function"
            
            chunks.append(
                Document(
                    page_content=function_code,
                    metadata=chunk_metadata
                )
            )
    
    # If we found functions, also include any code before the first function (headers, includes, etc.)
    if matches and matches[0].start() > 0:
        header_code = content[:matches[0].start()].strip()
        if header_code:
            header_metadata = doc.metadata.copy()
            header_metadata["chunk_type"] = "header"
            chunks.insert(0, Document(
                page_content=header_code,
                metadata=header_metadata
            ))
    
    return chunks if chunks else [doc]

