import os
import json
import time
import logging
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import telegram

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram_message(message):
    """텔레그램으로 메시지를 전송합니다."""
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 실패: {str(e)}")

def load_token():
    """Load the current token from token.json file"""
    try:
        with open('token.json', 'r') as token_file:
            return json.load(token_file)
    except FileNotFoundError:
        logger.error("token.json file not found")
        return None
    except json.JSONDecodeError:
        logger.error("Invalid JSON in token.json")
        return None

def save_token(token_data):
    """Save the token data to token.json file"""
    try:
        with open('token.json', 'w') as token_file:
            json.dump(token_data, token_file, indent=2)
        logger.info("Token successfully saved")
    except Exception as e:
        logger.error(f"Error saving token: {e}")

def is_token_expired(token_data):
    """Check if the token is expired or about to expire"""
    if not token_data or 'expiry' not in token_data:
        return True
    
    # Add 5 minutes buffer before actual expiration
    buffer_time = 300  # 5 minutes in seconds
    expiry_timestamp = time.mktime(time.strptime(token_data['expiry'], '%Y-%m-%dT%H:%M:%S.%fZ'))
    
    return time.time() + buffer_time >= expiry_timestamp

def refresh_token():
    """Refresh the Google Tasks API token"""
    try:
        # Load existing token
        token_data = load_token()
        if not token_data:
            logger.error("No token data available to refresh")
            return False

        # Create credentials object
        creds = Credentials.from_authorized_user_info(token_data, ['https://www.googleapis.com/auth/tasks'])

        # Check if token needs refresh
        if is_token_expired(token_data) and creds.refresh_token:
            logger.info("Token expired, attempting refresh...")
            
            # Perform token refresh
            creds.refresh(None)
            
            # Save the refreshed token
            token_info = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() + 'Z'
            }
            save_token(token_info)
            logger.info("Token successfully refreshed")
            send_telegram_message("🔄 <b>Google 토큰이 갱신되었습니다.</b>")
            return True
        
        logger.info("Token is still valid, no refresh needed")
        send_telegram_message("ℹ️ <b>Google 토큰이 아직 유효합니다.</b>")
        return True

    except Exception as e:
        logger.error(f"토큰 갱신 중 오류 발생: {str(e)}")
        send_telegram_message(f"⚠️ <b>Google 토큰 갱신 실패</b>\n\n오류: {str(e)}")
        return False

if __name__ == '__main__':
    refresh_token() 