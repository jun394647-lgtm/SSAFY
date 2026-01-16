import streamlit as st
import requests
import feedparser
from supabase import create_client, Client
from datetime import datetime

# --- 1. 보안 및 클라이언트 설정 ---
try:
    GMS_KEY = st.secrets["GMS_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    NOTION_DATABASE_ID = st.secrets["NOTION_DATABASE_ID"]
    
    # Supabase 클라이언트 초기화
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except KeyError as e:
    st.error(f"Secrets 설정이 누락되었습니다: {e}")
    st.stop()

API_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions"

# --- 2. 핵심 로직 함수 ---

def call_gms_api(messages):
    """GPT-5-Nano 호출"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GMS_KEY}"}
    payload = {"model": "gpt-5-nano", "messages": messages}
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']

def save_to_supabase(title, content, link, theme):
    """Supabase DB에 뉴스 저장"""
    data = {
        "title": title,
        "content": content,
        "link": link,
        "theme": theme,
        "created_at": datetime.now().isoformat()
    }
    return supabase.table("news_articles").insert(data).execute()

def send_to_notion(title, summary, link):
    """Notion 데이터베이스로 페이지 전송"""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "제목": {"title": [{"text": {"content": title}}]},
            "링크": {"url": link},
            "요약": {"rich_text": [{"text": {"content": summary}}]}
        }
    }
    return requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload)

# --- 3. UI 구성 ---
st.set_page_config(page_title="투자 뉴스 통합 관리", layout="wide")
st.sidebar.title("📈 투자 시스템")
menu = st.sidebar.radio("이동", ["AI 뉴스 챗봇", "테마별 아카이브"])

# --- [페이지 1] AI 뉴스 챗봇 ---
if menu == "AI 뉴스 챗봇":
    st.title("🤖 뉴스 검색 및 자동 저장")
    
    if prompt := st.chat_input("관심 키워드를 입력하세요"):
        with st.chat_message("user"): st.markdown(prompt)

        # 1. 의도 파악 및 뉴스 수집 (이전 로직 동일)
        # ... (중략: RSS 수집 로직) ...
        news_items = feedparser.parse(f"https://news.google.com/rss/search?q={prompt}&hl=ko&gl=KR&ceid=KR:ko").entries[:3]

        for item in news_items:
            with st.expander(f"📰 {item.title}"):
                st.write(f"[원문 링크]({item.link})")
                
                # 테마 선택 및 저장 버튼
                col1, col2 = st.columns(2)
                theme = col1.selectbox("테마 분류", ["반도체", "이차전지", "매크로", "정치"], key=item.link)
                
                if col2.button("데이터베이스 저장", key=f"save_{item.link}"):
                    # 요약 생성 후 저장
                    summary = call_gms_api([
                        {"role": "developer", "content": "3줄 요약 전문가"},
                        {"role": "user", "content": f"기사 제목: {item.title}\n이 내용을 요약해줘."}
                    ])
                    
                    # Supabase 저장
                    save_to_supabase(item.title, summary, item.link, theme)
                    # Notion 전송
                    send_to_notion(item.title, summary, item.link)
                    
                    st.success("✅ Supabase & Notion 저장 완료!")

# --- [페이지 2] 테마별 아카이브 ---
elif menu == "테마별 아카이브":
    st.title("📁 수집된 테마 뉴스")
    
    selected_theme = st.selectbox("조회할 테마", ["반도체", "이차전지", "매크로", "정치"])
    
    # Supabase에서 데이터 불러오기
    response = supabase.table("news_articles").select("*").eq("theme", selected_theme).order("created_at", desc=True).execute()
    articles = response.data

    if not articles:
        st.warning("저장된 뉴스가 없습니다.")
    else:
        for article in articles:
            with st.container(border=True):
                st.subheader(article['title'])
                st.caption(f"수집일: {article['created_at']}")
                st.write(article['content'])
                st.link_button("원문 읽기", article['link'])
