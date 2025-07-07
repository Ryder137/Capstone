import requests
import json

# Test get_journal_entries endpoint
def test_journal_entries():
    print("Testing /get_journal_entries endpoint...")
    url = "http://localhost:5000/get_journal_entries"
    
    # You'll need to be logged in to test this endpoint
    # This is a basic test that will work if the user is already logged in
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing /get_journal_entries: {str(e)}")

# Test chat endpoint
def test_chat():
    print("\nTesting /chat endpoint...")
    url = "http://localhost:5000/chat"
    
    # This endpoint requires authentication and a POST request with a message
    try:
        headers = {'Content-Type': 'application/json'}
        data = {'message': 'Hello, this is a test message'}
        response = requests.post(url, json=data, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error testing /chat: {str(e)}")

if __name__ == "__main__":
    test_journal_entries()
    test_chat()
