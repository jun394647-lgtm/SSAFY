import streamlit as st
from datetime import datetime
import feedparser
import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from notion_client import Client
import html
from email.utils import parsedate_to_datetime
from apscheduler.schedulers.background import BackgroundScheduler
import json

# .env 파일 로드
load_dotenv()

# Notion 클라이언트 초기화
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion_client = None
if NOTION_API_KEY:
    try:
        notion_client = Client(auth=NOTION_API_KEY)
    except Exception as e:
        st.warning(f"⚠️ Notion 연결 실패: {str(e)}")

# 페이지 설정
st.set_page_config(
    page_title="투자자용 뉴스 챗봇",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "saved_articles" not in st.session_state:
    st.session_state.saved_articles = []
if "category_articles" not in st.session_state:
    st.session_state.category_articles = {}
if "scheduled_time" not in st.session_state:
    st.session_state.scheduled_time = None
if "scheduled_categories" not in st.session_state:
    st.session_state.scheduled_categories = []

# 스타일링
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .category-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .economy { background-color: #FFE5CC; color: #8B4513; }
    .politics { background-color: #E5CCFF; color: #4B0082; }
    .science { background-color: #CCFFE5; color: #003300; }
    .tech { background-color: #CCE5FF; color: #000033; }
    .schedule-box {
        background-color: #E8F4F8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #0084D1;
    }
    .news-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .news-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
    }
    .news-card-title {
        font-size: 1.1rem;
        font-weight: bold;
        margin: 0.5rem 0;
        color: #1a1a1a;
    }
    .news-card-summary {
        font-size: 0.9rem;
        color: #555;
        margin: 0.5rem 0;
        line-height: 1.5;
    }
    .news-card-meta {
        font-size: 0.8rem;
        color: #999;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# RSS 피드 URL 정의
RSS_FEEDS = {
    "경제": [
        "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=투자&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "정치": [
        "https://news.google.com/rss/search?q=정치&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "과학": [
        "https://news.google.com/rss/search?q=과학&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "기술": [
        "https://news.google.com/rss/search?q=기술&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=AI&hl=ko&gl=KR&ceid=KR:ko",
    ]
}

# 스케줄 설정 파일
SCHEDULE_CONFIG_FILE = "schedule_config.json"

def load_schedule_config():
    """스케줄 설정 파일에서 로드"""
    try:
        if os.path.exists(SCHEDULE_CONFIG_FILE):
            with open(SCHEDULE_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"categories": [], "hour": 9, "minute": 0}

def save_schedule_config(categories, hour, minute):
    """스케줄 설정 파일에 저장"""
    try:
        config = {
            "categories": categories,
            "hour": hour,
            "minute": minute
        }
        with open(SCHEDULE_CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        return True
    except:
        return False

def clean_html(raw_html):
    """HTML 태그 제거"""
    if not raw_html:
        return ""
    cleanr = BeautifulSoup(raw_html, "html.parser")
    text = cleanr.get_text()
    text = html.unescape(text)
    return text.strip()

def parse_rss_date(date_string):
    """RSS 날짜를 ISO 8601 형식으로 변환"""
    if not date_string:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        dt = parsedate_to_datetime(date_string)
        return dt.strftime("%Y-%m-%d")
    except:
        try:
            return date_string[:10]
        except:
            return datetime.now().strftime("%Y-%m-%d")

def save_to_notion(article, summary):
    """Notion 데이터베이스에 기사 저장"""
    if not notion_client or not NOTION_DATABASE_ID:
        return False
    
    try:
        published_date = article.get("published", datetime.now().strftime("%Y-%m-%d"))
        if not isinstance(published_date, str) or len(published_date) < 10:
            published_date = datetime.now().strftime("%Y-%m-%d")
        else:
            published_date = published_date[:10]
        
        notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "제목": {
                    "title": [{"text": {"content": clean_html(article["title"])[:100]}}]
                },
                "카테고리": {
                    "select": {"name": article.get("category", "일반")}
                },
                "URL": {
                    "url": article["link"]
                },
                "요약": {
                    "rich_text": [{"text": {"content": summary[:2000]}}]
                },
                "날짜": {
                    "date": {"start": published_date}
                },
                "저장됨": {
                    "checkbox": True
                }
            }
        )
        return True
    except Exception as e:
        return False

def judge_search_intent(user_input):
    """사용자 입력이 기사 검색 요청인지 판단"""
    search_keywords = ["기사", "뉴스", "검색", "찾아", "알려", "최신", "동향", "트렌드"]
    input_lower = user_input.lower()
    return any(keyword in input_lower for keyword in search_keywords)

def fetch_articles_from_rss(category, limit=5):
    """RSS 피드에서 기사 수집"""
    articles = []
    if category not in RSS_FEEDS:
        return articles
    
    for feed_url in RSS_FEEDS[category]:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                raw_summary = entry.get("summary", "요약 없음")
                clean_summary = clean_html(raw_summary)
                published_date = parse_rss_date(entry.get("published", ""))
                
                article = {
                    "title": clean_html(entry.get("title", "제목 없음")),
                    "summary": clean_summary[:300],
                    "link": entry.get("link", "#"),
                    "published": published_date,
                    "category": category
                }
                articles.append(article)
        except Exception as e:
            continue
    
    return articles[:limit]

def auto_collect_articles():
    """자동으로 기사 수집 및 Notion 저장"""
    config = load_schedule_config()
    scheduled_categories = config.get("categories", [])
    
    if not scheduled_categories:
        return
    
    for category in scheduled_categories:
        try:
            articles = fetch_articles_from_rss(category, limit=3)
            for article in articles:
                save_to_notion(article, article["summary"])
        except Exception as e:
            pass

def extract_category_from_input(user_input):
    """사용자 입력에서 카테고리 추출"""
    input_lower = user_input.lower()
    category_keywords = {
        "경제": ["경제", "투자", "금융", "주식"],
        "정치": ["정치", "국정", "정부"],
        "과학": ["과학", "우주", "연구"],
        "기술": ["기술", "ai", "인공지능", "스타트업"]
    }
    for category, keywords in category_keywords.items():
        if any(kw in input_lower for kw in keywords):
            return category
    return "기술"

def generate_response(user_input, mode):
    """기본 챗봇 응답 생성"""
    responses = {
        "일반 대화": f"네, '{user_input}'에 대해 말씀해주셨네요.",
        "질문 답변": f"흥미로운 질문입니다! '{user_input}'에 대해 설명해드리겠습니다.",
        "투자 분석": f"투자 관점에서 '{user_input}'는 주목할 만한 주제입니다."
    }
    return responses.get(mode, f"'{user_input}'에 대해 답변드립니다.")

def format_article_display(article):
    """기사를 포맷된 형식으로 표시"""
    category_colors = {
        "경제": "economy",
        "정치": "politics",
        "과학": "science",
        "기술": "tech"
    }
    color_class = category_colors.get(article.get("category", ""), "default")
    
    return {
        "title": article["title"],
        "summary": article["summary"],
        "link": article["link"],
        "date": article["published"][:10] if article["published"] else "날짜 없음",
        "category": article.get("category", "일반"),
        "color_class": color_class
    }

# 글로벌 스케줄러
scheduler = None

def init_scheduler():
    """스케줄러 초기화"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
        scheduler.start()
    return scheduler

# 제목
st.title("📈 투자자용 AI 뉴스 챗봇")
st.subheader("전문가급 뉴스 분석 및 Notion 기반 기사 관리")

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    bot_mode = st.radio(
        "대화 모드를 선택하세요:",
        ("일반 대화", "질문 답변", "투자 분석")
    )
    
    st.divider()
    st.header("📂 뉴스 카테고리")
    
    selected_category = st.selectbox(
        "관심 분야를 선택하세요:",
        list(RSS_FEEDS.keys())
    )
    
    if st.button("🔄 기사 새로고침"):
        with st.spinner(f"{selected_category} 뉴스를 가져오는 중..."):
            articles = fetch_articles_from_rss(selected_category, limit=5)
            st.session_state.category_articles[selected_category] = articles
            st.success(f"✅ {len(articles)}개의 기사를 로드했습니다!")
    
    st.divider()
    
    if notion_client:
        st.success("✅ Notion 연동됨")
    else:
        st.warning("⚠️ Notion 미연동")
    
    if st.button("💬 대화 초기화"):
        st.session_state.messages = []
        st.success("대화가 초기화되었습니다!")
    
    st.divider()
    st.info(f"📊 총 메시지: {len(st.session_state.messages)}")
    st.info(f"⭐ 저장된 기사: {len(st.session_state.saved_articles)}")
    
    st.divider()
    st.header("⏰ 자동 기사 수집 설정")
    
    col1, col2 = st.columns(2)
    with col1:
        scheduled_hour = st.number_input(
            "시간 (0-23):",
            min_value=0,
            max_value=23,
            value=st.session_state.scheduled_time[0] if st.session_state.scheduled_time else 9
        )
    
    with col2:
        scheduled_minute = st.number_input(
            "분 (0-59):",
            min_value=0,
            max_value=59,
            value=st.session_state.scheduled_time[1] if st.session_state.scheduled_time else 0
        )
    
    st.write("**수집할 테마:**")
    selected_categories = []
    for cat in RSS_FEEDS.keys():
        if st.checkbox(f"📌 {cat}", key=f"sched_{cat}"):
            selected_categories.append(cat)
    
    if st.button("💾 스케줄 저장"):
        st.session_state.scheduled_time = (scheduled_hour, scheduled_minute)
        st.session_state.scheduled_categories = selected_categories
        
        if save_schedule_config(selected_categories, scheduled_hour, scheduled_minute):
            sched = init_scheduler()
            
            try:
                sched.remove_job("auto_collect")
            except:
                pass
            
            if selected_categories:
                sched.add_job(
                    auto_collect_articles,
                    'cron',
                    hour=scheduled_hour,
                    minute=scheduled_minute,
                    id='auto_collect',
                    replace_existing=True
                )
                st.success(f"✅ 매일 {scheduled_hour:02d}:{scheduled_minute:02d}에 수집 시작!")
                st.info(f"📂 수집 테마: {', '.join(selected_categories)}")

# 탭 설정
tab1, tab2, tab3 = st.tabs(["💬 챗봇", "📰 카테고리 뉴스", "⭐ 저장된 기사"])

# 탭 1: 챗봇
with tab1:
    st.subheader("AI 챗봇 대화")
    
    chat_container = st.container(border=True)
    
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="👤"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(message["content"])
    
    user_input = st.chat_input("메시지를 입력하세요...")
    
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        if judge_search_intent(user_input):
            category = extract_category_from_input(user_input)
            with st.spinner("관련 기사를 검색하는 중..."):
                articles = fetch_articles_from_rss(category, limit=3)
                if articles:
                    response = f"'{category}' 분야에서 관련 기사 {len(articles)}개를 찾았습니다:\n\n"
                    for i, article in enumerate(articles, 1):
                        response += f"{i}. {article['title']}\n"
                else:
                    response = f"죄송합니다. '{category}' 분야의 최신 기사를 찾지 못했습니다."
        else:
            response = generate_response(user_input, bot_mode)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# 탭 2: 카테고리 뉴스
with tab2:
    st.subheader(f"📰 {selected_category} 뉴스")
    
    if selected_category not in st.session_state.category_articles:
        st.info("🔄 왼쪽 사이드바에서 '기사 새로고침' 버튼을 클릭하세요.")
    else:
        articles = st.session_state.category_articles[selected_category]
        
        if not articles:
            st.warning("기사를 찾지 못했습니다.")
        else:
            # 카드 그리드 (2열)
            cols = st.columns(2, gap="large")
            for idx, article in enumerate(articles):
                formatted = format_article_display(article)
                col = cols[idx % 2]
                
                with col:
                    st.markdown(f"""
                    <div class='news-card'>
                        <span class='category-badge {formatted['color_class']}'>{formatted['category']}</span>
                        <div class='news-card-title'>{formatted['title']}</div>
                        <div class='news-card-summary'>{formatted['summary']}</div>
                        <div class='news-card-meta'>📅 {formatted['date']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 저장", key=f"save_{article['link']}", use_container_width=True):
                            if save_to_notion(article, formatted['summary']):
                                st.session_state.saved_articles.append(article)
                                st.success("저장됨!")
                                st.rerun()
                    
                    with col_btn2:
                        st.link_button("📄 읽기", formatted['link'], use_container_width=True)

# 탭 3: 저장된 기사
with tab3:
    st.subheader("⭐ 저장된 기사 목록")
    
    if not st.session_state.saved_articles:
        st.info("저장된 기사가 없습니다.")
    else:
        categorized = {}
        for article in st.session_state.saved_articles:
            cat = article.get("category", "일반")
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)
        
        for category, articles in categorized.items():
            with st.expander(f"📁 {category} ({len(articles)})"):
                for article in articles:
                    formatted = format_article_display(article)
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        st.markdown(f"**{formatted['title']}**")
                        st.caption(f"{formatted['date']}")
                    with col2:
                        if st.button("🗑️", key=f"delete_{article['link']}"):
                            st.session_state.saved_articles.remove(article)
                            st.rerun()
                    st.markdown(f"[읽기]({formatted['link']})")
                    st.divider()

st.divider()
st.caption(f"⏰ 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
