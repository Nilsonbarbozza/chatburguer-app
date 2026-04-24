# 1. Imagem Oficial do Playwright (Garante estabilidade do Scraper)
# Esta base já contém todas as dependências de sistema para o Chromium
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

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

# 6. Copia TODO o código-fonte do projeto
COPY . .

# 7. Cria as pastas de persistência e ajusta permissões ANTES de trocar de usuário
RUN mkdir -p data/output data/redis vector_db missoes && \
    chown -R appuser:appgroup $APP_HOME

# 8. Troca para o usuário seguro
USER appuser

# 9. Exposição de Porta (para o serviço RAG/FastAPI, ignorado pelo Batalhão)
EXPOSE 8000

# 10. Ponto de Entrada Dinâmico
# O CMD padrão roda o Batalhão. Para rodar o RAG, sobrescreva no docker-compose.
CMD ["python", "-m", "core.main_batalhao"]
