"""
Local Test Quiz Server
Creates multiple quiz questions to test your endpoint
Each question is on a separate URL and uses JavaScript rendering
"""

from flask import Flask, request, jsonify, send_file
import json
import base64
from io import BytesIO
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__)

# Store quiz state
quiz_state = {}

# Quiz questions database
QUIZZES = {
    "q1": {
        "type": "simple_calculation",
        "title": "Q1. Simple CSV Analysis",
        "question": "Download the <a href='/data/q1.csv'>CSV file</a>. What is the sum of the 'sales' column?",
        "submit_url": "http://localhost:5000/submit",
        "answer": 15000,
        "next_quiz": "q2"
    },
    "q2": {
        "type": "filtering",
        "title": "Q2. Data Filtering",
        "question": "Download the <a href='/data/q2.csv'>CSV file</a>. How many rows have 'status' equal to 'active'?",
        "submit_url": "http://localhost:5000/submit",
        "answer": 7,
        "next_quiz": "q3"
    },
    "q3": {
        "type": "json_analysis",
        "title": "Q3. JSON Data Analysis",
        "question": "Download the <a href='/data/q3.json'>JSON file</a>. What is the total count of all 'quantity' fields?",
        "submit_url": "http://localhost:5000/submit",
        "answer": 450,
        "next_quiz": "q4"
    },
    "q4": {
        "type": "string_manipulation",
        "title": "Q4. Text Processing",
        "question": "The secret code is 'DATAQUEST2024'. Convert it to lowercase. What is the result?",
        "submit_url": "http://localhost:5000/submit",
        "answer": "dataquest2024",
        "next_quiz": "q5"
    },
    "q5": {
        "type": "aggregation",
        "title": "Q5. Data Aggregation",
        "question": "Download the <a href='/data/q5.csv'>CSV file</a>. What is the average of the 'price' column? (round to 2 decimal places)",
        "submit_url": "http://localhost:5000/submit",
        "answer": 45.67,
        "next_quiz": "q6"
    },
    "q6": {
        "type": "linear_regression",
        "title": "Q6. Linear Regression - MSE Calculation",
        "question": """Download the <a href='/data/q6.csv'>CSV file</a> containing columns 'X' and 'y'. 
    Train a Linear Regression model on the FULL dataset (no train-test split).
    Use sklearn.linear_model.LinearRegression with default parameters (fit_intercept=True).
    Calculate the Mean Squared Error (MSE) on the training data.
    What is the MSE value? (round to 2 decimal places)""",
        "submit_url": "http://localhost:5000/submit",
        "answer": 0.12,
        "next_quiz": None
}

}

# Sample data generators
def generate_q1_csv():
    data = {
        'product': ['A', 'B', 'C', 'D', 'E'],
        'sales': [2000, 3500, 4000, 2500, 3000]
    }
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

def generate_q2_csv():
    data = {
        'id': range(1, 11),
        'name': ['User' + str(i) for i in range(1, 11)],
        'status': ['active', 'inactive', 'active', 'active', 'inactive', 
                   'active', 'active', 'active', 'active', 'inactive']
    }
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

def generate_q3_json():
    data = {
        "items": [
            {"name": "Item1", "quantity": 100},
            {"name": "Item2", "quantity": 150},
            {"name": "Item3", "quantity": 200}
        ]
    }
    return json.dumps(data, indent=2)

def generate_q5_csv():
    data = {
        'item': ['X', 'Y', 'Z'],
        'price': [45.50, 46.00, 45.50]
    }
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

def generate_q6_csv():
    """Generate dummy data for linear regression question"""
    np.random.seed(42)
    X_data = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    y_data = 2 * X_data + 3 + np.random.randn(10) * 0.5
    
    data = {'X': X_data, 'y': y_data}
    df = pd.DataFrame(data)
    return df.to_csv(index=False)

