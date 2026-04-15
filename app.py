import os
import sqlite3
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI

DB_PATH = "memory.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_memory(user_id: str, note: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO memories (user_id, note, created_at) VALUES (?, ?, ?)",
            (user_id, note.strip(), timestamp),
        )
        conn.commit()


def get_memories(user_id: str, limit: int = 8) -> list[str]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT note FROM memories
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [row[0] for row in rows]


def build_system_prompt(user_id: str) -> str:
    memories = get_memories(user_id)
    memory_block = "\n".join(f"- {m}" for m in memories) if memories else "- No saved memory yet."
    return (
        "You are a Coursera-style study coach. "
        "Help the user learn by explaining concepts clearly, offering examples, and giving short exercises.\n\n"
        "Use this persistent memory about the learner:\n"
        f"{memory_block}\n\n"
        "If relevant, adapt your response based on memory."
    )


def ask_chatgpt(client: OpenAI, user_id: str, question: str) -> str:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": build_system_prompt(user_id)},
            {"role": "user", "content": question},
        ],
    )
    return response.output_text


def main() -> None:
    st.set_page_config(page_title="Coursera Coach with Memory", page_icon="🧠")
    st.title("🧠 Coursera Coach on ChatGPT")
    st.caption("A simple learning assistant with persistent memory via SQLite.")

    init_db()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("Set OPENAI_API_KEY first (env var) and restart the app.")
        st.stop()

    client = OpenAI(api_key=api_key)

    user_id = st.text_input("Learner ID", value="default_learner")

    with st.expander("Add learner memory", expanded=True):
        memory_note = st.text_input(
            "Save a preference, goal, or weakness",
            placeholder="Example: I'm preparing for a machine learning quiz next week.",
        )
        if st.button("Save memory"):
            if memory_note.strip():
                add_memory(user_id, memory_note)
                st.success("Memory saved.")
            else:
                st.warning("Please enter memory text first.")

    st.subheader("Saved memory")
    saved = get_memories(user_id, limit=20)
    if saved:
        for item in saved:
            st.write(f"• {item}")
    else:
        st.info("No memory saved for this learner yet.")

    st.subheader("Ask your learning question")
    question = st.text_area(
        "Question",
        placeholder="Explain gradient descent in simple terms and quiz me with 2 questions.",
        height=120,
    )

    if st.button("Ask ChatGPT"):
        if not question.strip():
            st.warning("Please enter a question.")
            st.stop()
        with st.spinner("Thinking..."):
            answer = ask_chatgpt(client, user_id, question)
        st.markdown("### Coach response")
        st.write(answer)


if __name__ == "__main__":
    main()
