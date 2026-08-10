FROM python:3.12-slim

ARG GIT_SHA=local

WORKDIR /app

RUN printf '<h1>GitHub Actions Docker Lab</h1><p>Version: %s</p>\n' \
    "${GIT_SHA}" \
    > /app/index.html

EXPOSE 8000

CMD ["python","-m","http.server","8000","--bind","0.0.0.0"]
