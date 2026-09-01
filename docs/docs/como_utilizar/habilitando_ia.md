# Integração com Inteligência Artificial Generativa

O Ro-DOU permite gerar resumos automáticos das publicações encontradas no Diário Oficial da União (DOU) usando um modelo de linguagem (LLM) de um provedor de IA externo.

Isso ajuda a reduzir o tempo de análise, destacando rapidamente o conteúdo mais relevante de cada publicação. O prompt enviado à IA pode ser customizado (`ai_custom_prompt`), permitindo adaptar o resumo — em tópicos, mais detalhado, em outro tom, etc.

⚠️ **Disponível apenas para a fonte INLABS.**

Assista ao vídeo abaixo para ver a configuração completa na prática:

<iframe width="560" height="315" src="https://www.youtube.com/embed/tP18HtsI-0g?si=MTjvx_0GOMVYF_Hb" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Provedores suportados

* OpenAI
* Gemini
* Claude
* Azure OpenAI

⚠️ **Atenção aos custos:** o uso de IA pode gerar custos por consumo de tokens, cobrados diretamente pelo provedor escolhido. Ajuste `ai_pub_limit` para limitar quantas publicações são processadas por execução — importante em buscas com grande volume de resultados.

⚠️ **Veracidade das informações:** o texto gerado por IA pode conter informações imprecisas ou incompletas. Use sempre como apoio à análise, validando com a fonte original.

## Como configurar

### 1. Providers

Provedores de build disponíveis: `openai`, `gemini`, `claude`.

💡 O Azure OpenAI utiliza o mesmo SDK do OpenAI e não possui um pacote dedicado.

### 2. Crie a variável com a chave de API no Airflow

Acesse [http://localhost:8080/variable/list/](http://localhost:8080/variable/list/) e crie uma variável com a chave do provedor escolhido. O nome é livre — você vai referenciá-lo no YAML pelo campo `api_key_var` (passo 3):

| Provedor | Variável sugerida |
|---|---|
| OpenAI | `OPENAI_API_KEY` |
| Gemini | `GEMINI_API_KEY` |
| Claude (Anthropic) | `ANTHROPIC_API_KEY` |

Para **Azure**, além da chave de API, são necessárias três variáveis adicionais:

| Variável | Descrição |
|---|---|
| `AZURE_OPENAI_ENDPOINT` | URL do endpoint do Azure OpenAI |
| `AZURE_OPENAI_API_VERSION` | Versão da API |
| `AZURE_OPENAI_DEPLOYMENT` | Nome do deployment do modelo |
| `AZURE_OPENAI_API_KEY` | Chave de API do Azure OpenAI |

Crie-as automaticamente com:

```bash
make create-azure-openai-variables
```

### 3. Configure o YAML da DAG

Adicione `ai_config` no nível da DAG — ele aponta o provedor e a variável com a chave — e `ai_search_config` dentro de `search`, que liga o resumo e ajusta seus parâmetros:

```yaml
dag:
  id: exemplo_com_ia
  description: DAG de exemplo com resumo por IA
  ...

  ai_config:
    provider: openai  # openai | gemini | claude | azure
    api_key_var: OPENAI_API_KEY
    model: gpt-4o-mini

  search:
    sources:
      - INLABS
    terms:
      - concurso público
    ai_search_config:
      use_ai_summary: True
      ai_pub_limit: 5
      ai_custom_prompt: |
        Você é um assistente que cria resumos concisos de publicações oficiais.
```

⚠️ **Atenção:** `ai_search_config` fica dentro de `search`, no mesmo nível de `terms`/`sources` — não é o mesmo bloco que `ai_config` (que fica no nível da DAG).

## Referência de parâmetros

### `ai_config` (nível da DAG — obrigatório se `use_ai_summary: True`)

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `provider` | Sim | `openai`, `gemini`, `claude` ou `azure` |
| `api_key_var` | Sim | Nome da variável do Airflow que contém a chave de API |
| `model` | Sim | Modelo suportado pelo provedor (ex: `gpt-4o-mini`) |
| `temperature` | Não | 0.0 a 1.0. Default: `0.2`. Valores baixos deixam a resposta mais determinística; valores altos, mais variada |
| `max_tokens` | Não | Máximo de tokens na resposta da IA. Default: `200` |

### `ai_search_config` (dentro de `search`)

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `use_ai_summary` | Não | Habilita o resumo por IA. Default: `False` |
| `ai_pub_limit` | Não | Máximo de publicações resumidas por execução da DAG. Default: `10` |
| `ai_custom_prompt` | Não | Prompt customizado enviado à IA (veja o padrão abaixo) |
| `temperature` | Não | Mesmo efeito do `temperature` de `ai_config`. Default: `0.2` |
| `max_tokens` | Não | Mesmo efeito do `max_tokens` de `ai_config`. Default: `200` |

### Prompt padrão

```
Você é um assistente especializado em análise de
publicações do Diário Oficial da União (DOU).
Resuma o texto em uma única frase objetiva, fiel ao conteúdo original, em português brasileiro.

Inclua o termo "{}" no texto.

O resumo deve focar em:
- órgão responsável
- tipo de ato
- ação principal

Não invente informações. Não use markdown. Retorne apenas a frase.
```

### Observação

O parâmetro `use_summary` (recurso separado do INLABS, que exibe a ementa da publicação quando ela existe) tem prioridade sobre o resumo por IA: se a publicação já tem ementa, ela é exibida no lugar do resumo gerado por IA; o resumo por IA só é gerado para as publicações sem ementa.
