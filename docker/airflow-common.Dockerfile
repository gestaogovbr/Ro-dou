# Ajuste a tag base se você usa outra (mantenha a MESMA base p/ webserver e scheduler)
FROM apache/airflow:2.9.3-python3.10

# Nota: mantenha a mesma base para webserver e scheduler para evitar
# incompatibilidades entre containers.

# Defina noninteractive para evitar prompts durante apt installs
ARG DEBIAN_FRONTEND=noninteractive
USER root

# 1) Pacotes básicos + CA do sistema atualizada
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl openssl; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# 2) (Opcional) Instala um certificado intermediário Sectigo no trust store do sistema
#    Alguns deploys exigem certificados de CA adicionais. Isso NÃO deve conter
#    certificados privados nem segredos embutidos na imagem. Você pode desabilitar
#    esta etapa passando --build-arg INSTALL_SECTIGO_R36=false.
ARG INSTALL_SECTIGO_R36=true
RUN if [ "${INSTALL_SECTIGO_R36}" = "true" ]; then \
    tmp="$(mktemp -d)"; \
    cert_url_https="https://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"; \
    cert_url_http="http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"; \
    # tenta HTTPS primeiro; se falhar, tenta HTTP; se ambos falharem, avisa e continua
    if curl -fsSL "${cert_url_https}" -o "${tmp}/r36.der"; then \
        echo "Downloaded Sectigo cert via HTTPS"; \
    elif curl -fsSL "${cert_url_http}" -o "${tmp}/r36.der"; then \
        echo "Downloaded Sectigo cert via HTTP (fallback)"; \
    else \
        echo "Warning: could not download Sectigo R36 certificate; skipping installation"; \
    fi; \
    if [ -f "${tmp}/r36.der" ]; then \
        openssl x509 -inform DER -in "${tmp}/r36.der" -out /usr/local/share/ca-certificates/sectigo_r36.crt; \
        # checagem permissiva do issuer (não-fatal)
        openssl x509 -in /usr/local/share/ca-certificates/sectigo_r36.crt -noout -issuer \
          | grep -i -q "Sectigo Public Server Authentication CA" || echo "Warn: issuer check relaxed"; \
        update-ca-certificates; \
    fi; \
    rm -rf "${tmp}"; \
    fi

# 3) Copia e instala as dependências Python do projeto
#    (o build context é o diretório raiz do repo; copie daqui)
COPY --chown=airflow:root requirements.txt /requirements.txt
# Optional test requirements: installed only when present to keep production images lean
COPY --chown=airflow:root tests-requirements.txt /tests-requirements.txt

# Evita warnings do pip quando rodar como root durante o build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore

# Instala primeiro como root (em imagens do Airflow isso já acerta o venv usado)
RUN set -eux; \
    # retry loop para mitigar falhas de rede temporárias ao baixar pacotes
    max_retries=5; \
    attempt=0; \
    while [ "$attempt" -lt "$max_retries" ]; do \
        attempt=$((attempt + 1)); \
        echo "pip install attempt $attempt/$max_retries"; \
        if python -m pip install --no-cache-dir -U pip --timeout 120 && \
           python -m pip install --no-cache-dir -U certifi --timeout 120 && \
           python -m pip install --no-cache-dir -r /requirements.txt --timeout 120; then \
            # If tests-requirements.txt exists, install it too (provides pytest and friends)
            if [ -f /tests-requirements.txt ]; then \
                python -m pip install --no-cache-dir -r /tests-requirements.txt --timeout 120 || true; \
            fi; \
            echo "pip install succeeded on attempt $attempt"; \
            break; \
        fi; \
        echo "pip install attempt $attempt failed, sleeping 10s before retry"; \
        sleep 10; \
    done; \
    if [ "$attempt" -ge "$max_retries" ]; then \
        echo "ERROR: pip install failed after $max_retries attempts"; \
        exit 1; \
    fi

# Observação: se quiser forçar explicitamente o bundle do certifi para Requests,
# descomente e ajuste a linha abaixo.
# ENV SSL_CERT_FILE=/usr/local/lib/python3.10/site-packages/certifi/cacert.pem

# Volta ao usuário airflow — boa prática
USER airflow
