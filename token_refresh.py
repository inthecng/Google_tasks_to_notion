import os
import logging
from datetime import datetime
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

def refresh_token():
    """Google OAuth 토큰을 갱신합니다."""
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/tasks'])

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # 갱신된 토큰 저장
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Google 토큰이 성공적으로 갱신되었습니다.")
                    send_telegram_message("🔄 <b>Google 토큰이 갱신되었습니다.</b>")
                except Exception as e:
                    error_msg = f"토큰 갱신 실패: {str(e)}"
                    logger.error(error_msg)
                    send_telegram_message(f"⚠️ <b>Google 토큰 갱신 실패</b>\n\n오류: {str(e)}")
                    raise Exception(error_msg)
            else:
                error_msg = "토큰이 만료되었고 refresh token이 없습니다. 수동으로 재인증이 필요합니다."
                logger.error(error_msg)
                send_telegram_message(f"⚠️ <b>Google 토큰 갱신 실패</b>\n\n{error_msg}")
                raise Exception(error_msg)
        else:
            logger.info("토큰이 아직 유효합니다.")
            send_telegram_message("ℹ️ <b>Google 토큰이 아직 유효합니다.</b>")

    except Exception as e:
        logger.error(f"토큰 갱신 중 오류 발생: {str(e)}")
        raise

if __name__ == '__main__':
    refresh_token() 