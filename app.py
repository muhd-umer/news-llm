# app.py

__import__("pysqlite3")
import sys

sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import os
import time
from datetime import datetime

import pytz
import streamlit as st
from database import NewsDatabase
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from prompts import CHAT_RESPONSE_PROMPT, FOLLOW_UP_QUESTIONS_PROMPT, MAIN_SYSTEM_PROMPT

load_dotenv()

db = NewsDatabase()
db.start_automatic_updates()

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("Please set the GROQ_API_KEY environment variable")

llm = ChatGroq(
    model="llama-3.3-70b-versatile", groq_api_key=groq_api_key, temperature=0.2
)

custom_css = """
    <style>
        div[data-baseweb="select"] > div {
            overflow-x: auto !important;
        }
        .stAlert {
            margin-top: 1rem;
        }
        .last-update {
            font-size: 0.8rem;
            color: #888;
            margin-top: 0.5rem;
            text-align: center;
        }
        .logo {
            display: block;
            margin: 0 auto;
        }
        .top-space {
            margin-top: -40px;
        }
        .stSpinner {
            display: flex;
            flex-direction: column;
            align-items: center;
        }
    </style>
"""


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "sources" not in st.session_state:
        st.session_state.sources = []
    if "country" not in st.session_state:
        st.session_state.country = None
    if "topic" not in st.session_state:
        st.session_state.topic = None
    if "analysis_generated" not in st.session_state:
        st.session_state.analysis_generated = False
    if "generation_count" not in st.session_state:
        st.session_state.generation_count = 0
    if "generation_timestamps" not in st.session_state:
        st.session_state.generation_timestamps = []


def display_chat():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})


def reset_chat():
    st.session_state.messages = []
    st.session_state.sources = []
    st.session_state.country = None
    st.session_state.topic = None
    st.session_state.analysis_generated = False


def update_generation_count(cooldown_minutes=60):
    current_time = time.time()
    st.session_state.generation_timestamps = [
        timestamp
        for timestamp in st.session_state.generation_timestamps
        if current_time - timestamp < cooldown_minutes * 60
    ]
    st.session_state.generation_count = len(st.session_state.generation_timestamps)


def get_chat_history():
    return "\n".join(
        [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
    )


def get_last_update():
    try:
        with open("chroma_db/last_update.txt", "r") as f:
            last_update_str = f.read().strip()

        last_update = datetime.fromisoformat(last_update_str)
        last_update = last_update.replace(tzinfo=pytz.UTC)

        return last_update.strftime("%Y-%m-%d %H:%M:%S (Pakistan Time)")
    except Exception as e:
        print(f"Error reading last update time: {e}")
        return "Unknown"


def main():
    GENERATION_LIMIT = 5
    COOLDOWN_MINUTES = 30  # in minutes

    initialize_session_state()
    update_generation_count(COOLDOWN_MINUTES)

    st.set_page_config(
        layout="wide", page_title="NewsLLM", page_icon="images/favicon.ico"
    )
    st.markdown(custom_css, unsafe_allow_html=True)
    st.markdown(
        "<img src='https://raw.githubusercontent.com/muhd-umer/news-llm/main/images/logo.png' width='375' class='logo top-space'>",
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("#### Prompt")
    countries = ["USA", "UK", "Pakistan", "International"]
    topics = [
        "Sports ⚽",
        "Entertainment 🎬",
        "Politics 🏛️",
        "Economy 💰",
        "Health 🏥",
        "Science 🔬",
        "Technology 🤖",
    ]

    country = st.sidebar.selectbox("Choose a country:", countries)
    selected_topic = st.sidebar.selectbox("Select a topic:", topics)
    selected_topic = selected_topic.split(" ")[0].lower()

    button_disabled = st.session_state.generation_count >= GENERATION_LIMIT

    if st.sidebar.button(
        "Analyze news",
        use_container_width=True,
        type="primary",
        disabled=button_disabled,
    ):
        if st.session_state.generation_count < GENERATION_LIMIT:
            reset_chat()
            st.session_state.country = country
            st.session_state.topic = selected_topic
            st.session_state.generation_timestamps.append(time.time())
            st.session_state.generation_count += 1
            with st.spinner("Generating summary..."):
                query = f"{country} {selected_topic} news"
                relevant_documents = db.search(query, country, selected_topic, k=7)

                if not relevant_documents:
                    st.session_state.analysis_generated = False
                    add_message(
                        "assistant",
                        "No relevant documents found. Please try a different country or topic.",
                    )
                else:
                    context = "\n\n".join(
                        [
                            f"Article {i+1}:\n{doc.page_content}..."
                            for i, doc in enumerate(relevant_documents)
                        ]
                    )

                    main_chain = MAIN_SYSTEM_PROMPT | llm
                    summary = main_chain.invoke(
                        {
                            "country": country,
                            "topic": selected_topic,
                            "context": context,
                        }
                    )

                    if summary.content.strip():
                        add_message("assistant", summary.content)
                        st.session_state.sources = [
                            doc.metadata["source"] for doc in relevant_documents
                        ]
                        st.session_state.analysis_generated = True

                        questions_chain = FOLLOW_UP_QUESTIONS_PROMPT | llm
                        follow_up = questions_chain.invoke({"summary": summary.content})
                        add_message("assistant", follow_up.content)
                    else:
                        st.session_state.analysis_generated = False
                        add_message(
                            "assistant",
                            "Failed to generate a summary. Please try again.",
                        )

    if st.session_state.generation_count >= GENERATION_LIMIT:
        next_available = min(st.session_state.generation_timestamps) + (
            COOLDOWN_MINUTES * 60
        )
        wait_time = max(0, next_available - time.time())
        wait_minutes = int(wait_time // 60)
        wait_seconds = int(wait_time % 60)
        st.sidebar.info(
            f"Generation limit reached. Next generation available in approximately {wait_minutes} minutes and {wait_seconds} seconds."
        )

    if st.sidebar.button("Reset", use_container_width=True):
        reset_chat()

    st.sidebar.markdown("#### Sources")
    if st.session_state.sources:
        sources_text = "\n".join(
            [f"- [{source}]({source})" for source in st.session_state.sources]
        )
        st.sidebar.markdown(sources_text)
    else:
        st.sidebar.info("No sources available. Generate an analysis to see sources.")

    display_chat()

    if st.session_state.analysis_generated:
        user_input = st.chat_input(
            "Ask a follow-up question or type 'new analysis' to start over"
        )
        if user_input:
            if user_input.lower() == "new analysis":
                reset_chat()
                st.rerun()
            else:
                add_message("human", user_input)
                with st.spinner("Generating response..."):
                    chat_history = get_chat_history()
                    response_chain = CHAT_RESPONSE_PROMPT | llm
                    response = response_chain.invoke(
                        {
                            "country": st.session_state.country,
                            "topic": st.session_state.topic,
                            "user_input": user_input,
                            "chat_history": chat_history,
                        }
                    )
                    add_message("assistant", response.content)
                st.rerun()

    st.markdown(
        f"<p class='last-update'>Last database update: {get_last_update()} | Made by <a href='https://github.com/muhd-umer/' target='_blank'>Muhammad Umer</a></p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
