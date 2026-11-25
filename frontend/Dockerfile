FROM nginx:1.27-alpine

# Значення за замовчуванням; у Kubernetes задаються через ConfigMap/Helm values
ENV API_UPSTREAM=http://items-api:8080 \
    API_BASE_URL=/api \
    NGINX_ENVSUBST_FILTER=^API_

COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY nginx/40-config.sh /docker-entrypoint.d/40-config.sh
COPY index.html app.js styles.css config.js /usr/share/nginx/html/
RUN chmod +x /docker-entrypoint.d/40-config.sh

EXPOSE 80
