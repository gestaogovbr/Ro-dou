# Integração com Inteligência Artifical Generativa
O Ro-DOU permite a utilização de modelos de inteligência artificial generativa para geração automática de resumos das publicações encontradas no Diário Oficial da União (DOU). A integração se dá com um provedor de IA existente no mercado.

Essa funcionalidade é especialmente útil para reduzir o tempo de análise, destacando rapidamente o conteúdo mais relevante de cada publicação. Além disso, permite a customização do prompt, possibilitando adaptar o formato do resumo conforme a necessidade do usuário — como apresentação em tópicos, nível de detalhamento, tipo de linguagem, entre outros (parâmetro ai_custom_prompt).

Atualmente, são suportados os seguintes provedores de IA:

* OpenAI
* Gemini
* Claude
* Azure

⚠️ **Disponível apenas para a fonte INLABS**

⚠️ **Atenção aos custos**
A utilização de modelos de IA pode gerar custos baseados no consumo de tokens. Recomenda-se verificar junto ao provedor os valores praticados e escolher o modelo mais adequado para o seu cenário.
Para ajudar no controle de custos, ajuste o parâmetro ai_pub_limit, que permite limitar a quantidade de publicações processadas por IA em cada execução. Isso é especialmente importante em buscas com grande volume de resultados.

⚠️ **Veracidade das informações**
O texto gerado por IA pode conter informações inverídicas, imprecisas ou incompletas, devendo ser utilizado apenas como apoio à análise e sempre validado com a fonte original.

## Instalação

As dependências de IA são opcionais e controladas pelo argumento de build `AI_PROVIDERS`. Se nenhum provedor for especificado, as dependências de IA são ignoradas.

```bash
# Build com um provedor
make build AI_PROVIDERS="openai"

# Build com múltiplos provedores
make build AI_PROVIDERS="openai gemini"
```

Provedores disponíveis: `openai`, `gemini`, `claude`.

## Parâmetros da DAG
- **ai_config** *(obrigatório)*: Configurações do provedor de IA (Disponível apenas para INLABS)
- **provider** *(obrigatório)*: Provedor de LLM a ser utilizado. Valores aceitos: `openai`, `gemini`, `claude`, `azure`.
- **api_key_var** *(obrigatório)*: Nome da variável do Airflow que contém a chave de API do provedor.
- **model** *(obrigatório)*: Modelo da API de IA suportado pelo provider. (ex: gpt-4o-mini)
### Observação
Para o provider **Azure**, é necessário configurar, além dos parâmetros acima, as seguintes variáveis no Apache Airflow:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_KEY`
## Parâmetros da Pesquisa (Search)
- **ai_config** *(obrigatório)*: Configurações de IA para geração de resumos automáticos. (Disponível apenas para INLABS)
- **use_ai_summary** *(opcional)*: Habilita a geração de resumos automáticos com IA para as publicações encontradas.
      Valores: `True` ou `False`. Default: `False`. (Disponível apenas para INLABS)
- **ai_pub_limit** *(opcional)*: Número máximo de publicações que serão resumidas por IA na execução da DAG. Default: 5
- **ai_custom_prompt** *(opcional)*: Prompt personalizado enviado ao modelo de IA para orientar a geração dos resumos.
- **temperature** *(opcional)*: Parâmetro de temperature para o gerador de IA. Valores entre 0.0 e 1.
- Valores mais baixos (próximos de 0.0) tornam as respostas mais determinísticas e consistentes.
- Valores mais altos (até 1.0) aumentam a diversidade e criatividade das respostas.
- **max_tokens** *(opcional)*: Número máximo de tokens que podem ser gerados na resposta da IA.
    Default: `200`
### Prompt padrão (default)
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
### Observações
- Caso o use_summary esteja habilitado como True: Será considerado o campo da ementa e não será processado para geração de resumo por IA