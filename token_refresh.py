import os
import json
import logging
import asyncio
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import telegram

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-1002695323680"  # 채널 ID

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

async def send_telegram_message(message):
    """텔레그램으로 메시지를 전송합니다."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot token not found. Skipping notification.")
        return

    try:
        async with telegram.Bot(token=TELEGRAM_BOT_TOKEN) as bot:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            logger.info("Telegram notification sent successfully")
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 실패: {str(e)}")

async def refresh_token():
    """Google Tasks API 토큰을 강제로 리프레시합니다."""
    try:
        token_data = load_token()
        if not token_data:
            logger.error("No token data available to refresh")
            await send_telegram_message("⚠️ <b>토큰 데이터를 찾을 수 없습니다.</b>")
            return False

        creds = Credentials.from_authorized_user_info(token_data, ['https://www.googleapis.com/auth/tasks'])
        
        if creds.refresh_token:
            try:
                creds.refresh(Request())
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
                await send_telegram_message("🔄 <b>Google 토큰이 갱신되었습니다.</b>\n\n다음 만료 시간: " + token_info['expiry'])
                return True
            except Exception as refresh_error:
                error_message = f"토큰 갱신 중 오류 발생: {str(refresh_error)}"
                logger.error(error_message)
                await send_telegram_message(f"⚠️ <b>토큰 갱신 실패</b>\n\n{error_message}")
                return False
        else:
            error_message = "리프레시 토큰이 없습니다. 재인증이 필요합니다."
            logger.error(error_message)
            await send_telegram_message(f"⚠️ <b>토큰 갱신 실패</b>\n\n{error_message}")
            return False

    except Exception as e:
        error_message = f"토큰 처리 중 예상치 못한 오류 발생: {str(e)}"
        logger.error(error_message)
        await send_telegram_message(f"⚠️ <b>오류 발생</b>\n\n{error_message}")
        return False

if __name__ == '__main__':
    try:
        asyncio.run(refresh_token())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}") 