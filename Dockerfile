# 1. Imagem Oficial do Playwright (Garante estabilidade do Scraper)
# Esta base já contém todas as dependências de sistema para o Chromium
FROM mcr.microsoft.com/playwright/python:v1.59.0-jammy

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
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Verificação de Integridade: Garante que o Pydantic está no caminho e acessível
RUN python3 -c "import pydantic; print('Fase de Verificação: Pydantic v' + pydantic.__version__ + ' detectado com sucesso.')"

RUN python3 -m playwright install chromium

# 6. Copia TODO o código-fonte do projeto
COPY . .

# 7. Cria as pastas de persistência e ajusta permissões ANTES de trocar de usuário
RUN mkdir -p data/output data/redis vector_db missoes && \
    chown -R appuser:appgroup $APP_HOME

# 8. Configuração de Caminhos de Execução
ENV PYTHONPATH="/app:/usr/local/lib/python3.10/site-packages:/usr/lib/python3/dist-packages"

# 9. Troca para o usuário seguro
USER appuser

# 10. Exposição de Porta
EXPOSE 8000

# 11. Ponto de Entrada Dinâmico
CMD ["python3", "-m", "core.main_batalhao"]
