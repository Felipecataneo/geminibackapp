# Usa a imagem oficial do Python
FROM python:3.12

# Define o diretório de trabalho no container
WORKDIR /app

# Copia os arquivos do projeto para dentro do container
COPY . .

# Instala as dependências
RUN pip install --upgrade google-genai==0.5.0 websockets

# Expor a porta do WebSocket
EXPOSE 9084

# Comando para rodar o servidor
CMD ["python", "server.py"]
