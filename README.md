# 📈 투자자용 AI 뉴스 챗봇

Streamlit 기반 뉴스 수집 및 분석 챗봇 애플리케이션

## 기능
- 💬 AI 챗봇 대화
- 📰 카테고리별 뉴스 수집 (경제, 정치, 과학, 기술)
- 💾 Notion 데이터베이스 자동 저장
- ⏰ 특정 시간 자동 기사 수집
- ⭐ 기사 저장 및 관리

## 설치 및 실행

### 로컬 실행
```bash
# 1. 저장소 클론
git clone <repository-url>
cd PJH_1555934

# 2. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. .env 파일 생성
echo "NOTION_API_KEY=your_key_here" > .env
echo "NOTION_DATABASE_ID=your_id_here" >> .env

# 5. 실행
streamlit run chatbot_app.py
