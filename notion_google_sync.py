import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set
from dotenv import load_dotenv
from notion_client import Client
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import telegram
from telegram.ext import Updater

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
GOOGLE_TASKLIST_ID = os.getenv('GOOGLE_TASKLIST_ID')
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

def should_refresh_token() -> bool:
    """토큰을 갱신해야 하는지 확인합니다."""
    try:
        # token_refresh.json 파일에서 마지막 갱신 시간을 확인
        if os.path.exists('token_refresh.json'):
            with open('token_refresh.json', 'r') as f:
                data = json.load(f)
                last_refresh = datetime.fromisoformat(data['last_refresh'])
                # 마지막 갱신으로부터 24시간이 지났는지 확인
                return datetime.now() - last_refresh > timedelta(hours=24)
        return True  # 파일이 없으면 갱신 필요
    except Exception as e:
        logger.error(f"토큰 갱신 시간 확인 중 오류 발생: {str(e)}")
        return True  # 오류 발생 시 안전하게 갱신 진행

def update_refresh_time():
    """토큰 갱신 시간을 업데이트합니다."""
    try:
        with open('token_refresh.json', 'w') as f:
            json.dump({
                'last_refresh': datetime.now().isoformat()
            }, f)
    except Exception as e:
        logger.error(f"토큰 갱신 시간 업데이트 중 오류 발생: {str(e)}")

