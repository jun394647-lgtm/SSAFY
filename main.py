import streamlit as st
import feedparser
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
import openai # 혹은 사용하시는 LLM 라이브러리

# --- 1. 보안 설정 (Secrets 호출) ---
# secrets에 값이 없을 경우를 대비한 예외 처리
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    # NOTION_TOKEN = st.secrets["NOTION_TOKEN"] # 필요 시 활성화
except KeyError:
    st.error("Secrets 설정이 누락되었습니다. .streamlit/secrets.toml 파일을 확인하세요.")
    st.stop()

# --- 페이지 설정 ---
st.set_page_config(page_title="Investor News Bot", layout="wide")

# --- 2. 뉴스 수집 및 처리 로직 ---

def fetch_rss_news(keyword):
    """RSS를 통한 기사 검색"""
    rss_url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(rss_url)
    return feed.entries[:5]

async def scrape_full_text(url):
    """Playwright를 이용한 본문 크롤링"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            # 투자자에게 필요한 본문 텍스트 추출 (사이트별로 선택자 조정 가능)
            content = await page.evaluate("() => document.body.innerText")
            await browser.close()
            return content[:1000] # 분석을 위해 앞부분 1000자만 반환
        except Exception:
            await browser.close()
            return "본문을 가져올 수 없습니다."

def analyze_intent(user_input):
    """LLM을 이용한 뉴스 검색 의도 파악 (프롬프트 엔지니어링)"""
    # 실제 구현 시 OpenAI API 등을 호출합니다.
    # 여기서는 간단한 로직으로 대체하지만, 실제로는 st.secrets를 사용한 API 호출이 들어갑니다.
    keywords = ["뉴스", "기사", "소식", "검색", "찾아줘"]
    return any(word in user_input for word in keywords)

# --- 3. UI 구성 ---

st.sidebar.title("📈 투자자 뉴스 센터")
page = st.sidebar.radio("이동하기", ["메인: AI 뉴스 챗봇", "아카이브: 테마별 뉴스"])

# --- [페이지 1] 메인 챗봇 ---
if page == "메인: AI 뉴스 챗봇":
    st.title("🤖 뉴스 검색 & 요약 챗봇")
    st.info("투자 키워드를 입력하면 RSS를 통해 뉴스를 찾아 요약해 드립니다.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("예: 삼성전자 최신 뉴스 보여줘"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # 의도 판단
            if analyze_intent(prompt):
                st.write(f"🔍 '{prompt}' 관련 뉴스를 검색합니다...")
                news_items = fetch_rss_news(prompt)
                
                if news_items:
                    response_md = ""
                    for item in news_items:
                        with st.expander(f"📰 {item.title}"):
                            st.write(f"출처: {item.source.get('title', '알 수 없음')} | 날짜: {item.published}")
                            st.write(f"[원문 링크]({item.link})")
                            # 필요 시 버튼 클릭으로 Playwright 실행 가능
                            if st.button("AI 상세 요약 생성", key=item.link):
                                full_text = asyncio.run(scrape_full_text(item.link))
                                st.write("**본문 요약 중...**")
                                st.write(full_text[:300] + "...") # 예시 출력
                        response_md += f"- {item.title}\n"
                    st.session_state.messages.append({"role": "assistant", "content": f"검색 결과입니다:\n{response_md}"})
                else:
                    st.write("검색 결과가 없습니다.")
            else:
                response = "일반 대화 모드입니다. 투자 뉴스에 대해 물어봐주세요!"
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

# --- [페이지 2] 테마별 뉴스 ---
elif page == "아카이브: 테마별 뉴스":
    st.title("📁 테마별 맞춤 기사 리스트")
    
    themes = ["반도체", "2차전지", "매크로 경제", "미국 증시"]
    selected_theme = st.selectbox("관심 테마를 선택하세요", themes)
    
    st.subheader(f"📍 {selected_theme} 테마 수집 현황")
    
    # 이 부분은 실제 Supabase나 Notion DB에서 불러오는 로직으로 대체됩니다.
    st.write(f"최근 수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%00')}")
    
    # 가상의 데이터 그리드 (st.dataframe 또는 카드 UI)
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.write("**뉴스 제목 샘플**")
            st.caption("2024-05-22")
            st.write("이 기사는 해당 테마의 주요 변곡점을 다루고 있습니다.")
            st.link_button("Notion에서 보기", "https://notion.so")
    with col2:
         with st.container(border=True):
            st.write("**뉴스 제목 샘플 2**")
            st.caption("2024-05-22")
            st.write("시장 컨센서스를 상회하는 실적 발표 관련 뉴스입니다.")
            st.link_button("원문 확인", "https://news.naver.com")
