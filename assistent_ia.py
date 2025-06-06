import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import os

KEY = os.getenv("OPENAI_API_KEY")
if not KEY:
    st.error("Chave de API não encontrada. Por favor, defina a variável de ambiente OPENAI_API_KEY.")

# Função para ler arquivos do sistema
def ler_arquivos(caminhos):
    conteudos = {}
    for caminho in caminhos:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                conteudos[caminho] = f.read()
        except Exception as e:
            conteudos[caminho] = f"Erro ao ler: {e}"
    return conteudos

# Defina aqui os arquivos que deseja usar como contexto
ARQUIVOS_CONTEXTO = [
    "models.py",
    "routes.py",
    "database.py",
    # Adicione outros arquivos relevantes
]

conteudo_arquivos = ler_arquivos(ARQUIVOS_CONTEXTO)

# Configuração do modelo de linguagem
chat = ChatOpenAI(
    api_key=KEY,
    model="gpt-3.5-turbo",
    temperature=0.7
)

st.set_page_config(
    page_title="Assistente IA",
    page_icon="🤖",
    layout="wide"
)
st.title("Assistente IA")
st.write("Este é um assistente de IA que pode responder a perguntas e ajudar com tarefas sobre o sistema.")

st.markdown("""
## Instruções
Faça perguntas sobre o banco de dados, lógica ou rotas do sistema.
""")

pergunta = st.text_input("Digite sua pergunta:")

if pergunta:
    contexto = "\n\n".join([f"Arquivo: {k}\n{v}" for k, v in conteudo_arquivos.items()])
    prompt = f"""
Você é um assistente para desenvolvedores. Use as informações abaixo sobre o sistema para responder à pergunta do usuário.

{contexto}

Pergunta: {pergunta}
Resposta:"""
    resposta = chat.invoke(prompt)
    st.markdown(f"**Resposta:** {resposta.content}")