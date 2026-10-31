import streamlit as st
from agent.agent_loop import AgentLoop

st.set_page_config(page_title="Reasoning Agent", page_icon="🧠")


@st.cache_resource
def get_agent():
    return AgentLoop(max_retries=2)


agent = get_agent()

st.title("🧠 Multi-Step Reasoning Agent")
st.caption("Ask a question and the agent will solve it step by step.")

question = st.text_area("Your question", placeholder="Type your question here...")

if st.button("Solve", type="primary"):
    if not question.strip():
        st.warning("Please enter a question!")
    else:
        with st.spinner("Thinking..."):
            result = agent.solve(question)

        st.subheader("Answer")
        st.success(result["answer"])
        st.caption(f"Status: {result['status']}")

        with st.expander("Explanation", expanded=True):
            st.write(result["reasoning_visible_to_user"])
        with st.expander("Debug Info"):
            st.json(result["metadata"])