import httpx
import json
import logging
import re
from typing import Any, Optional, Dict, Tuple
from config import config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.api_key = config.AIPIPE_API_KEY
        self.base_url = config.AIPIPE_BASE_URL
        self.model = config.MODEL_NAME
        self.http_client = httpx.AsyncClient(timeout=120.0)
    
    async def get_completion(self, prompt: str, context_url: str = None) -> Any:
        """Get completion from LLM with tool use capabilities"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Call LLM API
            response = await self.call_api(messages)
            
            if not response:
                return None
            
            # Extract answer from response
            answer = self.extract_answer(response)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error getting LLM completion: {e}")
            return None
    
    async def get_solution_strategy(self, quiz_content: str, file_data: Dict) -> Tuple[str, Optional[str]]:
        """
        Analyze the quiz and determine if code execution is needed
        
        Returns:
            Tuple[strategy, code]
            strategy: "direct" or "code_execution"
            code: Python code if strategy is "code_execution", None otherwise
        """
        try:
            prompt = self._build_strategy_prompt(quiz_content, file_data)
            
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.call_api(messages)
            
            if not response:
                return "direct", None
            
            content = response["choices"][0]["message"]["content"]
            
            # Check if LLM suggests code execution
            if self._needs_code_execution(content, quiz_content):
                code = self._extract_code(content)
                if code:
                    logger.info("Strategy: Code execution required")
                    return "code_execution", code
            
            logger.info("Strategy: Direct answer")
            return "direct", None
            
        except Exception as e:
            logger.error(f"Error determining strategy: {e}")
            return "direct", None
    
    def _build_strategy_prompt(self, quiz_content: str, file_data: Dict) -> str:
        """Build prompt to determine solution strategy"""
        
        prompt_parts = [
            "Analyze this quiz question and determine the best solution approach.",
            "",
            "QUIZ QUESTION:",
            quiz_content,
            ""
        ]
        
        if file_data:
            prompt_parts.append("AVAILABLE DATA FILES:")
            for url, data in file_data.items():
                if data:
                    file_type = data.get('type', 'unknown')
                    prompt_parts.append(f"- {url} (Type: {file_type})")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "TASK:",
            "Determine if this question requires:",
            "1. DIRECT ANSWER: Simple calculation, data lookup, or text processing that you can solve directly",
            "2. CODE EXECUTION: Complex tasks like:",
            "   - Creating visualizations (charts, plots, graphs)",
            "   - Machine learning models (regression, classification, clustering)",
            "   - Complex data transformations or aggregations",
            "   - Generating files (CSV, images, etc.)",
            "   - Statistical analysis requiring specific libraries",
            "",
            "If CODE EXECUTION is needed:",
            "- Write complete, executable Python code",
            "- Use standard libraries: pandas, numpy, matplotlib, seaborn, sklearn, etc.",
            "- Store the final answer in a variable called 'answer'",
            "- For visualizations, save to a file (e.g., plt.savefig('output.png'))",
            "- For CSV output, save to a file",
            "- Include all necessary imports",
            "- Handle file reading (files are available in current directory)",
            "- Code should be production-ready and handle edge cases",
            "",
            "Respond with:",
            "STRATEGY: [DIRECT or CODE_EXECUTION]",
            "",
            "If CODE_EXECUTION, provide:",
            "```python",
            "# Your complete Python code here",
            "```"
        ])
        
        return "\n".join(prompt_parts)
    
    def _needs_code_execution(self, response: str, quiz_content: str) -> bool:
        """Determine if code execution is needed based on response and question content"""
        
        # Check explicit strategy declaration
        if "STRATEGY: CODE_EXECUTION" in response.upper():
            return True
        
        # Check for code blocks
        if "```python" in response or "```Python" in response:
            return True
        
        # Check quiz content for keywords suggesting code execution
        execution_keywords = [
            'visualization', 'visualize', 'plot', 'chart', 'graph',
            'machine learning', 'regression', 'classification', 'clustering',
            'model', 'predict', 'train',
            'generate', 'create a file', 'create csv',
            'statistical analysis', 'hypothesis test',
            'correlation', 'distribution'
        ]
        
        content_lower = quiz_content.lower()
        if any(keyword in content_lower for keyword in execution_keywords):
            # If question suggests complex task and LLM provided code, execute it
            if "```" in response:
                return True
        
        return False
    
    def _extract_code(self, response: str) -> Optional[str]:
        """Extract Python code from LLM response"""
        try:
            # Look for code blocks
            pattern = r'```(?:python|Python)?\s*(.*?)```'
            matches = re.findall(pattern, response, re.DOTALL)
            
            if matches:
                # Take the first code block
                code = matches[0].strip()
                logger.info(f"Extracted code ({len(code)} chars)")
                return code
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting code: {e}")
            return None
    
    async def generate_code_solution(self, quiz_content: str, file_data: Dict) -> Optional[str]:
        """
        Generate Python code to solve the quiz question
        """
        try:
            prompt = self._build_code_generation_prompt(quiz_content, file_data)
            
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await self.call_api(messages)
            
            if not response:
                return None
            
            content = response["choices"][0]["message"]["content"]
            code = self._extract_code(content)
            
            return code
            
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            return None
    
    def _build_code_generation_prompt(self, quiz_content: str, file_data: Dict) -> str:
        """Build prompt for code generation"""
        
        prompt_parts = [
            "Generate Python code to solve this quiz question.",
            "",
            "QUIZ QUESTION:",
            quiz_content,
            ""
        ]
        
        if file_data:
            prompt_parts.append("AVAILABLE DATA FILES:")
            for url, data in file_data.items():
                if data:
                    file_type = data.get('type', 'unknown')
                    filename = self._get_filename_from_url(url, file_type)
                    prompt_parts.append(f"- {filename} (Type: {file_type})")
                    
                    if file_type == 'csv' and 'columns' in data:
                        prompt_parts.append(f"  Columns: {data['columns']}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "REQUIREMENTS:",
            "1. Write complete, executable Python code",
            "2. Import all necessary libraries (pandas, numpy, matplotlib, sklearn, etc.)",
            "3. Read data files from current directory using their filenames",
            "4. Store the final answer in a variable called 'answer'",
            "5. For visualizations:",
            "   - Create the plot/chart",
            "   - Save to a file (e.g., plt.savefig('output.png'))",
            "   - Use high DPI for quality (dpi=300)",
            "6. For CSV output:",
            "   - Save to a file (e.g., df.to_csv('output.csv', index=False))",
            "7. Handle errors gracefully",
            "8. Include comments explaining key steps",
            "",
            "OUTPUT FORMAT:",
            "Provide ONLY the Python code in a code block:",
            "```python",
            "# Your code here",
            "```"
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_filename_from_url(self, url: str, file_type: str) -> str:
        """Extract filename from URL"""
        if '/' in url:
            potential_name = url.split('/')[-1]
            if '.' in potential_name:
                return potential_name
        
        extensions = {
            'csv': 'data.csv',
            'json': 'data.json',
            'excel': 'data.xlsx',
            'pdf': 'data.txt'  # PDF is saved as text
        }
        
        return extensions.get(file_type, 'data.dat')
    
    async def call_api(self, messages: list) -> Optional[dict]:
        """Call the AIPipe API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 3000  # Increased for code generation
            }

            full_url = f"{self.base_url}/chat/completions"
            logger.info(f"Calling AIPipe API at: {full_url}")
            logger.info(f"Using model: {self.model}")
            
            response = await self.http_client.post(
                full_url,
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info("LLM API call successful")
                return result
            else:
                logger.error(f"LLM API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return None
    
    def extract_answer(self, response: dict) -> Any:
        """Extract and parse the answer from LLM response"""
        try:
            if not response or "choices" not in response:
                return None
            
            content = response["choices"][0]["message"]["content"]
            logger.info(f"LLM response: {content}")
            
            # Try to parse as JSON first
            try:
                json_match = re.search(r'\{.*\}|\[.*\]', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
            
            # Try to extract number
            number_match = re.search(r'-?\d+\.?\d*', content)
            if number_match:
                num_str = number_match.group()
                if '.' in num_str:
                    return float(num_str)
                return int(num_str)
            
            # Try to extract boolean
            content_lower = content.lower().strip()
            if content_lower in ['true', 'yes']:
                return True
            if content_lower in ['false', 'no']:
                return False
            
            # Return as string, cleaned up
            return content.strip()
            
        except Exception as e:
            logger.error(f"Error extracting answer: {e}")
            return None
    
    async def close(self):
        """Cleanup resources"""
        await self.http_client.aclose()