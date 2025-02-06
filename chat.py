import streamlit as st
from langchain_aws import ChatBedrock

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "llm" not in st.session_state:
        st.session_state.llm = ChatBedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            model_kwargs=dict(temperature=0),
        )

def chat_interface():
    st.title("💬 Chat with CorpAct Buddy")
    

    init_session_state()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Welcome back, How can I assit you with your Corporate Actions Research today?"):

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:

                    response = st.session_state.llm.predict(prompt)
                    
                    st.markdown(response)
                    

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                except Exception as e:
                    st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    chat_interface()