# syntax=docker/dockerfile:1
FROM python:3.12-alpine AS build
WORKDIR /app
COPY tools/ tools/
COPY src/ src/
RUN python3 tools/build.py && test -s dist/index.html && test -s dist/machine.css
FROM python:3.12-alpine AS converter
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=build /app/tools/ tools/
COPY --from=build /app/src/ src/
USER 101:101
EXPOSE 8090
CMD ["gunicorn", "--chdir", "/app/tools", "--bind", "0.0.0.0:8090", "--workers", "2", "--no-control-socket", "--timeout", "180", "--max-requests", "100", "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "server:application"]

FROM nginx/nginx-unprivileged:1.31.9-alpine AS web
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 8080
