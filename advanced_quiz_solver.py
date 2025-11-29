import asyncio
import logging
from playwright.async_api import async_playwright
import httpx
import base64
import re
import json
from typing import Dict, Any, Optional, List
from config import config
from llm_client import LLMClient
from code_executor import CodeExecutor
import pandas as pd
from io import BytesIO
import PyPDF2

logger = logging.getLogger(__name__)

class AdvancedQuizSolver:
    """Enhanced quiz solver with code execution and image handling capabilities"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.code_executor = CodeExecutor()
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.downloaded_files = {}
    
    async def solve_quiz(self, quiz_url: str) -> Dict[str, Any]:
        """Solve a single quiz question with enhanced capabilities"""
        try:
            # Fetch and parse the quiz page (now includes images)
            quiz_content, images = await self.fetch_quiz_page(quiz_url)
            
            if not quiz_content:
                logger.error("Failed to fetch quiz content")
                return {"correct": False, "reason": "Failed to fetch quiz page"}
            
            logger.info(f"Quiz content fetched: {len(quiz_content)} characters")
            logger.info(f"Found {len(images)} images in the page")
            
            # Extract submit URL and any file URLs
            submit_url = self.extract_submit_url(quiz_content)
            file_urls = self.extract_file_urls(quiz_content)
            
            if not submit_url:
                logger.error("Could not find submit URL")
                return {"correct": False, "reason": "Submit URL not found"}
            
            logger.info(f"Submit URL: {submit_url}")
            logger.info(f"Found {len(file_urls)} file URLs")

            # Convert relative URLs to absolute
            from urllib.parse import urljoin
            base_url = '/'.join(quiz_url.split('/')[:3])
            
            absolute_file_urls = []
            for file_url in file_urls:
                if file_url.startswith('/'):
                    absolute_url = base_url + file_url
                    absolute_file_urls.append(absolute_url)
                    logger.info(f"Converted relative URL: {file_url} -> {absolute_url}")
                else:
                    absolute_file_urls.append(file_url)
            
            # Download and analyze files if present
            file_data = {}
            for file_url in absolute_file_urls:
                logger.info(f"Downloading file: {file_url}")
                data = await self.download_and_process_file(file_url)
                if data:
                    file_data[file_url] = data
            
            # Add images to file_data
            for idx, img_data in enumerate(images):
                file_data[f"image_{idx}"] = img_data
            
            # Determine solution strategy
            strategy, code = await self.llm_client.get_solution_strategy(
                quiz_content, 
                file_data
            )
            
            logger.info(f"Solution strategy: {strategy}")
            
            answer = None
            
            if strategy == "code_execution" and code:
                # Execute code to get answer
                logger.info("Executing generated code...")
                print("\n" + "="*60)
                print("GENERATED CODE:")
                print("="*60)
                print(code)
                print("="*60 + "\n")
                
                success, result, error = await self.code_executor.execute_code(
                    code, 
                    file_data
                )
                
                if success:
                    answer = result
                    logger.info(f"Code execution successful. Result: {type(answer)}")
                else:
                    logger.error(f"Code execution failed: {error}")
                    # Fall back to direct solving
                    logger.info("Falling back to direct solving...")
                    answer = await self.solve_with_context(
                        quiz_content, 
                        quiz_url, 
                        file_data
                    )
            else:
                # Solve directly using LLM
                answer = await self.solve_with_context(
                    quiz_content, 
                    quiz_url, 
                    file_data
                )
            
            if answer is None:
                logger.error("Failed to generate answer")
                return {"correct": False, "reason": "Failed to solve quiz"}
            
            logger.info(f"Generated answer type: {type(answer)}")
            if isinstance(answer, str) and len(answer) > 100:
                logger.info(f"Answer preview: {answer[:100]}...")
            else:
                logger.info(f"Generated answer: {answer}")
            
            # Submit the answer
            result = await self.submit_answer(submit_url, quiz_url, answer)
            
            return result
            
        except Exception as e:
            logger.error(f"Error solving quiz: {e}", exc_info=True)
            return {"correct": False, "reason": str(e)}
    
    async def fetch_quiz_page(self, url: str) -> tuple[Optional[str], List[Dict]]:
        """Fetch quiz page with JavaScript rendering and extract images"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config.HEADLESS)
                context = await browser.new_context()
                page = await context.new_page()
                
                await page.goto(url, wait_until="networkidle", timeout=config.BROWSER_TIMEOUT)
                await asyncio.sleep(3)
                
                body_text = await page.evaluate("() => document.body.innerText")
                html_content = await page.content()
                
                # Extract images from the page
                images = await self.extract_images_from_page(page)
                
                await browser.close()
                
                content = f"{body_text}\n\nHTML:\n{html_content}"
                if images:
                    content += f"\n\n[Page contains {len(images)} image(s)]"
                
                return content, images
                
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None, []
    
    async def extract_images_from_page(self, page) -> List[Dict]:
        """Extract all images from the page as base64"""
        try:
            # Get all img elements
            img_elements = await page.query_selector_all('img')
            images = []
            
            for idx, img in enumerate(img_elements):
                try:
                    # Get the image source
                    src = await img.get_attribute('src')
                    alt = await img.get_attribute('alt') or f"image_{idx}"
                    
                    if not src:
                        continue
                    
                    # Handle data URIs
                    if src.startswith('data:'):
                        images.append({
                            "type": "image",
                            "format": "base64_uri",
                            "data": src,
                            "alt": alt,
                            "index": idx
                        })
                        logger.info(f"Extracted inline image {idx}: {alt}")
                    
                    # Handle regular URLs
                    elif src.startswith('http') or src.startswith('/'):
                        # Download the image
                        if src.startswith('/'):
                            base_url = '/'.join(page.url.split('/')[:3])
                            src = base_url + src
                        
                        try:
                            response = await self.http_client.get(src)
                            if response.status_code == 200:
                                img_bytes = response.content
                                b64_data = base64.b64encode(img_bytes).decode('utf-8')
                                
                                # Determine mime type from content-type or extension
                                content_type = response.headers.get('content-type', 'image/png')
                                if 'image' not in content_type:
                                    content_type = 'image/png'
                                
                                data_uri = f"data:{content_type};base64,{b64_data}"
                                
                                images.append({
                                    "type": "image",
                                    "format": "base64_uri",
                                    "data": data_uri,
                                    "alt": alt,
                                    "index": idx,
                                    "url": src
                                })
                                logger.info(f"Downloaded and encoded image {idx}: {alt}")
                        except Exception as e:
                            logger.warning(f"Failed to download image {src}: {e}")
                
                except Exception as e:
                    logger.warning(f"Error processing image {idx}: {e}")
                    continue
            
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []
    
    def extract_submit_url(self, content: str) -> Optional[str]:
        """Extract submit URL from content"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]()]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            if "submit" in url.lower():
                return url.strip()
        
        return None
    
    def extract_file_urls(self, content: str) -> list:
        """Extract downloadable file URLs"""
        html_pattern = r'href=["\']([^"\']+)["\']'
        urls = re.findall(html_pattern, content)
        
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]()]+'
        urls.extend(re.findall(url_pattern, content))
        
        file_urls = []
        file_extensions = ['.pdf', '.csv', '.json', '.xlsx', '.txt', '.xml']
        
        for url in urls:
            url = url.strip()
            
            if any(ext in url.lower() for ext in file_extensions):
                file_urls.append(url)
            
            if '/data/' in url or '/files/' in url or '/download/' in url:
                file_urls.append(url)
        
        return list(set(file_urls))
        
    async def download_and_process_file(self, url: str) -> Optional[Dict]:
        """Download and process different file types"""
        try:
            response = await self.http_client.get(url)
            
            if response.status_code != 200:
                logger.error(f"Failed to download {url}: {response.status_code}")
                return None
            
            content_type = response.headers.get("content-type", "")
            content = response.content
            
            if "pdf" in content_type or url.endswith(".pdf"):
                return await self.process_pdf(content)
            elif "json" in content_type or url.endswith(".json"):
                return self.process_json(content)
            elif "csv" in content_type or url.endswith(".csv"):
                return self.process_csv(content)
            elif "excel" in content_type or url.endswith((".xlsx", ".xls")):
                return self.process_excel(content)
            elif "image" in content_type or url.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp")):
                return self.process_image(content, content_type)
            else:
                return {"type": "text", "content": content.decode('utf-8', errors='ignore')}
                
        except Exception as e:
            logger.error(f"Error processing file {url}: {e}")
            return None
    
    def process_image(self, content: bytes, content_type: str) -> Dict:
        """Process image file"""
        try:
            b64_data = base64.b64encode(content).decode('utf-8')
            if not content_type or 'image' not in content_type:
                content_type = 'image/png'
            
            data_uri = f"data:{content_type};base64,{b64_data}"
            
            return {
                "type": "image",
                "format": "base64_uri",
                "data": data_uri,
                "size": len(content)
            }
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
    
    async def process_pdf(self, content: bytes) -> Dict:
        """Process PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            pages = []
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                pages.append({
                    "page_number": i + 1,
                    "text": text
                })
            
            return {
                "type": "pdf",
                "num_pages": len(pages),
                "pages": pages
            }
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return None
    
    def process_json(self, content: bytes) -> Dict:
        """Process JSON file"""
        try:
            data = json.loads(content)
            return {
                "type": "json",
                "data": data
            }
        except Exception as e:
            logger.error(f"Error processing JSON: {e}")
            return None
    
    def process_csv(self, content: bytes) -> Dict:
        """Process CSV file"""
        try:
            df = pd.read_csv(BytesIO(content))
            
            return {
                "type": "csv",
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "head": df.head(10).to_dict('records'),
                "describe": df.describe().to_dict(),
                "data": df.to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error processing CSV: {e}")
            return None
    
    def process_excel(self, content: bytes) -> Dict:
        """Process Excel file"""
        try:
            df = pd.read_excel(BytesIO(content))
            
            return {
                "type": "excel",
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "head": df.head(10).to_dict('records'),
                "data": df.to_dict('records')
            }
        except Exception as e:
            logger.error(f"Error processing Excel: {e}")
            return None
    
    async def solve_with_context(self, quiz_content: str, quiz_url: str, file_data: Dict) -> Any:
        """Solve quiz with full context including file data and images"""
        try:
            prompt_parts = [
                "You are solving a data analysis quiz. Analyze carefully and provide the CORRECT FINAL ANSWER ONLY, WITHOUT ANY EXPLANATIONS/STEPS.",
                "",
                "QUIZ QUESTION:",
                quiz_content,
                ""
            ]
            
            if file_data:
                prompt_parts.append("DOWNLOADED FILES AND IMAGES:")
                for key, data in file_data.items():
                    if data.get('type') == 'image':
                        prompt_parts.append(f"\n{key}:")
                        prompt_parts.append(f"Type: Image")
                        prompt_parts.append(f"Alt text: {data.get('alt', 'N/A')}")
                        prompt_parts.append(f"Data URI: {data['data'][:100]}... (truncated)")
                        prompt_parts.append("NOTE: Full base64 image data available for vision analysis")
                    
                    elif data.get('type') == 'csv':
                        prompt_parts.append(f"\nFile: {key}")
                        prompt_parts.append(f"Type: {data.get('type', 'unknown')}")
                        prompt_parts.append(f"Shape: {data['shape']}")
                        prompt_parts.append(f"Columns: {data['columns']}")
                        prompt_parts.append(f"Complete data: {json.dumps(data['data'], indent=2)}")
                    
                    elif data.get('type') == 'excel':
                        prompt_parts.append(f"\nFile: {key}")
                        prompt_parts.append(f"Type: {data.get('type', 'unknown')}")
                        prompt_parts.append(f"Shape: {data['shape']}")
                        prompt_parts.append(f"Columns: {data['columns']}")
                        prompt_parts.append(f"Complete data: {json.dumps(data['data'], indent=2)}")
                    
                    elif data.get('type') == 'pdf':
                        prompt_parts.append(f"\nFile: {key}")
                        prompt_parts.append(f"Type: PDF")
                        prompt_parts.append(f"Pages: {data['num_pages']}")
                        for page in data['pages']:
                            prompt_parts.append(f"\nPage {page['page_number']}:")
                            prompt_parts.append(page['text'][:500])
                    
                    elif data.get('type') == 'json':
                        prompt_parts.append(f"\nFile: {key}")
                        prompt_parts.append(f"Type: JSON")
                        prompt_parts.append(f"Data: {json.dumps(data['data'], indent=2)}")
                
                prompt_parts.append("")
            
            prompt_parts.extend([
                "INSTRUCTIONS:",
                "1. Read the question carefully (including any images)",
                "2. Analyze any provided data",
                "3. Perform required calculations/analysis",
                "4. RETURN ONLY THE FINAL ANSWER IN THE REQUIRED FORMAT:",
                "   - Number: just the number (e.g., 12345)",
                "   - String: just the string (e.g., hello)",
                "   - Boolean: true or false",
                "   - JSON: valid JSON object",
                "   - Image: base64 data URI (data:image/png;base64,...)",
                "",
                "FINAL ANSWER:"
            ])
            
            full_prompt = "\n".join(prompt_parts)
            
            answer = await self.llm_client.get_completion(full_prompt, quiz_url)
 
            print("\n+------------------ FULL PROMPT ------------------+")
            print(full_prompt[:1000] + "..." if len(full_prompt) > 1000 else full_prompt)
            print("+------------------------------------------------+\n")

            print("+------------------ LLM OUTPUT ------------------+")
            print(answer)
            print("+------------------------------------------------+")
            
            return answer
            
        except Exception as e:
            logger.error(f"Error solving with context: {e}")
            return None
    
    async def submit_answer(self, submit_url: str, quiz_url: str, answer: Any) -> Dict[str, Any]:
        """Submit answer to quiz endpoint"""
        try:
            payload = {
                "email": config.EMAIL,
                "secret": config.SECRET,
                "url": quiz_url,
                "answer": answer
            }
            
            logger.info(f"Submitting answer to {submit_url}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)[:500]}...")
            
            response = await self.http_client.post(
                submit_url,
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "correct": False,
                    "reason": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return {"correct": False, "reason": str(e)}
    
    async def close(self):
        """Cleanup resources"""
        await self.http_client.aclose()
        await self.llm_client.close()
        self.code_executor.cleanup()