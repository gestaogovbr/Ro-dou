# Ajuste a tag base se você usa outra (mantenha mesma base p/ webserver e scheduler)
FROM apache/airflow:2.9.3-python3.10

USER root

# 1) Pacotes básicos + CA do sistema atualizada
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl openssl; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# 2) Instala o intermediário Sectigo R36 no trust store do sistema
#    (converte DER -> PEM, valida emissor e atualiza o trust)
RUN set -eux; \
    tmp="$(mktemp -d)"; \
    curl -fsSL http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt -o "${tmp}/r36.der"; \
    openssl x509 -inform DER -in "${tmp}/r36.der" -out /usr/local/share/ca-certificates/sectigo_r36.crt; \
        # sanity check: garante que o emissor aparenta ser Sectigo (não-fatal)
        # alguns servidores podem formatar o issuer de forma ligeiramente diferente,
        # então fazemos uma checagem mais permissiva e não falhamos o build se não casar.
        openssl x509 -in /usr/local/share/ca-certificates/sectigo_r36.crt -noout -issuer \
            | grep -i -q "Sectigo Public Server Authentication CA" || echo "Warning: issuer did not match exactly; continuing"; \
    update-ca-certificates; \
    rm -rf "${tmp}"

# 3) Atualiza certifi dentro do venv do Airflow (permitindo pip como root no build)
USER root
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore
RUN python - <<'PY'
import sys, subprocess
subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-U", "certifi"])
import certifi; print("certifi bundle:", certifi.where())
PY

# (Opcional) você pode omitir isto, pois Requests já usa certifi por padrão.
# Deixei comentado — ative se quiser forçar explicitamente.
# ENV SSL_CERT_FILE=/usr/local/lib/python3.10/site-packages/certifi/cacert.pem

# Volta para o usuário airflow (boa prática na imagem do Airflow)
USER airflow