FROM python:3.10-slim

WORKDIR /usr/src/app

COPY . .

RUN pip install mkdocs

EXPOSE 8000

CMD ["mkdocs", "serve", "-a", "0.0.0.0:8000"]

# To launch the site locally without containers,
# first install the "mkdocs" using pip/Python.
# Then, in the directory, run: mkdocs serve

# To build using the Docker container, run:
# docker compose up --build

# To generate the necessary static files for GitHub Pages, run:
# docker compose run --rm mkdocs mkdocs build