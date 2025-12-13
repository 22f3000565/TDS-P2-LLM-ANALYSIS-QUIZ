from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
import asyncio
import logging
from typing import Optional
from config import config
from advanced_quiz_solver import AdvancedQuizSolver as QuizSolver
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLM Analysis Quiz Solver")

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str

class QuizResponse(BaseModel):
    status: str
    message: str
    details: Optional[dict] = None

@app.post("/")
async def handle_quiz(request: Request):
    """Main endpoint to receive and solve quiz tasks"""
    try:
        # Parse JSON payload
        try:
            body = await request.json()
        except Exception as e:
            logger.error(f"Invalid JSON: {e}")
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate request structure
        try:
            quiz_req = QuizRequest(**body)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            raise HTTPException(status_code=400, detail="Invalid request format")
        
        # Verify secret
        if quiz_req.secret != config.SECRET:
            logger.warning(f"Invalid secret attempt for email: {quiz_req.email}")
            raise HTTPException(status_code=403, detail="Invalid secret")
        
        # Verify email
        if quiz_req.email != config.EMAIL:
            logger.warning(f"Email mismatch: {quiz_req.email} != {config.EMAIL}")
            raise HTTPException(status_code=403, detail="Email does not match")
        
        logger.info(f"Received quiz request for URL: {quiz_req.url}")
        
        # Start quiz solving in background
        asyncio.create_task(solve_quiz_chain(quiz_req.url))
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Quiz solving started",
                "url": quiz_req.url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

async def solve_quiz_chain(initial_url: str):
    """Solve a chain of quiz questions with intelligent retry using code execution"""
    solver = QuizSolver()
    current_url = initial_url
    question_number = 1
    
    QUESTION_TIMEOUT = 160
    MAX_RETRIES_PER_QUESTION = 2  # Try: auto, forced code

    try:
        while current_url:
            logger.info(f"\n{'='*80}")
            logger.info(f"QUESTION {question_number}: {current_url}")
            logger.info(f"{'='*80}\n")

            question_start_time = time.time()
            retry_count = 0
            question_solved = False
            last_next_url = None  # Track the last next URL we got
            
            while retry_count < MAX_RETRIES_PER_QUESTION and not question_solved:
                retry_count += 1
                force_code = (retry_count == 2)  # Force code execution on second try only
                
                if force_code:
                    logger.info(f"\n{'*'*80}")
                    logger.info(f"RETRY ATTEMPT {retry_count}: Using FORCED CODE EXECUTION")
                    logger.info(f"{'*'*80}\n")
                else:
                    logger.info(f"Attempt {retry_count}: Using automatic strategy detection")
                
                # Solve the question
                result = await solver.solve_quiz(current_url, force_code_execution=force_code)
                
                elapsed = time.time() - question_start_time
                
                # Store next URL if provided (even if answer is wrong)
                if result.get("url"):
                    last_next_url = result["url"]
                    logger.info(f"→ Server provided next URL: {last_next_url}")
                
                if result.get("correct"):
                    logger.info(f"\n{'✓'*80}")
                    logger.info(f"✓ Question {question_number} SOLVED in {elapsed:.1f}s (attempt {retry_count})")
                    logger.info(f"{'✓'*80}\n")
                    
                    question_solved = True
                    current_url = result.get("url")
                    
                    if current_url:
                        logger.info(f"→ Moving to next question: {current_url}")
                        question_number += 1
                    else:
                        logger.info(f"\n{'🎉'*40}")
                        logger.info("🎉 QUIZ COMPLETED SUCCESSFULLY! 🎉")
                        logger.info(f"{'🎉'*40}\n")
                        break
                else:
                    reason = result.get('reason', 'Unknown error')
                    logger.warning(f"\n{'✗'*80}")
                    logger.warning(f"✗ Question {question_number} attempt {retry_count} FAILED: {reason}")
                    logger.warning(f"{'✗'*80}\n")
                    
                    # Check if timeout exceeded
                    if elapsed >= QUESTION_TIMEOUT:
                        logger.error(f"⏱ Timeout reached for question {question_number} ({elapsed:.1f}s)")
                        
                        # If we have a next URL (from any attempt), use it
                        if last_next_url and last_next_url != current_url:
                            logger.info(f"→ Using last known next URL: {last_next_url}")
                            current_url = last_next_url
                            question_number += 1
                            break
                        else:
                            logger.error("No next URL available, stopping.")
                            return
                    
                    # Check if we should retry
                    if retry_count < MAX_RETRIES_PER_QUESTION:
                        logger.info(f"⟳ Preparing retry {retry_count + 1}/{MAX_RETRIES_PER_QUESTION}...")
                        await asyncio.sleep(2)  # Small delay before retry
                    else:
                        logger.error(f"Max retries ({MAX_RETRIES_PER_QUESTION}) reached for question {question_number}")
                        
                        # Even if we failed, if server gave us next URL, continue
                        # (Question says difficulty 1 reveals next URL even if wrong)
                        if last_next_url and last_next_url != current_url:
                            logger.info(f"→ Continuing with next URL (Difficulty 1 allows this): {last_next_url}")
                            current_url = last_next_url
                            question_number += 1
                            break
                        else:
                            logger.error("No next URL provided, stopping quiz chain")
                            return
            
            # If we exhausted retries without solving
            if not question_solved and last_next_url and last_next_url != current_url:
                logger.warning(f"Moving to next question despite not solving question {question_number}")
                current_url = last_next_url
                question_number += 1
            elif not question_solved:
                logger.error(f"Cannot continue - question {question_number} not solved and no next URL")
                break
                    
    except Exception as e:
        logger.error(f"⚠ Critical error in quiz chain: {e}", exc_info=True)
    finally:
        # Cleanup
        await solver.close()
        logger.info("\n" + "="*80)
        logger.info("Quiz solver cleanup completed")
        logger.info("="*80)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LLM Analysis Quiz Solver"}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "LLM Analysis Quiz Solver",
        "version": "2.0",
        "features": [
            "Automatic strategy detection",
            "Code execution fallback on failure",
            "Intelligent retry mechanism",
            "Image and file processing"
        ],
        "endpoints": {
            "POST /": "Submit quiz task",
            "GET /health": "Health check",
            "GET /": "API information"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration
    config.validate()
    
    logger.info(f"Starting server on {config.HOST}:{config.PORT}")
    logger.info(f"Email: {config.EMAIL}")
    logger.info(f"Timeout: {config.TIMEOUT_SECONDS} seconds")
    logger.info(f"Max retries per question: 2 (auto + forced code)")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )
