FROM python:3.10-slim

WORKDIR /usr/src/app

COPY . .

RUN pip install mkdocs

EXPOSE 8000

CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]

# Para rodar o site localmente, sem container, basta instalar o MkDocs
# via pip/Python
# Em seguida, rodar neste diretório: mkdocs serve

# Para efetuar o build com container Docker:
# docker compose up --build

# Para gerar os arquivos estáticos necessários para o GitHub Pages:
# docker compose run --rm mkdocs mkdocs build