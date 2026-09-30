# Enriquecimento com GLiNER2

O Ro-DOU pode enriquecer as publicações do INLABS indexadas no OpenSearch com **entidades nomeadas** extraídas pelo modelo [GLiNER2](https://github.com/fastino-ai/GLiNER2): pessoas, órgãos, cargos, códigos de cargo, localidades, processos, matrículas e atos normativos. As entidades ficam gravadas no próprio documento do índice `dou`, nos campos `entities.<tipo>`, e podem ser usadas em consultas e análises.

O recurso é **opcional** e fica desligado por padrão. Ele só se aplica quando o backend de busca do INLABS é o OpenSearch (`RO_DOU_INLABS_USE_OPENSEARCH = True`).

## Como funciona

O modelo roda em um **serviço HTTP dedicado** (`gliner_service/`), separado do Airflow. Assim a imagem do Airflow continua sem PyTorch, e o serviço pode ser dimensionado à parte (inclusive com GPU).

1. A DAG `ro-dou_inlabs_load_pg` carrega e indexa as publicações do dia e publica os assets `inlabs` / `inlabs_edicao_extra`.
2. Os mesmos assets disparam a DAG `ro-dou_inlabs_gliner_enrich`, **em paralelo** às DAGs de clipping. O enriquecimento nunca atrasa o envio dos relatórios.
3. A DAG consulta o serviço (`/info`), cria os campos de entidades no mapeamento do índice e seleciona as publicações da data que ainda precisam ser enriquecidas.
4. Os textos são enviados em lotes ao serviço (`/extract`). O resultado é gravado por **atualização parcial**: os campos da indexação original não são alterados.

Cada publicação enriquecida guarda também os metadados em `gliner`:

| Campo | Conteúdo |
|---|---|
| `gliner.fingerprint` | Impressão digital da configuração do serviço (modelo, entidades, limiares, chunking) |
| `gliner.text_hash` | Hash do `texto_plain` processado |
| `gliner.model` | Modelo utilizado |
| `gliner.enriched_at` | Data e hora do enriquecimento (UTC) |

Uma publicação só é reprocessada quando ainda não foi enriquecida, quando o texto mudou ou quando a configuração do serviço mudou. Com isso, retries, a execução da edição extra e novas execuções para a mesma data retomam apenas o que falta.

A indexação do INLABS passou a usar `update` com `doc_as_upsert`. Recarregar uma data não apaga as entidades já extraídas.

A indexação também grava `texto_plain_hash`, o hash do `texto_plain`. Para saber quais publicações estão pendentes, a DAG compara esse campo com `gliner.text_hash` sem baixar os textos. Publicações indexadas antes da criação desse campo e já enriquecidas têm o texto consultado para a comparação.

## Habilitando no ambiente local

1. Suba o serviço. A primeira construção baixa o PyTorch (CPU), e a primeira inicialização baixa o modelo do Hugging Face para o volume `gliner-models`. Isso pode levar alguns minutos.

    ```bash
    make gliner-up
    ```

2. Defina as variáveis do Airflow que habilitam o enriquecimento:

    ```bash
    make create-gliner-variables
    ```

    O comando define (criando ou atualizando):

    | Variável | Valor |
    |---|---|
    | `RO_DOU_INLABS_USE_OPENSEARCH` | `True` |
    | `RO_DOU_GLINER_ENABLED` | `True` |
    | `RO_DOU_GLINER_SERVICE_URL` | `http://gliner:8000` |

    Isso também passa a buscar do INLABS no OpenSearch em vez do PostgreSQL. As variáveis podem ainda ser definidas manualmente em [http://localhost:8080/variable/list/](http://localhost:8080/variable/list/).

3. A DAG `ro-dou_inlabs_gliner_enrich` roda automaticamente após cada carga do INLABS. Para enriquecer uma data já carregada, dispare a DAG manualmente: a data de referência é a data lógica da execução.

Para desligar o serviço: `make gliner-down`.

### Variáveis do Airflow

Todas podem ser definidas como variável do Airflow ou como variável de ambiente de mesmo nome. A variável do Airflow tem precedência.

| Variável | Padrão | Descrição |
|---|---|---|
| `RO_DOU_GLINER_ENABLED` | `false` | Liga o enriquecimento. Também exige `RO_DOU_INLABS_USE_OPENSEARCH = True`. |
| `RO_DOU_GLINER_SERVICE_URL` | `http://gliner:8000` | Endereço do serviço (somente `http`/`https`). |
| `RO_DOU_GLINER_API_TOKEN` | *(vazio)* | Token enviado como `Authorization: Bearer`. Obrigatório quando o serviço define `GLINER_API_TOKEN`. |
| `RO_DOU_GLINER_TIMEOUT` | `600` | Timeout, em segundos, de cada requisição ao serviço. |

## Configuração do serviço

O serviço lê o arquivo [`gliner_service/config.yaml`](https://github.com/gestaogovbr/Ro-dou/blob/main/gliner_service/config.yaml). Para usar outro arquivo, monte-o no contêiner e aponte a variável de ambiente `GLINER_CONFIG_PATH` para ele.

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `model` | `fastino/gliner2.5-multi-v1` | Modelo no Hugging Face Hub ou diretório local com o checkpoint (ambientes sem internet). |
| `revision` | commit fixado | Commit do modelo no Hub. O arquivo padrão fixa um commit para que o modelo baixado não mude sem revisão. |
| `threshold` | `0.45` | Confiança mínima usada pelo modelo. |
| `min_confidence` | `0.0` | Filtro adicional antes de responder. |
| `chunk_size` / `chunk_overlap` | `384` / `64` | Tamanho e sobreposição, em palavras, dos trechos de textos longos. |
| `batch_size` | `8` | Trechos inferidos por vez. |
| `max_text_chars` | `100000` | Textos maiores são truncados. |
| `max_entities_per_type` | `200` | Valores distintos devolvidos por tipo de entidade. |
| `max_texts_per_request` | `32` | Textos aceitos por requisição a `/extract`. |
| `max_chars_per_request` | `100000` | Soma máxima de caracteres por requisição a `/extract` (deve ser ≥ `max_text_chars`). A DAG divide os lotes para respeitar esse limite. |
| `entities` | ver arquivo | Tipos de entidade e suas descrições em linguagem natural. Os nomes aceitam apenas letras minúsculas, dígitos e `_`. |

Alterar o modelo, as entidades, os limiares ou o chunking muda a impressão digital da configuração. Na execução seguinte, as publicações da data processada são reenriquecidas.

Se um tipo de entidade for removido da configuração, os valores antigos desse tipo **permanecem** nos documentos: nem o reenriquecimento nem a recarga do INLABS os apagam. Para removê-los, use um `_update_by_query` no índice.

### Variáveis de ambiente do serviço

| Variável | Descrição |
|---|---|
| `GLINER_CONFIG_PATH` | Caminho do arquivo de configuração. |
| `GLINER_API_TOKEN` | Quando definida, `/info` e `/extract` exigem `Authorization: Bearer <token>`. No Compose, defina-a no arquivo `gliner_service/.env` (opcional e não versionado), que o serviço `gliner` carrega via `env_file`. |
| `HF_HOME` | Cache do Hugging Face (`/models` na imagem). |

## Consultando as entidades

Exemplo de consulta às publicações de uma data que citam um órgão:

```json
GET dou/_search
{
  "query": {
    "bool": {
      "filter": [{ "range": { "pubdate": { "gte": "2026-09-29", "lte": "2026-09-29" } } }],
      "must": [{ "match_phrase": { "entities.organization": "Agência Nacional de Mineração" } }]
    }
  }
}
```

Para comparações exatas e agregações, use o subcampo `.keyword` (ex.: `entities.process.keyword`).

## Desempenho e dimensionamento

A inferência é o gargalo. Em CPU, uma publicação longa pode levar dezenas de segundos ou mais. Antes de habilitar em produção:

- meça o tempo por publicação com dados reais do seu ambiente;
- lembre que todas as publicações da data (todas as seções) são sempre enriquecidas; confira se o tempo total cabe no timeout da tarefa;
- considere executar o serviço com GPU. A imagem padrão instala o PyTorch para CPU; use os argumentos de build `TORCH_INDEX_URL`/`TORCH_VERSION` para outra variante.

O serviço atende uma requisição de inferência por vez. A tarefa de enriquecimento tem timeout de 8 horas e grava o progresso a cada lote. Quando um lote falha (timeout, erro HTTP), as publicações dele são reenviadas uma a uma. As que falharem sozinhas são registradas no log, o restante segue normalmente, e a tarefa termina com erro para que o retry do Airflow reprocesse apenas o que faltou.

Se várias cargas do INLABS ocorrerem enquanto uma execução longa está ativa, a execução seguinte recebe os eventos agrupados e enriquece todas as datas envolvidas.

## Segurança e privacidade

- O modelo roda **localmente** no serviço: o conteúdo das publicações não é enviado a terceiros. Apenas o download do modelo acessa o Hugging Face Hub. Para ambientes isolados, aponte `model` para um diretório local.
- O `docker-compose.yml` não publica a porta do serviço no host: ele só é acessível pela rede interna do Compose. A documentação interativa (`/docs`, `/openapi.json`) é desabilitada, e corpos de requisição acima do limite são recusados antes de serem lidos. Em qualquer ambiente compartilhado, defina `GLINER_API_TOKEN` no serviço e `RO_DOU_GLINER_API_TOKEN` no Airflow e restrinja o acesso de rede ao serviço.
- As publicações são públicas, mas as entidades extraídas incluem nomes e matrículas de pessoas. Aplique ao índice as mesmas regras de acesso e retenção adotadas para o texto das publicações, conforme a LGPD e as políticas do órgão.
