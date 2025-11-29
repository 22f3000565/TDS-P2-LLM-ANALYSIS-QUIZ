from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
import asyncio
import logging
from typing import Optional
from config import config
from advanced_quiz_solver import AdvancedQuizSolver as QuizSolver

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
    """Solve a chain of quiz questions"""
    solver = QuizSolver()
    current_url = initial_url
    question_number = 1
    
    try:
        while current_url:
            logger.info(f"Solving question {question_number}: {current_url}")
            
            result = await solver.solve_quiz(current_url)
            
            if result.get("correct"):
                logger.info(f"Question {question_number} answered correctly!")
                current_url = result.get("url")
                if current_url:
                    logger.info(f"Moving to next question: {current_url}")
                    question_number += 1
                else:
                    logger.info("Quiz completed successfully!")
                    break
            else:
                logger.warning(f"Question {question_number} answered incorrectly: {result.get('reason')}")
                # Check if we can skip to next question
                next_url = result.get("url")
                if next_url and next_url != current_url:
                    logger.info(f"Skipping to next question: {next_url}")
                    current_url = next_url
                    question_number += 1
                else:
                    # Retry current question if within time limit
                    logger.info("Retrying current question...")
                    await asyncio.sleep(1)  # Small delay before retry
                    
    except Exception as e:
        logger.error(f"Error in quiz chain: {e}", exc_info=True)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "LLM Analysis Quiz Solver"}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "LLM Analysis Quiz Solver",
        "version": "1.0",
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
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info"
    )