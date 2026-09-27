from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from retriever import retrieve


load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0
)

prompt = ChatPromptTemplate.from_template("""
You are a helpful YouTube video assistant.

Answer the user's question using ONLY the provided context.

If the answer is not present in the context,
say that the information was not found in the video.

Context:
{context}

Question:
{question}

Answer:
""")
chain = prompt | llm

def generate_answer(question, chunks):

    context = "\n\n".join(
        chunk["text"]
        for chunk in chunks
    )

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return response.content

def answer_question(question, documents):

    context = "\n\n".join(
        doc.page_content
        for doc in documents
    )

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return response.content