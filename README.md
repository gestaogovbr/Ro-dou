![banner](docs/img/banner.png)
# Ro-DOU

[![CI Tests](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml/badge.svg)](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml) 
![Python](https://img.shields.io/badge/Python-%3E%3D3.8-blue) ![Docker](https://img.shields.io/badge/Docker-%232496ED?logo=docker) ![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.x-orange?logo=apache-airflow) ![Postgres](https://img.shields.io/badge/PostgreSQL-13-blue?logo=postgresql) ![Pydantic](https://img.shields.io/badge/Pydantic-1.x-brightgreen) ![PyYAML](https://img.shields.io/badge/PyYAML-present-blue)

O Ro-DOU é uma ferramenta que faz clipping do Diário Oficial da União (D.O.U.) e de diários municipais via Querido Diário. Ele processa publicações, gera relatórios e envia notificações (e-mail, Slack, Discord ou outros) quando encontra correspondências para os termos configurados.

Documentação completa e exemplos estão em: https://gestaogovbr.github.io/Ro-dou/

## Ferramentas e bibliotecas principais
- Python (runtime do projeto)
- Apache Airflow (orquestração de DAGs)
- Docker / Docker Compose (ambientes e containers)
- PostgreSQL (armazenamento)
- Pydantic (validação de configurações YAML)
- PyYAML (parsing de YAML)
- psycopg2 (conector PostgreSQL)
- requests / httpx (chamadas HTTP)
- pytest (testes automatizados)

## Fork ANPD — especializações desta cópia
Esta cópia é mantida pela ANPD com adaptações operacionais para ambientes internos. Principais mudanças na branch `feat/make-bootstrap` (vs `origin/main:HEAD`):
- Evita retries desnecessários em falhas por `SSLError` em chamadas de rede.
- Parametriza o `Makefile` para builds e execuções mais flexíveis em CI/local.
- Aumenta a robustez do `Dockerfile` durante o build.
- Ajustes de bootstrap do Airflow: migrações automáticas e criação de usuário admin para facilitar desenvolvimento local.
- Ajustes no `docker-compose.yml` para dev (omissão intencional do `version:`, fallbacks seguros e `smtp4dev` em `profiles: ["dev"]`).

> Consulte `CHANGELOG.md` para o histórico completo de releases.


## Links úteis
- Documentação do projeto: https://gestaogovbr.github.io/Ro-dou/
- Changelog: `CHANGELOG.md`
- Canal da comunidade: https://discord.gg/8R6bS5D2KN

---

Posso commitar e dar push desta versão consolidada do `README.md` (usa uma mensagem padrão `docs: consolidar README e adicionar badges`) ou aplicar outra mensagem — diga qual prefere.

