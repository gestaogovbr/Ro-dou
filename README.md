![banner](docs/img/banner.png)
# Ro-DOU

[![CI Tests](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml/badge.svg)](https://github.com/gestaogovbr/Ro-dou/actions/workflows/ci-tests.yml)

O Ro-DOU é uma ferramenta de clipping automatizado do Diário Oficial da União (D.O.U.) e de diários oficiais de municípios via [Querido Diário](https://docs.queridodiario.ok.org.br/pt-br/latest/). Ele monitora publicações que contenham palavras-chave definidas pelo usuário e envia notificações por e-mail, Slack, Discord e outros canais.

A ferramenta é executada sobre o [Apache Airflow](https://airflow.apache.org/) e configurada por meio de arquivos YAML simples — sem necessidade de escrever código.

> Para a documentação completa, acesse: <https://gestaogovbr.github.io/Ro-dou/>

O Ro-DOU é desenvolvido e mantido pela Secretaria de Gestão e Inovação do [Ministério da Gestão e da Inovação em Serviços Públicos](https://www.gov.br/gestao/pt-br).

<p>
  <a href="https://discord.gg/8R6bS5D2KN" target="_blank">
    <img alt="Discord Invite" src="https://img.shields.io/badge/Discord-Entre%20no%20servidor-blue?style=for-the-badge&logo=discord" >
  </a>
</p>

Ingresse em nosso [canal de comunidade](https://discord.gg/8R6bS5D2KN) para dúvidas, sugestões, contribuições e conversas em geral sobre o Ro-DOU.

---

## Fontes de dados suportadas

| Fonte | Descrição |
|-------|-----------|
| **DOU** | Diário Oficial da União — seções 1, 2, 3, edições extras e suplementares |
| **INLABS** | API oficial de acesso ao DOU, com suporte a busca avançada, ementa e resumo por IA |
| **QD** | Diários oficiais de municípios via [Querido Diário](https://queridodiario.ok.org.br/) |

## Canais de notificação

- **E-mail** — HTML estilizado com destaques dos termos encontrados
- **Slack** — via webhook
- **Discord** — via webhook
- **Outros canais** — via [Apprise](https://github.com/caronc/apprise) (Telegram, Teams, ntfy etc.)

## Principais funcionalidades

- Busca por **palavras-chave**, **departamento** e/ou **tipo de publicação**
- Agendamento **diário**, **semanal**, **mensal** ou via expressão **cron**
- Relatório em **CSV** anexado ao e-mail
- Busca dinâmica de termos a partir de **banco de dados** ou **variável do Airflow**
- Filtro de termos e departamentos a ignorar (`terms_ignore`, `department_ignore`)
- Exibição de **ementa** (`use_summary`) e texto completo (`full_text`) — INLABS
- **Resumos automáticos por IA** com suporte a OpenAI, Gemini, Claude e Azure — INLABS
- **Score de relevância** dos resultados — INLABS
- Pesquisa em **seção específica** do DOU
- Suporte a **múltiplas pesquisas** em uma mesma DAG

## Início rápido

### Requisitos

- Docker e Docker Compose (≥ 1.29)
- Linux ou Windows com WSL

### Instalação

```bash
git clone https://github.com/gestaogovbr/Ro-dou
cd Ro-dou
make up
```

Acesse o Airflow em `http://localhost:8080` (usuário: `airflow`, senha: `airflow`).

Para habilitar resumos por IA, informe os provedores no build:

```bash
make build AI_PROVIDERS="openai gemini"
```

Provedores disponíveis: `openai`, `gemini`, `claude`.

Para mais detalhes, consulte o [guia de instalação](https://gestaogovbr.github.io/Ro-dou/como_utilizar/instalacao/).

### Exemplo de configuração (YAML)

```yaml
dag:
  id: pesquisa_exemplo
  description: Exemplo de pesquisa no DOU
  schedule: "0 8 * * MON-FRI"
  search:
    sources:
      - DOU
    terms:
      - nome da empresa
      - servidor público
    dou_sections:
      - SECAO_3
  report:
    emails:
      - seu@email.gov.br
    subject: "Clipping DOU - {{ ds }}"
```

Veja mais exemplos em [docs/docs/como_funciona/exemplos.md](docs/docs/como_funciona/exemplos.md).

## Documentação

A documentação completa está disponível em <https://gestaogovbr.github.io/Ro-dou/> e inclui:

- [Como funciona](https://gestaogovbr.github.io/Ro-dou/como_funciona/intro_funcionamento/)
- [Parâmetros de configuração](https://gestaogovbr.github.io/Ro-dou/como_funciona/parametros/)
- [Como instalar](https://gestaogovbr.github.io/Ro-dou/como_utilizar/instalacao/)
- [Habilitando IA](https://gestaogovbr.github.io/Ro-dou/como_utilizar/habilitando_ia/)

## Contribuindo

Contribuições são bem-vindas! Abra uma _issue_ ou _pull request_ no [repositório GitHub](https://github.com/gestaogovbr/Ro-dou). Participe também do nosso [servidor no Discord](https://discord.gg/8R6bS5D2KN).