def get_google_credentials():
    """Google OAuth 인증 정보를 가져옵니다."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/tasks'])
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            error_msg = "토큰이 만료되었습니다. 자동 갱신을 기다리거나 수동으로 갱신해주세요."
            logger.error(error_msg)
            send_telegram_message(f"⚠️ <b>Google 토큰 만료</b>\n\n{error_msg}")
            raise Exception(error_msg)
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', ['https://www.googleapis.com/auth/tasks'])
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    
    return creds

class NotionGoogleTasksSync:
    def __init__(self):
        # Notion 클라이언트 초기화
        self.notion = Client(auth=NOTION_TOKEN)
        self.database_id = NOTION_DATABASE_ID
        
        # Google Tasks 클라이언트 초기화
        self.tasks_service = self._initialize_google_tasks()
        self.tasklist_id = self._get_default_tasklist_id()

    def _initialize_google_tasks(self) -> any:
        """Google Tasks API 인증 및 서비스 객체 생성"""
        creds = get_google_credentials()
        return build('tasks', 'v1', credentials=creds)

    def _get_default_tasklist_id(self) -> str:
        """기본 태스크 리스트 ID 가져오기"""
        # 환경 변수에서 태스크 리스트 ID를 가져오기 시도
        tasklist_id = GOOGLE_TASKLIST_ID
        if tasklist_id:
            return tasklist_id

        # 환경 변수에 없다면 사용자의 태스크 리스트를 가져와서 '습관' 리스트 찾기
        try:
            results = self.tasks_service.tasklists().list().execute()
            tasklists = results.get('items', [])

            if not tasklists:
                print("태스크 리스트를 찾을 수 없습니다. 새로운 리스트를 생성합니다.")
                new_list = self.tasks_service.tasklists().insert(body={
                    'title': '습관'
                }).execute()
                return new_list['id']
            
            # 모든 태스크 리스트 출력
            print("\n사용 가능한 태스크 리스트:")
            for i, tasklist in enumerate(tasklists, 1):
                print(f"{i}. {tasklist['title']} (ID: {tasklist['id']})")
            
            # '습관' 리스트 찾기
            habit_list = next((tasklist for tasklist in tasklists if tasklist['title'] == '습관'), None)
            
            if habit_list:
                print(f"\n'습관' 태스크 리스트를 사용합니다.")
                return habit_list['id']
            else:
                print("\n'습관' 태스크 리스트를 찾을 수 없어 새로 생성합니다.")
                new_list = self.tasks_service.tasklists().insert(body={
                    'title': '습관'
                }).execute()
                return new_list['id']
            
        except Exception as e:
            print(f"태스크 리스트를 가져오는 중 오류 발생: {e}")
            raise

    def get_notion_tasks(self) -> List[Dict]:
        """Notion 데이터베이스에서 작업 목록 가져오기"""
        response = self.notion.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {
                        "property": "google 업로드",
                        "select": {
                            "does_not_equal": "완료"
                        }
                    }
                ]
            }
        )
        return response['results']

    def create_google_task(self, notion_task: Dict) -> str:
        """Notion 작업을 Google Tasks에 추가"""
        # 이름 필드에서 제목 가져오기
        title = notion_task['properties']['이름']['title']
        task = {
            'title': title[0]['text']['content'] if title else '제목 없음',
            'notes': f"Notion Task ID: {notion_task['id']}",  # Notion ID를 명확한 형식으로 저장
            'status': 'needsAction'
        }
        
        # 날짜 필드에서 마감일 가져오기
        if notion_task['properties'].get('날짜') and \
           notion_task['properties']['날짜']['date']:
            due_date = notion_task['properties']['날짜']['date']['start']
            task['due'] = f"{due_date}T00:00:00.000Z"

        result = self.tasks_service.tasks().insert(
            tasklist=self.tasklist_id,
            body=task
        ).execute()

        # Google Task ID를 Notion의 remark 필드에 저장
        self.notion.pages.update(
            page_id=notion_task['id'],
            properties={
                "remark": {
                    "rich_text": [
                        {
                            "text": {
                                "content": f"Google Task ID: {result['id']}"
                            }
                        }
                    ]
                }
            }
        )
        
        return result['id']

    def update_notion_task_sync_status(self, task_id: str, google_task_id: str):
        """Notion 작업의 동기화 상태 업데이트"""
        self.notion.pages.update(
            page_id=task_id,
            properties={
                "google 업로드": {"select": {"name": "완료"}}
            }
        )

    def check_completed_google_tasks(self):
        """완료된 Google Tasks 확인 및 Notion 업데이트"""
        print("\nGoogle Tasks의 완료된 작업을 확인합니다...")
        try:
            tasks = self.tasks_service.tasks().list(
                tasklist=self.tasklist_id,
                showCompleted=True,
                showHidden=True,  # 숨겨진 작업도 포함
                maxResults=100
            ).execute()
            
            print(f"가져온 전체 작업 수: {len(tasks.get('items', []))}")
            
            completed_count = 0
            for task in tasks.get('items', []):
                status = task.get('status', '')
                title = task.get('title', '')
                completed = task.get('completed')
                
                print(f"• 작업: '{title}' (상태: {status}, 완료일: {completed})")
                
                if status == 'completed' or completed:
                    print(f"  - 완료된 작업 발견")
                    # Notion Task ID 추출 시도
                    notes = task.get('notes', '')
                    notion_id = None
                    
                    # 1. notes에서 Notion ID 찾기
                    if 'Notion Task ID:' in notes:
                        notion_id = notes.split('Notion Task ID:')[1].strip().split('\n')[0]
                        print(f"  - Notion ID 찾음: {notion_id}")
                    
                    if notion_id:
                        try:
                            # Notion 작업 완료 상태로 업데이트
                            self.notion.pages.update(
                                page_id=notion_id,
                                properties={
                                    "완료여부": {"checkbox": True}
                                }
                            )
                            completed_count += 1
                            print(f"  - Notion 작업 완료 상태로 업데이트 성공")
                        except Exception as e:
                            print(f"  - Notion ID로 업데이트 실패: {str(e)}")
                            # 2. Google Task ID로 Notion 작업 찾기 시도
                            try:
                                notion_tasks = self.notion.databases.query(
                                    database_id=self.database_id,
                                    filter={
                                        "property": "remark",
                                        "rich_text": {
                                            "contains": f"Google Task ID: {task['id']}"
                                        }
                                    }
                                ).get('results', [])
                                
                                if notion_tasks:
                                    notion_task = notion_tasks[0]
                                    self.notion.pages.update(
                                        page_id=notion_task['id'],
                                        properties={
                                            "완료여부": {"checkbox": True}
                                        }
                                    )
                                    completed_count += 1
                                    print(f"  - Google Task ID로 Notion 작업 찾아서 업데이트 성공")
                                else:
                                    print(f"  - Google Task ID로도 Notion 작업을 찾을 수 없음")
                            except Exception as e2:
                                print(f"  - Google Task ID로도 업데이트 실패: {str(e2)}")
                    else:
                        print(f"  - Notion ID를 찾을 수 없음")
            
            if completed_count > 0:
                print(f"\n총 {completed_count}개의 작업 완료 상태를 Notion에 반영했습니다.")
            else:
                print("\n완료 상태를 반영한 작업이 없습니다.")
        except Exception as e:
            print(f"Google Tasks 가져오기 실패: {str(e)}")

    def get_all_notion_tasks(self) -> List[Dict]:
        """Notion 데이터베이스에서 모든 작업 목록 가져오기"""
        response = self.notion.databases.query(
            database_id=self.database_id
        )
        return response['results']

    def get_all_google_tasks(self) -> List[Dict]:
        """Google Tasks에서 모든 작업 가져오기 (완료된 작업 포함)"""
        try:
            tasks = self.tasks_service.tasks().list(
                tasklist=self.tasklist_id,
                showCompleted=True,
                showHidden=True,
                maxResults=100
            ).execute()
            return tasks.get('items', [])
        except HttpError as e:
            print(f"Google Tasks를 가져오는 중 오류 발생: {e}")
            return []

    def validate_task_sync(self):
        """작업 동기화 상태 검증"""
        print("\n작업 동기화 상태를 검증합니다...")
        
        # 모든 Notion 작업과 Google Tasks 가져오기
        notion_tasks = self.get_all_notion_tasks()
        google_tasks = self.get_all_google_tasks()
        
        # Google Tasks ID와 Notion ID 매핑 생성
        google_task_map = {}  # Notion Task ID -> Google Task
        
        # Google Tasks 매핑
        for task in google_tasks:
            notes = task.get('notes', '')
            if 'Notion Task ID:' in notes:
                notion_id = notes.split('Notion Task ID:')[1].strip().split('\n')[0]
                google_task_map[notion_id] = task
        
        # 검증 및 수정
        for task in notion_tasks:
            notion_id = task['id']
            if task['properties'].get('google 업로드') and \
               task['properties']['google 업로드']['select'] and \
               task['properties']['google 업로드']['select']['name'] == "완료":
                
                # Google Task가 존재하지 않는 경우
                if notion_id not in google_task_map:
                    # remark 필드에서 Google Task ID 찾기
                    remark = task['properties'].get('remark', {}).get('rich_text', [])
                    google_task_id = None
                    if remark and 'Google Task ID:' in remark[0]['text']['content']:
                        google_task_id = remark[0]['text']['content'].split('Google Task ID:')[1].strip()
                    
                    if google_task_id:
                        # Google Task ID로 작업 찾기
                        matching_tasks = [t for t in google_tasks if t['id'] == google_task_id]
                        if matching_tasks:
                            # 연결 정보 복구
                            self.tasks_service.tasks().update(
                                tasklist=self.tasklist_id,
                                task=google_task_id,
                                body={
                                    'notes': f"Notion Task ID: {notion_id}"
                                }
                            ).execute()
                            print(f"  • '{task['properties']['이름']['title'][0]['text']['content']}' 연결 정보를 복구했습니다.")
                            continue
                    
                    title = task['properties']['이름']['title'][0]['text']['content']
                    print(f"경고: Notion 작업 '{title}'의 Google Task가 존재하지 않습니다.")
                    # google 업로드 상태 초기화
                    self.notion.pages.update(
                        page_id=notion_id,
                        properties={
                            "google 업로드": {"select": None}
                        }
                    )
                    print("→ Notion의 업로드 상태를 초기화했습니다.")

    def get_existing_task_names(self) -> Set[str]:
        """Google Tasks에 있는 모든 작업 이름 가져오기"""
        try:
            tasks = self.tasks_service.tasks().list(
                tasklist=self.tasklist_id,
                showCompleted=True,
                showHidden=True,
                maxResults=100
            ).execute()
            
            return {task['title'] for task in tasks.get('items', [])}
        except HttpError as e:
            print(f"Google Tasks 목록을 가져오는 중 오류 발생: {e}")
            return set()

    def sync_tasks(self):
        """작업 동기화 실행"""
        print("Notion 작업을 Google Tasks와 동기화합니다...")
        
        # 0. 기존 동기화 상태 검증
        self.validate_task_sync()
        
        # 1. Google Tasks의 기존 작업 이름 가져오기
        existing_task_names = self.get_existing_task_names()
        
        # 2. 노션에서 동기화되지 않은 작업 가져오기
        notion_tasks = self.get_notion_tasks()
        new_tasks = []
        skipped_tasks = []
        
        # 3. 중복 작업 필터링
        for task in notion_tasks:
            title = task['properties']['이름']['title']
            task_name = title[0]['text']['content'] if title else '제목 없음'
            
            if task_name in existing_task_names:
                skipped_tasks.append(task_name)
            else:
                new_tasks.append(task)
        
        print(f"\n동기화되지 않은 작업 {len(notion_tasks)}개 중:")
        if skipped_tasks:
            print(f"- {len(skipped_tasks)}개 작업이 이미 존재하여 건너뜁니다:")
            for task_name in skipped_tasks:
                print(f"  • {task_name}")
        
        if new_tasks:
            print(f"- {len(new_tasks)}개 작업을 동기화합니다:")
            # 4. 새로운 작업만 Google Tasks에 추가
            for task in new_tasks:
                title = task['properties']['이름']['title']
                task_name = title[0]['text']['content'] if title else '제목 없음'
                print(f"  • '{task_name}' 동기화 중...")
                google_task_id = self.create_google_task(task)
                self.update_notion_task_sync_status(task['id'], google_task_id)
        else:
            print("- 동기화할 새로운 작업이 없습니다.")
        
        # 5. 완료된 Google Tasks 확인 및 Notion 업데이트
        print("\nGoogle Tasks의 완료된 작업을 Notion에 반영합니다...")
        self.check_completed_google_tasks()
        
        print("동기화가 완료되었습니다!")

def main():
    """메인 동기화 함수"""
    start_time = datetime.now()
    sync_results = {
        'success': True,
        'tasks_synced': 0,
        'tasks_completed': 0,
        'errors': []
    }

    try:
        sync = NotionGoogleTasksSync()
        sync.sync_tasks()

        # 실행 결과 메시지 생성
        duration = datetime.now() - start_time
        message = f"🔄 <b>Notion-Google Tasks 동기화 완료</b>\n\n"
        message += f"⏱ 실행 시간: {duration.total_seconds():.1f}초\n"
        message += f"📋 동기화된 작업: {sync_results['tasks_synced']}개\n"
        message += f"✅ 완료된 작업: {sync_results['tasks_completed']}개\n"
        
        if sync_results['errors']:
            message += "\n⚠️ <b>오류 발생</b>\n"
            for error in sync_results['errors']:
                message += f"- {error}\n"

        # 텔레그램으로 결과 전송
        send_telegram_message(message)

    except Exception as e:
        error_message = f"❌ <b>동기화 중 오류 발생</b>\n\n{str(e)}"
        send_telegram_message(error_message)
        logger.error(f"동기화 실패: {str(e)}")
        raise

if __name__ == '__main__':
    main() 