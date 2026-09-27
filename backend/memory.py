from langchain_core.messages import HumanMessage, AIMessage


chat_history = []


def add_user_message(message):
    chat_history.append(
        HumanMessage(content=message)
    )


def add_ai_message(message):
    chat_history.append(
        AIMessage(content=message)
    )


def get_chat_history():
    return chat_history