@app.route('/quiz/<quiz_id>')
def quiz_page(quiz_id):
    """Serve quiz page with JavaScript rendering"""
    
    if quiz_id not in QUIZZES:
        return "Quiz not found", 404
    
    quiz = QUIZZES[quiz_id]
    
    # Create the question text with submit instructions
    question_text = f"""{quiz['title']}

{quiz['question']}

Post your answer to {quiz['submit_url']} with this JSON payload:

{{
  "email": "your-email",
  "secret": "your-secret",
  "url": "http://localhost:5000/quiz/{quiz_id}",
  "answer": YOUR_ANSWER_HERE
}}"""
    
    # Base64 encode the question
    encoded_question = base64.b64encode(question_text.encode()).decode()
    
    # HTML with JavaScript rendering
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Quiz {quiz_id.upper()}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        #result {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            white-space: pre-wrap;
            line-height: 1.6;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        pre {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div id="result"></div>
    
    <script>
        document.querySelector("#result").innerHTML = atob("{encoded_question}");
    </script>
</body>
</html>
"""
    return html

@app.route('/data/q1.csv')
def data_q1():
    """Serve Q1 CSV data"""
    csv_data = generate_q1_csv()
    return csv_data, 200, {'Content-Type': 'text/csv'}

@app.route('/data/q2.csv')
def data_q2():
    """Serve Q2 CSV data"""
    csv_data = generate_q2_csv()
    return csv_data, 200, {'Content-Type': 'text/csv'}

@app.route('/data/q3.json')
def data_q3():
    """Serve Q3 JSON data"""
    json_data = generate_q3_json()
    return json_data, 200, {'Content-Type': 'application/json'}

@app.route('/data/q5.csv')
def data_q5():
    """Serve Q5 CSV data"""
    csv_data = generate_q5_csv()
    return csv_data, 200, {'Content-Type': 'text/csv'}

@app.route('/data/q6.csv')
def data_q6():
    """Serve Q6 CSV data"""
    csv_data = generate_q6_csv()
    return csv_data, 200, {'Content-Type': 'text/csv'}

@app.route('/submit', methods=['POST'])
def submit_answer():
    """Handle answer submissions"""
    
    try:
        data = request.json
        
        email = data.get('email')
        secret = data.get('secret')
        url = data.get('url')
        answer = data.get('answer')
        
        if not all([email, secret, url, answer]):
            return jsonify({
                "correct": False,
                "reason": "Missing required fields"
            }), 400
        
        # Extract quiz ID from URL
        quiz_id = url.split('/')[-1]
        
        if quiz_id not in QUIZZES:
            return jsonify({
                "correct": False,
                "reason": "Invalid quiz ID"
            }), 400
        
        quiz = QUIZZES[quiz_id]
        expected_answer = quiz['answer']
        
        # Check answer
        correct = False
        
        if isinstance(expected_answer, (int, float)):
            # For numeric answers, allow small tolerance
            try:
                user_answer = float(answer)
                correct = abs(user_answer - expected_answer) < 0.01
            except:
                correct = False
        else:
            # For string answers, case-insensitive comparison
            correct = str(answer).strip().lower() == str(expected_answer).strip().lower()
        
        # Prepare response
        response = {
            "correct": correct,
            "quiz_id": quiz_id
        }
        
        if correct:
            response["message"] = "Correct answer!"
            if quiz['next_quiz']:
                response["url"] = f"http://localhost:5000/quiz/{quiz['next_quiz']}"
        else:
            response["reason"] = f"Incorrect. Expected: {expected_answer}, Got: {answer}"
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "correct": False,
            "reason": str(e)
        }), 500

@app.route('/')
def home():
    """Home page with quiz links"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Quiz Test Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .quiz-list {
            list-style: none;
            padding: 0;
        }
        .quiz-list li {
            background: #f5f5f5;
            margin: 10px 0;
            padding: 15px;
            border-radius: 4px;
        }
        .quiz-list a {
            color: #0066cc;
            text-decoration: none;
            font-weight: bold;
        }
        .info {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>🎯 Quiz Test Server</h1>
    
    <div class="info">
        <h3>Test Your Endpoint</h3>
        <p>Send a POST request to your endpoint with:</p>
        <pre>{
  "email": "your-email",
  "secret": "your-secret",
  "url": "http://localhost:5000/quiz/q1"
}</pre>
    </div>
    
    <h2>Available Quizzes</h2>
    <ul class="quiz-list">
        <li>
            <a href="/quiz/q1">Quiz 1</a> - CSV Analysis (Sum calculation)
        </li>
        <li>
            <a href="/quiz/q2">Quiz 2</a> - Data Filtering (Count rows)
        </li>
        <li>
            <a href="/quiz/q3">Quiz 3</a> - JSON Analysis (Sum quantities)
        </li>
        <li>
            <a href="/quiz/q4">Quiz 4</a> - Text Processing (String transformation)
        </li>
        <li>
            <a href="/quiz/q5">Quiz 5</a> - Data Aggregation (Average calculation)
        </li>
        <li>
            <a href="/quiz/q6">Quiz 6</a> - Machine Learning (Linear Regression MSE)
        </li>
    </ul>
    
    <h2>Answers (for verification)</h2>
    <ul>
        <li>Q1: 15000</li>
        <li>Q2: 7</li>
        <li>Q3: 450</li>
        <li>Q4: dataquest2024</li>
        <li>Q5: 45.67</li>
        <li>Q6: 0.12</li>
    </ul>
</body>
</html>
"""
    return html

if __name__ == '__main__':
    print("=" * 60)
    print("Quiz Test Server Starting...")
    print("=" * 60)
    print("\nAvailable endpoints:")
    print("  http://localhost:5000/          - Home page")
    print("  http://localhost:5000/quiz/q1   - Quiz 1")
    print("  http://localhost:5000/quiz/q2   - Quiz 2")
    print("  http://localhost:5000/quiz/q3   - Quiz 3")
    print("  http://localhost:5000/quiz/q4   - Quiz 4")
    print("  http://localhost:5000/quiz/q5   - Quiz 5")
    print("  http://localhost:5000/quiz/q6   - Quiz 6")
    print("\nTest your endpoint with:")
    print('  POST http://localhost:8000/')
    print('  Body: {"email": "...", "secret": "...", "url": "http://localhost:5000/quiz/q1"}')
    print("\n" + "=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)