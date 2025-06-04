# Notion-Google Tasks Sync

Notion 데이터베이스와 Google Tasks를 자동으로 동기화하는 프로그램입니다.

## 기능

- Notion 데이터베이스의 작업을 Google Tasks에 동기화
- Google Tasks의 완료 상태를 Notion에 자동 반영
- 10분마다 자동 동기화 (GitHub Actions 사용)

## 설정 방법

1. GitHub Secrets 설정
   - `NOTION_TOKEN`: Notion API 토큰
   - `NOTION_DATABASE_ID`: Notion 데이터베이스 ID
   - `GOOGLE_CREDENTIALS`: Google Cloud 프로젝트의 credentials.json 파일 내용
   - `GOOGLE_TASKLIST_ID`: Google Tasks의 태스크 리스트 ID

2. Notion 데이터베이스 구조
   - 이름(Title): 작업 제목
   - 날짜(Date): 작업 마감일
   - remark(Rich text): Google Task ID 저장용
   - 습관명(Relation): 습관 연결
   - 완료여부(Checkbox): 작업 완료 상태
   - google 업로드(Select): 동기화 상태

## 사용 방법

1. 이 저장소를 Fork합니다.
2. GitHub Secrets에 필요한 값들을 설정합니다.
3. GitHub Actions가 자동으로 10분마다 동기화를 수행합니다.
4. 수동으로 동기화하려면 Actions 탭에서 "Notion-Google Tasks Sync" 워크플로우를 실행하면 됩니다.

## 주의사항

- Google Cloud Console에서 Tasks API를 활성화해야 합니다.
- Notion API 토큰은 데이터베이스에 대한 접근 권한이 있어야 합니다.
- credentials.json의 내용은 JSON 형식을 유지한 채로 GitHub Secrets에 저장해야 합니다. 