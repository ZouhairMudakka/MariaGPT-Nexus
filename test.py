import requests

def test_conversation(queries):
    print("\nTesting conversation flow:")
    for query in queries:
        response = requests.post('http://127.0.0.1:5000/support', 
            json={"query": query})
        print(f"\nUser: {query}")
        print(f"Assistant: {response.json()['response']}")

# Test conversation flow
test_queries = [
    "Hi, I need help with my account",
    "I can't log in",
    "Yes, I tried resetting my password but didn't receive any email",
    "The email address I'm using is test@example.com"
]

test_conversation(test_queries) 