# Como o Ro-DOU Funciona

O Ro-DOU é um sistema de monitoramento automatizado do Diário Oficial da União (DOU) e diários municipais. Este documento explica seu funcionamento.

## Arquitetura Geral

O sistema usa **Apache Airflow** para orquestrar tarefas automatizadas que:
1. Buscam termos específicos em publicações oficiais
2. Processam os resultados encontrados
3. Enviam notificações quando há correspondências

## Como Funciona

### 1. **Configuração via YAML**
Cada busca é definida em um arquivo YAML em `dag_confs/`:

```yaml
dag:
  id: basic_example
  description: DAG de teste
  search:
    terms:
    - dados abertos
    - governo aberto
    - lei de acesso à informação
  report:
    emails:
      - destination@economia.gov.br
    subject: "Teste do Ro-dou"
```

### 2. **Geração Dinâmica de DAGs**
O `dou_dag_generator.py` lê esses YAMLs e cria automaticamente DAGs do Airflow que:
- Executam buscas nos termos definidos
- Verificam se há resultados
- Enviam notificações quando encontram publicações

### 3. **Motores de Busca**
Três searchers diferentes fazem as buscas:

- **DOUSearcher**: Busca no DOU oficial
- **QDSearcher**: Busca em diários municipais via Querido Diário  
- **INLABSSearcher**: Busca no portal INLabs

### 4. **Fluxo de Execução**
1. O Airflow scheduler executa os DAGs conforme programado
2. Para cada termo, faz buscas nas fontes configuradas
3. Coleta e processa os resultados
4. Se encontra publicações, gera relatório
5. Envia notificação (email/Slack/Discord)

### 5. **Notificações**
O sistema de notificação suporta múltiplos canais:
- Email (via SMTP)
- Slack 
- Discord
- Outros implementáveis via interface

## Tecnologias Principais

- **Apache Airflow**: Orquestração de workflows
- **Docker**: Containerização (Airflow + PostgreSQL + SMTP)
- **Python**: Lógica de negócio
- **Pydantic**: Validação de configurações YAML
- **PostgreSQL**: Armazenamento de dados

## Componentes Principais

### Estrutura de Diretórios
```
src/
├── dou_dag_generator.py    # Gerador dinâmico de DAGs
├── searchers.py            # Motores de busca
├── schemas.py              # Validação de configurações
├── parsers.py              # Parser de arquivos YAML
├── hooks/                  # Integrações com APIs externas
└── notification/           # Sistema de notificações

dag_confs/                  # Configurações YAML dos DAGs
tests/                      # Testes automatizados
```

### Workflow Típico
1. **Configuração**: Criar arquivo YAML com termos e configurações
2. **Deploy**: O sistema detecta automaticamente novos YAMLs
3. **Execução**: Airflow executa as buscas conforme cronograma
4. **Processamento**: Resultados são coletados e processados
5. **Notificação**: Relatórios são enviados aos destinatários

O sistema é especialmente útil para órgãos públicos que precisam monitorar publicações oficiais relevantes automaticamente.