# 1. Imagem Oficial do Playwright (Garante estabilidade do Scraper)
# Esta base já contém todas as dependências de sistema para o Chromium
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# 2. Configurações de Ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app

# 3. Define o diretório de trabalho
WORKDIR $APP_HOME

# 4. Criação do usuário não-root (Segurança Enterprise)
# Impede que o processo rode como root, cumprindo requisitos de compliance
RUN groupadd -r appgroup && useradd -r -g appgroup -d $APP_HOME -s /sbin/nologin appuser

# 5. Instalação de dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia o código-fonte (Core e API)
COPY ./core ./core
COPY ./static ./static
COPY ./rag_generator.py .
COPY .env .

# 7. Cria as pastas de persistência e ajusta permissões ANTES de trocar de usuário
# Precisamos garantir que o appuser tenha controle sobre os bancos de dados
RUN mkdir -p vector_db output && \
    chown -R appuser:appgroup $APP_HOME

# 8. Troca para o usuário seguro
USER appuser

# 9. Exposição e Comando de Execução (Production Standard)
EXPOSE 8000
CMD ["uvicorn", "rag_generator:app", "--host", "0.0.0.0", "--port", "8000"]
