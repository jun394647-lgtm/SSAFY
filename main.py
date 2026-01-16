import streamlit as st
import feedparser
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="투자자 뉴스 챗봇", layout="wide")

# --- 헬퍼 함수: RSS 뉴스 가져오기 ---
def fetch_rss_news(keyword):
    # Google News RSS (한글)
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]  # 최근 5개 기사만 반환

# --- 헬퍼 함수: Playwright 본문 크롤링 ---
async def scrape_article_content(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000)
            # 단순 예시로 p 태그 내용만 추출
            content = await page.locator("p").all_text_contents()
            await browser.close()
            return " ".join(content[:5]) + "..." # 일부만 반환
        except Exception as e:
            await browser.close()
            return f"크롤링 실패: {e}"

# --- 세션 상태 초기화 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scheduled_news" not in st.session_state:
    # 예시 데이터 (실제로는 DB/Supabase에서 불러옴)
    st.session_state.scheduled_news = {
        "반도체": [{"title": "삼성전자 실적 발표", "date": "2024-05-20", "summary": "내용 요약..."}, {"title": "SK하이닉스 HBM 공급", "date": "2024-05-21", "summary": "내용 요약..."}],
        "거시경제": [{"title": "금리 동결 결정", "date": "2024-05-21", "summary": "내용 요약..."}]
    }

# --- 사이드바 네비게이션 ---
page = st.sidebar.radio("메뉴 선택", ["메인 챗봇 (RSS 검색)", "테마별 뉴스 아카이브"])

# --- [페이지 1] 메인 챗봇 & RSS 검색 ---
if page == "메인 챗봇 (RSS 검색)":
    st.title("🤖 AI 투자 뉴스 챗봇")
    st.caption("기사 검색 의도를 판단하여 RSS 기반 뉴스를 요약해 드립니다.")

    # 대화 기록 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 채팅 입력
    if prompt := st.chat_input("관심 있는 종목이나 경제 키워드를 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 1. 의도 판단 (여기서는 단순 키워드 체크, 실제로는 LLM 활용)
        is_news_request = any(word in prompt for word in ["뉴스", "기사", "소식", "찾아줘"])

        with st.chat_message("assistant"):
            if is_news_request:
                st.write(f"🔍 '{prompt}' 관련 최신 뉴스를 RSS로 수집 중입니다...")
                news_items = fetch_rss_news(prompt)
                
                response_text = f"'{prompt}'에 대한 최신 뉴스입니다:\n\n"
                for item in news_items:
                    st.info(f"**[{item.title}]**\n\n링크: {item.link}")
                    # 여기서 선택적으로 Playwright 요약 호출 가능
                
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            else:
                response = "기사 검색이 아닌 일반 대화입니다. 무엇을 도와드릴까요?"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- [페이지 2] 테마별 뉴스 아카이브 ---
elif page == "테마별 뉴스 아카이브":
    st.title("📁 테마별 수집 뉴스")
    st.write("지정된 시간에 수집된 테마별 뉴스를 확인하세요.")

    selected_theme = st.selectbox("확인할 테마를 선택하세요", ["반도체", "거시경제", "이차전지", "정치"])

    if selected_theme in st.session_state.scheduled_news:
        articles = st.session_state.scheduled_news[selected_theme]
        
        # 카드 형태로 출력
        for article in articles:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(article["title"])
                    st.write(f"📅 수집일시: {article['date']}")
                    st.write(article["summary"])
                with col2:
                    if st.button("본문 보기", key=article["title"]):
                        st.write("상세 페이지로 이동 또는 팝업 표시")
    else:
        st.warning("해당 테마로 수집된 뉴스가 아직 없습니다.")

    st.divider()
    if st.button("지금 즉시 수집 (Playwright 작동 테스트)"):
        with st.spinner("Playwright 가동 중..."):
            test_url = "https://news.naver.com"
            content = asyncio.run(scrape_article_content(test_url))
            st.success("테스트 수집 완료")
            st.write(content)
