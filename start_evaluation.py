import httpx
import asyncio
import json
from config import config

async def start_evaluation():
    """Start the evaluation by submitting to the initial URL"""
    
    # The starting point
    submit_url = "https://tds-llm-analysis.s-anand.net/submit"
    initial_quiz_url = "https://tds-llm-analysis.s-anand.net/project2-reevals"
    
    print("="*80)
    print("STARTING EVALUATION")
    print("="*80)
    print(f"Email: {config.EMAIL}")
    print(f"Initial URL: {initial_quiz_url}")
    print(f"Submit URL: {submit_url}")
    print("="*80)
    
    # First, let's visit the initial URL to see what the first question is
    print("\n1. Fetching initial question...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(initial_quiz_url)
            print(f"Status: {response.status_code}")
            print(f"\nPage Content Preview:")
            print("-"*80)
            print(response.text[:500])
            print("-"*80)
            
            # Now trigger your solver by POSTing to your local server
            print("\n2. Triggering your quiz solver...")
            print(f"POSTing to http://{config.HOST}:{config.PORT}/")
            
            payload = {
                "email": config.EMAIL,
                "secret": config.SECRET,
                "url": initial_quiz_url
            }
            
            response = await client.post(
                #f"http://{config.HOST}:{config.PORT}/",
                "https://subaquatic-unconducively-jocelynn.ngrok-free.dev",
                json=payload,
                timeout=5.0
            )
            
            print(f"Response: {response.status_code}")
            print(f"Body: {response.json()}")
            
            print("\n" + "="*80)
            print("✓ Quiz solving started!")
            print("✓ Check your server logs to see the progress")
            print("="*80)
            
        except Exception as e:
            print(f"Error: {e}")
            print("\nMake sure your server is running with: python main.py")

if __name__ == "__main__":
    # Validate config
    config.validate()
    
    # Run
    asyncio.run(start_evaluation())