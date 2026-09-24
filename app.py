import streamlit as st

from rag_pipeline import generate_answer, generate_compliance_check

st.set_page_config(page_title="BIS Saarthi", page_icon="🤖", layout="centered")

st.markdown("## 🤖 BIS Saarthi")
st.caption("A source-grounded assistant for Indian Standards (BIS) - built for the "
           "Smart India Hackathon.")

with st.sidebar:
    st.markdown("### Mode")
    mode = st.radio(
        "What do you want to do?",
        ["Ask a question", "Check product compliance"],
        label_visibility="collapsed",
    )

    st.markdown("### Example questions")
    examples = [
        "What is required to hallmark gold jewellery?",
        "What are the silver hallmarking fineness grades?",
        "How do I apply for a BIS licence?",
        "What happens if I sell goods without a valid BIS licence?",
    ]
    for ex in examples:
        st.markdown(f"- {ex}")

    st.divider()
    st.caption(
        "⚠️ BIS Saarthi answers only from its indexed BIS knowledge base and "
        "always cites the standard/clause it used. It is an information aid, "
        "not a legal substitute for the official standard - always verify "
        "against bis.gov.in for compliance decisions."
    )

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello! I'm BIS Saarthi. Ask me about a BIS standard, hallmarking, "
                "certification, or licensing - or switch to **Check product "
                "compliance** in the sidebar and paste a product description."
            ),
            "sources": [],
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("📄 Sources"):
                for chunk in message["sources"]:
                    st.markdown(f"**{chunk.standard}** - {chunk.clause}\n\n{chunk.source}")

placeholder = (
    "Ask about a BIS standard or service..."
    if mode == "Ask a question"
    else "Paste your product description to check compliance..."
)

if user_prompt := st.chat_input(placeholder):
    st.session_state.messages.append({"role": "user", "content": user_prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Looking this up in the BIS knowledge base..."):
            if mode == "Ask a question":
                result = generate_answer(user_prompt)
            else:
                result = generate_compliance_check(user_prompt)

        st.markdown(result.answer)
        if result.sources:
            with st.expander("📄 Sources"):
                for chunk in result.sources:
                    st.markdown(f"**{chunk.standard}** - {chunk.clause}\n\n{chunk.source}")

        st.session_state.messages.append(
            {"role": "assistant", "content": result.answer, "sources": result.sources}
        )
