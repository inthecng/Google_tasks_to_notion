import json
import sys

def format_token(token_str):
    try:
        # Try to parse the token string as JSON
        token_data = json.loads(token_str)
        
        # Format it properly
        formatted_token = json.dumps(token_data, indent=2)
        print("\nFormatted token (use this to update GitHub secret):")
        print(formatted_token)
        return True
    except json.JSONDecodeError as e:
        print(f"\nError: Invalid JSON format")
        print(f"Error details: {str(e)}")
        return False

if __name__ == '__main__':
    print("Paste your token string (Ctrl+D or Ctrl+Z when done):")
    token_str = sys.stdin.read().strip()
    format_token(token_str) 