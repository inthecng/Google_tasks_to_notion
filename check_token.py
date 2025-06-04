import pickle
from pprint import pprint

def check_token():
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            print("\nToken Information:")
            print("-----------------")
            print(f"Token Valid: {creds.valid}")
            print(f"Token Expired: {creds.expired}")
            print(f"Refresh Token: {creds.refresh_token}")
            print("-----------------")
    except FileNotFoundError:
        print("token.pickle file not found. Please run get_tasklist_id.py first.")
    except Exception as e:
        print(f"Error reading token: {e}")

if __name__ == '__main__':
    check_token() 