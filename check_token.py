import pickle
import json
from datetime import datetime
import logging
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_pickle_token():
    """Check token.pickle file"""
    try:
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            print("\nToken.pickle Information:")
            print("-----------------------")
            print(f"Token Valid: {creds.valid}")
            print(f"Token Expired: {creds.expired}")
            print(f"Has Refresh Token: {'Yes' if creds.refresh_token else 'No'}")
            if hasattr(creds, 'expiry'):
                print(f"Expiry: {creds.expiry}")
            print("-----------------------")
            return True
    except FileNotFoundError:
        print("token.pickle file not found")
        return False
    except Exception as e:
        print(f"Error reading token.pickle: {e}")
        return False

def check_json_token():
    """Check token.json file"""
    try:
        with open('token.json', 'r') as token_file:
            token_data = json.load(token_file)
            
            # Create credentials object to check validity
            creds = Credentials.from_authorized_user_info(token_data, ['https://www.googleapis.com/auth/tasks'])
            
            print("\nToken.json Information:")
            print("---------------------")
            print(f"Token Valid: {creds.valid}")
            print(f"Token Expired: {creds.expired}")
            print(f"Has Refresh Token: {'Yes' if creds.refresh_token else 'No'}")
            
            if 'expiry' in token_data:
                expiry = datetime.strptime(token_data['expiry'], '%Y-%m-%dT%H:%M:%S.%fZ')
                print(f"Expiry: {expiry}")
                
                # Calculate time until expiry
                time_until_expiry = expiry - datetime.utcnow()
                if time_until_expiry.total_seconds() > 0:
                    print(f"Time until expiry: {time_until_expiry}")
                else:
                    print("Token has expired")
            
            print("---------------------")
            return True
    except FileNotFoundError:
        print("token.json file not found")
        return False
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in token.json: {e}")
        return False
    except Exception as e:
        print(f"Error reading token.json: {e}")
        return False

def check_token():
    """Check both token formats and provide status information"""
    print("Checking token files...")
    
    pickle_exists = check_pickle_token()
    json_exists = check_json_token()
    
    if not pickle_exists and not json_exists:
        print("\n⚠️  No token files found. Please run get_tasklist_id.py first.")
    elif pickle_exists and not json_exists:
        print("\n⚠️  Only token.pickle exists. You might want to run token_convert.py to create token.json")
    elif not pickle_exists and json_exists:
        print("\n✓ Using token.json for authentication")
    else:
        print("\n✓ Both token formats are available")

if __name__ == '__main__':
    check_token() 