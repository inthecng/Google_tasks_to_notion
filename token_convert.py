import pickle
import json

def convert_token():
    try:
        # Read the pickle file
        with open('token.pickle', 'rb') as token_file:
            creds = pickle.load(token_file)
        
        # Convert to JSON and save
        with open('token.json', 'w') as json_file:
            json_file.write(creds.to_json())
        
        print("Successfully converted token.pickle to token.json")
        
        # Print the JSON content so you can update your GitHub secret
        with open('token.json', 'r') as json_file:
            print("\nToken JSON content (use this to update your GitHub secret):")
            print(json_file.read())
            
    except Exception as e:
        print(f"Error converting token: {e}")

if __name__ == '__main__':
    convert_token() 