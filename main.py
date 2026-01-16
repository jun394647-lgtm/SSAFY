import streamlit as st
import requests
import feedparser
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# --- 1. 환경 설정 및 보안 ---
try:
    GMS_KEY = st.secrets["GMS_KEY"]
except KeyError:
    st.error("GMS_KEY가 설정되지 않았습니다. Secrets를 확인해주세요.")
    st.stop()

API_URL = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions"

# --- 2. API 호출 함수 (GMS 전용) ---
def call_gms_api(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GMS_KEY}"
    }
    payload = {
        "model": "gpt-5-nano",
        "messages": messages
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"API 호출 오류: {e}"

# --- 3. 뉴스 수집 및 크롤링 로직 ---
def fetch_rss_news(keyword):
    """Google News RSS 수집"""
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]

async def scrape_content(url):
    """Playwright를 이용한 본문 텍스트 추출"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return content[:1500] # 분석을 위한 선두 1500자
        except:
            await browser.close()
            return ""

# --- 4. 메인 UI 구성 ---
st.set_page_config(page_title="투자자 뉴스 통합 챗봇", layout="wide")

# 사이드바 페이지 전환
st.sidebar.title("🚀 투자 뉴스 센터")
menu = st.sidebar.radio("이동", ["메인: 뉴스 검색 챗봇", "아카이브: 테마별 뉴스"])

# --- [페이지 1] 메인 뉴스 챗봇 ---
if menu == "메인: 뉴스 검색 챗봇":
    st.title("🤖 AI 뉴스 검색 비서")
    st.info("뉴스 검색 요청 시 RSS 데이터를 가져와 gpt-5-nano가 요약해 드립니다.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 대화 내용 표시
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("메시지를 입력하세요 (예: 최근 삼성전자 뉴스 요약해줘)"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 1단계: LLM을 이용한 의도 파악 (프롬프트 엔지니어링)
        intent_check_messages = [
            {"role": "developer", "content": "사용자 입력이 뉴스/기사 검색 요청인지 판단하여 'NEWS' 또는 'GENERAL'로만 답하세요."},
            {"role": "user", "content": prompt}
        ]
        intent = call_gms_api(intent_check_messages).strip()

        with st.chat_message("assistant"):
            if "NEWS" in intent:
                st.write("🔍 최신 뉴스를 검색하고 있습니다...")
                news_items = fetch_rss_news(prompt)
                
                if news_items:
                    articles_summary = ""
                    for i, item in enumerate(news_items):
                        articles_summary += f"{i+1}. {item.title} (출처: {item.source.get('title')})\n"
                    
                    # 2단계: 수집된 뉴스를 바탕으로 최종 응답 생성
                    summarize_messages = [
                        {"role": "developer", "content": "제공된 뉴스 목록을 바탕으로 투자자에게 도움이 되도록 요약하고 한국어로 답변하세요."},
                        {"role": "user", "content": f"검색된 뉴스들:\n{articles_summary}\n\n이 뉴스들을 요약해줘."}
                    ]
                    final_response = call_gms_api(summarize_messages)
                    
                    # 뉴스 카드 표시
                    for item in news_items:
                        with st.expander(f"📰 {item.title}"):
                            st.write(f"날짜: {item.published}")
                            st.write(f"[기사 원문 보기]({item.link})")
                    
                    st.markdown(final_response)
                    st.session_state.chat_history.append({"role": "assistant", "content": final_response})
                else:
                    st.write("관련 뉴스를 찾을 수 없습니다.")
            else:
                # 일반 챗봇 응답
                gen_messages = [
                    {"role": "developer", "content": "투자 전문가로서 한국어로 친절하게 답변하세요."},
                    {"role": "user", "content": prompt}
                ]
                response = call_gms_api(gen_messages)
                st.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

# --- [페이지 2] 테마별 뉴스 아카이브 ---
elif menu == "아카이브: 테마별 뉴스":
    st.title("📁 테마별 수집 데이터")
    
    selected_theme = st.selectbox("리뷰할 테마를 선택하세요", ["반도체", "정치", "경제", "과학/기술"])
    
    st.subheader(f"📍 {selected_theme} 관련 자동 수집 결과")
    
    # 실제 구현 시에는 DB(Supabase)나 Notion에서 데이터를 쿼리해오는 코드가 들어갑니다.
    # 현재는 UI 레이아웃 예시를 보여줍니다.
    cols = st.columns(2)
    for i in range(4):
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"### {selected_theme} 테마 주요 기사 #{i+1}")
                st.caption(f"수집 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                st.write("이 영역에는 지정된 시간에 수집되어 Notion/Supabase에 저장된 요약본이 표시됩니다.")
                st.button("상세 분석 보기", key=f"btn_{i}")
