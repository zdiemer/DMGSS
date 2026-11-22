# syntax=docker/dockerfile:1
FROM python:3.12-alpine AS build
WORKDIR /app
COPY tools/ tools/
COPY src/ src/
RUN python3 tools/build.py && test -s dist/index.html && test -s dist/machine.css
FROM nginx/nginx-unprivileged:1.31.9-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 8080
