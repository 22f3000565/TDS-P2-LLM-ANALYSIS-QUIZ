import asyncio
import logging
import tempfile
import os
import sys
import subprocess
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class CodeExecutor:
    """Execute Python code safely in isolated environment"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="quiz_exec_")
        self.timeout = 60  # seconds
        
    async def execute_code(self, code: str, file_data: Dict = None) -> Tuple[bool, Any, str]:
        """
        Execute Python code and return results
        
        Returns:
            Tuple[success, result, error_message]
        """
        try:
            # Create temporary directory for this execution
            exec_dir = tempfile.mkdtemp(dir=self.temp_dir)
            
            # Save any downloaded files to the execution directory
            if file_data:
                await self._save_files_to_disk(file_data, exec_dir)
            
            # Create the Python script
            script_path = os.path.join(exec_dir, "quiz_solution.py")
            
            # Wrap code to capture output
            wrapped_code = self._wrap_code(code, exec_dir)
            
            with open(script_path, 'w') as f:
                f.write(wrapped_code)
            
            # Execute the script
            result = await self._run_script(script_path, exec_dir)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing code: {e}", exc_info=True)
            return False, None, str(e)
    
    def _wrap_code(self, code: str, exec_dir: str) -> str:
        """Wrap user code to capture output properly"""
        
        wrapper = f'''
import sys
import os
import json
import base64
from pathlib import Path

# Set working directory
os.chdir(r"{exec_dir}")

# Result container
__result__ = None
__output_file__ = None

try:
    # User code starts here
{self._indent_code(code, 4)}
    # User code ends here
    
    # Try to capture the result
    # Check if there's a variable called 'answer' or 'result'
    if 'answer' in locals():
        __result__ = answer
    elif 'result' in locals():
        __result__ = result
    
    # Check for output files (images, csv, etc.)
    output_files = []
    for ext in ['*.png', '*.jpg', '*.jpeg', '*.svg', '*.csv', '*.json', '*.xlsx']:
        output_files.extend(list(Path('.').glob(ext)))
    
    if output_files and not __result__:
        # Use the most recently created file
        latest_file = max(output_files, key=os.path.getctime)
        __output_file__ = str(latest_file)
        
except Exception as e:
    print(f"EXECUTION_ERROR: {{e}}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Output results as JSON
output = {{}}
if __result__ is not None:
    output['result'] = __result__
if __output_file__:
    output['output_file'] = __output_file__

print("__QUIZ_RESULT_START__")
print(json.dumps(output, default=str))
print("__QUIZ_RESULT_END__")
'''
        return wrapper
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces"""
        indent = ' ' * spaces
        return '\n'.join(indent + line if line.strip() else line 
                        for line in code.split('\n'))
    
    async def _save_files_to_disk(self, file_data: Dict, exec_dir: str):
        """Save downloaded files to execution directory"""
        for url, data in file_data.items():
            if not data:
                continue
                
            file_type = data.get('type', 'unknown')
            
            # Determine filename from URL or type
            filename = self._extract_filename(url, file_type)
            filepath = os.path.join(exec_dir, filename)
            
            try:
                if file_type == 'csv':
                    # Save CSV data
                    import pandas as pd
                    df = pd.DataFrame(data['data'])
                    df.to_csv(filepath, index=False)
                    logger.info(f"Saved CSV file: {filename}")
                    
                elif file_type == 'json':
                    # Save JSON data
                    with open(filepath, 'w') as f:
                        json.dump(data['data'], f, indent=2)
                    logger.info(f"Saved JSON file: {filename}")
                    
                elif file_type == 'excel':
                    # Save Excel data
                    import pandas as pd
                    df = pd.DataFrame(data['data'])
                    df.to_excel(filepath, index=False)
                    logger.info(f"Saved Excel file: {filename}")
                    
                elif file_type == 'pdf':
                    # PDF is more complex, save the text content
                    text_file = filepath.replace('.pdf', '.txt')
                    with open(text_file, 'w') as f:
                        for page in data.get('pages', []):
                            f.write(f"Page {page['page_number']}:\n")
                            f.write(page['text'])
                            f.write('\n\n')
                    logger.info(f"Saved PDF text: {text_file}")
                
                elif file_type == 'image':
                    # Save image from base64 data URI
                    data_uri = data.get('data', '')
                    if data_uri.startswith('data:'):
                        # Extract base64 data
                        header, b64_data = data_uri.split(',', 1)
                        img_bytes = base64.b64decode(b64_data)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_bytes)
                        logger.info(f"Saved image file: {filename}")
                    
            except Exception as e:
                logger.error(f"Error saving file {filename}: {e}")
    
    def _extract_filename(self, url: str, file_type: str) -> str:
        """Extract filename from URL or generate one"""
        # Handle image_N keys
        if url.startswith('image_'):
            index = url.split('_')[1]
            return f"image_{index}.png"
        
        # Try to get filename from URL
        if '/' in url:
            potential_name = url.split('/')[-1]
            if '.' in potential_name:
                return potential_name
        
        # Generate filename based on type
        extensions = {
            'csv': '.csv',
            'json': '.json',
            'excel': '.xlsx',
            'pdf': '.pdf',
            'text': '.txt',
            'image': '.png'
        }
        
        ext = extensions.get(file_type, '.dat')
        return f"data{ext}"
    
    async def _run_script(self, script_path: str, exec_dir: str) -> Tuple[bool, Any, str]:
        """Run the Python script and capture results"""
        try:
            # Run the script with timeout
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=exec_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return False, None, "Code execution timeout"
            
            stdout_text = stdout.decode('utf-8', errors='ignore')
            stderr_text = stderr.decode('utf-8', errors='ignore')
            
            # Check for execution errors
            if process.returncode != 0:
                logger.error(f"Script failed with code {process.returncode}")
                logger.error(f"STDERR: {stderr_text}")
                return False, None, f"Execution failed: {stderr_text}"
            
            # Parse the result
            result = self._parse_output(stdout_text, exec_dir)
            
            if result is not None:
                return True, result, ""
            else:
                return False, None, "Could not extract result from execution"
                
        except Exception as e:
            logger.error(f"Error running script: {e}", exc_info=True)
            return False, None, str(e)
    
    def _parse_output(self, stdout: str, exec_dir: str) -> Any:
        """Parse the output from executed code"""
        try:
            # Look for our result markers
            if "__QUIZ_RESULT_START__" in stdout and "__QUIZ_RESULT_END__" in stdout:
                start_idx = stdout.index("__QUIZ_RESULT_START__") + len("__QUIZ_RESULT_START__")
                end_idx = stdout.index("__QUIZ_RESULT_END__")
                result_json = stdout[start_idx:end_idx].strip()
                
                output = json.loads(result_json)
                
                # Check if we have a direct result
                if 'result' in output:
                    return output['result']
                
                # Check if we have an output file
                if 'output_file' in output:
                    filepath = os.path.join(exec_dir, output['output_file'])
                    return self._process_output_file(filepath)
                
            return None
            
        except Exception as e:
            logger.error(f"Error parsing output: {e}")
            return None
    
    def _process_output_file(self, filepath: str) -> Any:
        """Process output file and return appropriate format"""
        try:
            if not os.path.exists(filepath):
                logger.error(f"Output file not found: {filepath}")
                return None
            
            ext = os.path.splitext(filepath)[1].lower()
            
            # Image files - return as base64 data URI
            if ext in ['.png', '.jpg', '.jpeg', '.svg']:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                    b64_data = base64.b64encode(file_data).decode('utf-8')
                    
                    mime_types = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.svg': 'image/svg+xml'
                    }
                    mime_type = mime_types.get(ext, 'application/octet-stream')
                    
                    return f"data:{mime_type};base64,{b64_data}"
            
            # CSV files - return as data or base64
            elif ext == '.csv':
                import pandas as pd
                df = pd.read_csv(filepath)
                # Return as JSON object or base64 depending on context
                # For now, return as base64 data URI
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                    b64_data = base64.b64encode(file_data).decode('utf-8')
                    return f"data:text/csv;base64,{b64_data}"
            
            # JSON files
            elif ext == '.json':
                with open(filepath, 'r') as f:
                    return json.load(f)
            
            # Excel files
            elif ext in ['.xlsx', '.xls']:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                    b64_data = base64.b64encode(file_data).decode('utf-8')
                    return f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_data}"
            
            # Other files - return as base64
            else:
                with open(filepath, 'rb') as f:
                    file_data = f.read()
                    b64_data = base64.b64encode(file_data).decode('utf-8')
                    return f"data:application/octet-stream;base64,{b64_data}"
                    
        except Exception as e:
            logger.error(f"Error processing output file: {e}")
            return None
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logger.error(f"Error cleaning up temp directory: {e}")