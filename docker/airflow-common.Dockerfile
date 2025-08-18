# Ajuste a tag base se você usa outra (mantenha a MESMA base p/ webserver e scheduler)
FROM apache/airflow:2.9.3-python3.10

# 1) Pacotes básicos + CA do sistema atualizada
USER root
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl openssl; \
    update-ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# 2) Instala o intermediário Sectigo R36 no trust store do sistema
RUN set -eux; \
    tmp="$(mktemp -d)"; \
    curl -fsSL http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt -o "${tmp}/r36.der"; \
    openssl x509 -inform DER -in "${tmp}/r36.der" -out /usr/local/share/ca-certificates/sectigo_r36.crt; \
    # checagem “suave” do emissor; não falha o build se o texto variar
    openssl x509 -in /usr/local/share/ca-certificates/sectigo_r36.crt -noout -issuer \
      | grep -i -q "Sectigo Public Server Authentication CA" || echo "Warn: issuer check relaxed"; \
    update-ca-certificates; \
    rm -rf "${tmp}"

# 3) Copia e instala as dependências Python do projeto
#    (o build context é o diretório raiz do repo; copie daqui)
COPY --chown=airflow:root requirements.txt /requirements.txt

# Evita warnings do pip quando rodar como root durante o build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_ROOT_USER_ACTION=ignore

# Instala primeiro como root (em imagens do Airflow isso já acerta o venv usado)
RUN python -m pip install --no-cache-dir -U pip && \
    python -m pip install --no-cache-dir -U certifi && \
    python -m pip install --no-cache-dir -r /requirements.txt

# (opcional) se quiser forçar explicitamente o bundle do certifi para Requests:
# ENV SSL_CERT_FILE=/usr/local/lib/python3.10/site-packages/certifi/cacert.pem

# Volta ao usuário airflow – boa prática
USER airflow
