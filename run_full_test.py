"""
Complete Test Runner
Tests your endpoint against the local quiz server
"""

import requests
import json
import time
from config import config

class QuizTester:
    def __init__(self):
        self.quiz_server = "http://localhost:5000"
        self.api_endpoint = f"http://localhost:{config.PORT}"
        self.results = []
    
    def test_quiz(self, quiz_id, expected_answer):
        """Test a single quiz"""
        print(f"\n{'='*60}")
        print(f"Testing Quiz {quiz_id.upper()}")
        print('='*60)
        
        quiz_url = f"{self.quiz_server}/quiz/{quiz_id}"
        
        # Step 1: Send request to your API endpoint
        print(f"\n[1] Sending request to your API endpoint...")
        payload = {
            "email": config.EMAIL,
            "secret": config.SECRET,
            "url": quiz_url
        }
        
        try:
            response = requests.post(self.api_endpoint, json=payload, timeout=10)
            print(f"    Status: {response.status_code}")
            print(f"    Response: {response.json()}")
            
            if response.status_code != 200:
                print(f"    ❌ API endpoint rejected request")
                self.results.append({
                    "quiz": quiz_id,
                    "status": "failed",
                    "reason": "API rejected request"
                })
                return False
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            self.results.append({
                "quiz": quiz_id,
                "status": "failed",
                "reason": str(e)
            })
            return False
        
        # Step 2: Wait for background processing
        print(f"\n[2] Waiting for quiz to be solved (15 seconds)...")
        for i in range(15, 0, -1):
            print(f"    {i}...", end=" ", flush=True)
            time.sleep(1)
        print("\n")
        
        # Step 3: Manually verify by checking the quiz page
        print(f"[3] Quiz details:")
        print(f"    URL: {quiz_url}")
        print(f"    Expected answer: {expected_answer}")
        print(f"    Check your server logs to see if it was solved correctly")
        
        self.results.append({
            "quiz": quiz_id,
            "status": "completed",
            "expected_answer": expected_answer
        })
        
        return True
    
    def run_all_tests(self):
        """Run all quiz tests"""
        print("="*60)
        print("COMPLETE QUIZ TEST SUITE")
        print("="*60)
        print(f"\nQuiz Server: {self.quiz_server}")
        print(f"API Endpoint: {self.api_endpoint}")
        print(f"Email: {config.EMAIL}")
        
        # Check if both servers are running
        print(f"\n[Pre-check] Verifying servers are running...")
        
        try:
            response = requests.get(self.quiz_server, timeout=5)
            print(f"    ✅ Quiz server is running (port 5000)")
        except:
            print(f"    ❌ Quiz server not running!")
            print(f"    Start it with: python test_quiz_server.py")
            return
        
        try:
            response = requests.get(f"{self.api_endpoint}/health", timeout=5)
            print(f"    ✅ API server is running (port {config.PORT})")
        except:
            print(f"    ❌ API server not running!")
            print(f"    Start it with: python main.py")
            return
        
        # Define test cases
        test_cases = [
            ("q1", 15000),
            ("q2", 7),
            ("q3", 450),
            ("q4", "dataquest2024"),
            ("q5", 45.67)
        ]
        
        # Run each test
        for quiz_id, expected_answer in test_cases:
            success = self.test_quiz(quiz_id, expected_answer)
            
            if not success:
                print(f"\n⚠️  Test failed, continuing to next quiz...")
            
            # Small delay between tests
            time.sleep(2)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for result in self.results:
            quiz_id = result['quiz']
            status = result['status']
            
            if status == "completed":
                print(f"\n✅ Quiz {quiz_id.upper()}")
                print(f"   Expected: {result['expected_answer']}")
                print(f"   Check logs to verify if answer was correct")
            else:
                print(f"\n❌ Quiz {quiz_id.upper()}")
                print(f"   Reason: {result['reason']}")
        
        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\n1. Check your main.py logs to see quiz solving progress")
        print("2. Look for messages like:")
        print("   - 'Quiz content fetched'")
        print("   - 'Generated answer: XXX'")
        print("   - 'Question answered correctly'")
        print("\n3. If answers are incorrect:")
        print("   - Check LLM prompts in llm_client.py")
        print("   - Verify file processing in quiz_solver.py")
        print("   - Ensure Playwright is working correctly")
        print("\n4. Once all tests pass, you're ready to deploy!")
        print("="*60)

def manual_test_single_quiz():
    """Test a single quiz manually"""
    print("\n" + "="*60)
    print("MANUAL SINGLE QUIZ TEST")
    print("="*60)
    
    quiz_id = input("\nEnter quiz ID (q1, q2, q3, q4, q5, q6): ").strip().lower()
    
    if quiz_id not in ['q1', 'q2', 'q3', 'q4', 'q5', 'q6']:
        print("Invalid quiz ID")
        return
    
    quiz_url = f"http://localhost:5000/quiz/{quiz_id}"
    
    print(f"\n1. Visit the quiz page: {quiz_url}")
    print(f"2. Read the question and note the expected answer")
    print(f"3. Your endpoint should:")
    print(f"   - Fetch the page")
    print(f"   - Extract the question and download URL")
    print(f"   - Process the data")
    print(f"   - Submit the answer")
    
    print(f"\nSending request to your endpoint...")
    
    payload = {
        "email": config.EMAIL,
        "secret": config.SECRET,
        "url": quiz_url
    }
    
    try:
        response = requests.post(
            f"http://localhost:{config.PORT}",
            json=payload,
            timeout=10
        )
        
        print(f"\nAPI Response:")
        print(f"  Status: {response.status_code}")
        print(f"  Body: {json.dumps(response.json(), indent=2)}")
        
        print(f"\nNow check your main.py logs for the solving process!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("QUIZ ENDPOINT TESTING TOOL")
    print("="*60)
    print("\nMake sure both servers are running:")
    print("  Terminal 1: python test_quiz_server.py")
    print("  Terminal 2: python main.py")
    print("\nThen run this script in Terminal 3")
    
    print("\n" + "="*60)
    choice = input("\nChoose test mode:\n1. Run all quizzes\n2. Test single quiz\n\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        tester = QuizTester()
        tester.run_all_tests()
    elif choice == "2":
        manual_test_single_quiz()
    else:
        print("Invalid choice")