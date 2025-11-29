# TDS-P2-LLM-ANALYSIS-QUIZ

# LLM Analysis Quiz Solver

An intelligent quiz solver that uses LLM (Large Language Models) to automatically answer data analysis and coding questions. The system intelligently determines when to use direct LLM responses or execute Python code for complex tasks.

## Overview

This project automates quiz solving through:
- **Async FastAPI server** for handling quiz requests
- **Playwright browser automation** for JavaScript-rendered pages
- **LLM strategy selection** (direct answers vs code execution)
- **Python code executor** with isolated execution environments
- **Multi-format file support** (CSV, JSON, PDF, Excel, Images)

## Architecture

```
FastAPI Server (main.py)
├── Advanced Quiz Solver (advanced_quiz_solver.py)
│   ├── Page fetching with Playwright
│   ├── Image extraction & processing
│   ├── File download & parsing
│   └── Answer submission
├── LLM Client (llm_client.py)
│   ├── Strategy determination
│   ├── Direct completion
│   └── Code generation
└── Code Executor (code_executor.py)
    ├── Sandboxed Python execution
    ├── File I/O management
    └── Output capture & parsing
```

## Features

**Smart Strategy Selection**
- Analyzes questions to determine if direct answer or code execution is needed
- Handles simple calculations, data analysis, ML tasks, and visualizations

**Multi-Format Data Processing**
- CSV files with pandas integration
- JSON data parsing
- PDF text extraction
- Excel spreadsheets
- Base64-encoded images

🔬 **Code Execution**
- Generates and executes Python code in isolated environment
- Supports ML libraries (scikit-learn, pandas, numpy)
- Visualization output (matplotlib, seaborn)
- Result capture and submission

**Browser Automation**
- Playwright for JavaScript rendering
- Automatic image extraction from pages
- Relative URL handling
- Network idle detection

## Setup

### 1. Clone Repository
```bash
git clone https://github.com/22f3000565/TDS-P2-LLM-ANALYSIS-QUIZ
cd TDS-P2-LLM-ANALYSIS-QUIZ
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment
Copy and fill `file.env`:
```env
EMAIL=your-email@example.com
SECRET=your-secret-key
AIPIPE_API_KEY=your-api-key
AIPIPE_BASE_URL=https://aipipe.org/openrouter/v1
MODEL_NAME=tngtech/deepseek-r1t2-chimera:free
HOST=0.0.0.0
PORT=8000
TIMEOUT_SECONDS=180
```

### 4. Run Server
```bash
python main.py
```

Server starts at `http://0.0.0.0:8000`

## API Endpoints

### POST `/`
Submit a quiz for solving
```json
{
  "email": "user@example.com",
  "secret": "secret-key",
  "url": "https://quiz-server.com/q1"
}
```

### GET `/health`
Health check endpoint
```json
{
  "status": "healthy",
  "service": "LLM Analysis Quiz Solver"
}
```

## Testing

### Run Local Test Server
```bash
# Terminal 1: Start test quiz server
python test_quiz_server.py  # Runs on port 5000

# Terminal 2: Start API server
python main.py  # Runs on port 8000

# Terminal 3: Run tests
python run_full_test.py
```

**Available Test Quizzes:**
- Q1: CSV sum calculation
- Q2: Data filtering (count rows)
- Q3: JSON aggregation
- Q4: String manipulation
- Q5: Average calculation
- Q6: Linear regression MSE

## Project Structure

```
├── main.py                      # FastAPI server & request handler
├── advanced_quiz_solver.py      # Core quiz solving logic
├── llm_client.py               # LLM API client & strategy selection
├── code_executor.py            # Python code execution manager
├── config.py                   # Configuration loader
├── test_quiz_server.py         # Local test quiz server
├── run_full_test.py            # Test runner
├── file.env                    # Environment variables
└── requirements.txt            # Python dependencies
```

## How It Works

1. **Request Received** → FastAPI validates email/secret and queues the quiz

2. **Page Fetch** → Playwright retrieves the quiz page (handles JavaScript)

3. **Content Analysis** → Extracts question, files, images, and submit URL

4. **Strategy Selection** → LLM determines if direct answer or code execution needed

5. **Answer Generation**
   - **Direct**: LLM generates answer based on context
   - **Code Execution**: LLM generates Python code, executor runs it

6. **Result Submission** → Answer posted back to quiz server

## Key Components

### LLMClient
- Interfaces with AIPipe/OpenRouter API
- Prompt engineering for strategy selection
- Code extraction from LLM responses
- Answer parsing (numbers, strings, JSON, etc.)

### CodeExecutor
- Sandboxed Python execution with timeout
- Temporary directory management
- File I/O (CSV, JSON, images)
- Result capture via stdout markers

### AdvancedQuizSolver
- Orchestrates the solving process
- Handles multiple file types
- Extracts and processes images
- Manages answer submission

## Technologies

- **FastAPI** - Async web framework
- **Playwright** - Browser automation
- **httpx** - Async HTTP client
- **pandas** - Data manipulation
- **scikit-learn** - ML models
- **PyPDF2** - PDF processing
- **matplotlib/seaborn** - Visualizations

## Configuration

| Variable | Purpose |
|----------|---------|
| `AIPIPE_API_KEY` | LLM API authentication |
| `MODEL_NAME` | LLM model to use (free or paid) |
| `TIMEOUT_SECONDS` | Maximum execution time |
| `PORT` | Server port (default: 8000) |

## Performance

- **Concurrent Handling**: Async request processing
- **Timeout Protection**: 60s code execution, 30s browser timeout
- **Sandboxed Execution**: Isolated temp directories per execution
- **Streaming Output**: Base64 encoding for binary data

## Troubleshooting

**Quiz not solving?**
- Check server logs for LLM errors
- Verify file downloads in `extract_file_urls()`
- Test Playwright separately: `python -c "from playwright.async_api import async_playwright"`

**Playwright issues?**
- Reinstall: `playwright install chromium`
- Check browser compatibility

**LLM API errors?**
- Verify API key and model name in `.env`
- Check rate limits and token usage

## License

MIT License

## Author

[22f3000565@ds.study.iitm.ac.in](mailto:22f3000565@ds.study.iitm.ac.in)
