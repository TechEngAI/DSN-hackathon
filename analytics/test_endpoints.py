import subprocess
import time
import requests
import sys
import os

def test_endpoints():
    print("="*60)
    print("   STARTING FASTAPI APPS & ENDPOINT INTEGRATION TESTS")
    print("="*60)

    # Use the same python interpreter running this script
    python_path = sys.executable

    # Start Uvicorn as a subprocess
    cmd = [
        python_path, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ]
    
    print(f"Launching Uvicorn server: {' '.join(cmd)}")
    server_process = subprocess.Popen(
        cmd,
        cwd="dsn-bct-hackathon",
        text=True
    )
    
    # Wait for server to boot up
    print("Waiting 12 seconds for server to start...")
    time.sleep(12)
    
    # Check if server process is still alive
    if server_process.poll() is not None:
        print("Error: Uvicorn server failed to start.")
        sys.exit(1)
        
    base_url = "http://127.0.0.1:8000"
    
    try:
        # 1. Test Health Endpoint
        print("\nChecking health endpoint...")
        res = requests.get(f"{base_url}/health")
        print(f"Status Code: {res.status_code}")
        print(f"Response: {res.json()}")
        assert res.status_code == 200, "Health check failed"
        assert res.json().get("status") == "running"

        # 2. Test Task A: Generate Review Endpoint
        print("\nTesting Task A /task-a/generate-review...")
        task_a_payload = {
            "user_id": "Jt3GylPuH64uA3zTdbMdCg",
            "item_id": "yelp_naija_1",
            "persona": {
                "user_id": "Jt3GylPuH64uA3zTdbMdCg",
                "rating_bias": "appreciative_inclined",
                "preferred_topics": ["Casual Dining", "Nightlife & Drinks"],
                "lifestyle_profile": "Beer_Parlour_Regular",
                "naija_cues": True,
                "review_style_notes": "Writes short conversational reviews."
            }
        }
        res_a = requests.post(f"{base_url}/task-a/generate-review", json=task_a_payload)
        print(f"Status Code: {res_a.status_code}")
        print(f"Response: {json_pretty(res_a.json())}")
        assert res_a.status_code == 200, "Task A failed"
        data_a = res_a.json()
        assert "rating" in data_a
        assert "review_text" in data_a
        assert "reasoning" in data_a
        print("Task A Schema Validation: PASSED")

        # 3. Test Task B: Recommendation Endpoint (Normal Flow)
        print("\nTesting Task B /task-b/recommend...")
        task_b_payload = {
            "user_id": "mh_-eMZ6K5RLWhZyISBhwA",
            "query": "spicy chicken wings and beer",
            "top_k": 3,
            "is_cold_start": False
        }
        res_b = requests.post(f"{base_url}/task-b/recommend", json=task_b_payload)
        print(f"Status Code: {res_b.status_code}")
        print(f"Response: {json_pretty(res_b.json())}")
        assert res_b.status_code == 200, "Task B recommendation failed"
        data_b = res_b.json()
        assert "recommendations" in data_b
        assert "reasoning_summary" in data_b
        for rec in data_b["recommendations"]:
            assert "item_id" in rec or "id" in rec
            assert "name" in rec
            assert "reason" in rec
        print("Task B Schema Validation: PASSED")

        # 4. Test Task B: Recommendation Endpoint (Cold Start Flow - Stage 1: Get Questions)
        print("\nTesting Task B /task-b/recommend (Cold Start - Stage 1)...")
        task_b_cold_payload = {
            "user_id": "new_user_123",
            "query": "anything",
            "top_k": 3,
            "is_cold_start": True
        }
        res_b_cold = requests.post(f"{base_url}/task-b/recommend", json=task_b_cold_payload)
        print(f"Status Code: {res_b_cold.status_code}")
        print(f"Response: {json_pretty(res_b_cold.json())}")
        assert res_b_cold.status_code == 200, "Task B cold-start failed"
        data_b_cold = res_b_cold.json()
        assert data_b_cold.get("status") == "cold_start"
        assert "questions" in data_b_cold
        print("Task B Cold Start Stage 1 Validation: PASSED")

        # 5. Test Task B: Recommendation Endpoint (Cold Start Flow - Stage 2: Submit Responses)
        print("\nTesting Task B /task-b/recommend (Cold Start - Stage 2)...")
        task_b_cold_responses_payload = {
            "user_id": "new_user_123",
            "query": "traditional dinner",
            "top_k": 3,
            "is_cold_start": True,
            "user_responses": {
                "What's your favourite type of food or cuisine?": "suya and pepper soup",
                "Rate your last great experience out of 5": "5",
                "Name one thing that ruins your experience anywhere": "slow service",
                "Are you a 'try new things' or 'stick to favourites' person?": "try new things",
                "Do you prefer local Nigerian spots or international chains?": "local Nigerian spots"
            }
        }
        res_b_cold_2 = requests.post(f"{base_url}/task-b/recommend", json=task_b_cold_responses_payload)
        print(f"Status Code: {res_b_cold_2.status_code}")
        print(f"Response: {json_pretty(res_b_cold_2.json())}")
        assert res_b_cold_2.status_code == 200, "Task B cold-start stage 2 failed"
        data_b_cold_2 = res_b_cold_2.json()
        assert "recommendations" in data_b_cold_2
        assert "reasoning_summary" in data_b_cold_2
        print("Task B Cold Start Stage 2 Validation: PASSED")

        print("\n" + "="*60)
        print("   ALL APIS RUNNING AND FULLY VALIDATED SUCCESSFULLY!")
        print("="*60)

    finally:
        print("\nTerminating Uvicorn server process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("Server process shut down cleanly.")
        except subprocess.TimeoutExpired:
            print("Forcing server process shutdown...")
            server_process.kill()
            server_process.wait()
            print("Server process killed.")

def json_pretty(data):
    import json
    return json.dumps(data, indent=2)

if __name__ == "__main__":
    test_endpoints()
