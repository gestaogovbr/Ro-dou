# Parâmetros de pesquisa disponíveis

A página abaixo lista os parâmetros configuráveis nos arquivos YAML:

## Parâmetros da DAG
* **id** *(obrigatório)*: Nome identificador da DAG a ser gerada. Deve ser único.
* **description** *(obrigatório)*: Descrição da DAG de pesquisa exibida na interface do Airflow.
* **doc_md** *(opcional)*: Documentação em markdown da DAG para uma descrição mais completa. Pode conter títulos, listas e links.
* **schedule** *(opcional)*: Agendamento da periodicidade de execução da DAG. Use expressão cron (o padrão utilizado pelo gerador é `0 8 * * MON-FRI` quando não informado).
* **dataset** *(opcional)*: Nome de um `Dataset` do Airflow. Se fornecido, a DAG só dispara quando o dataset for atualizado; pode ser combinado com `schedule`.
* **callback** *(opcional)*: Notificações técnicas do sistema.
  * **on_failure_callback**: Lista de e‑mail para recebimento de avisos de falhas nas execuções da DAG.
* **tags** *(opcional)*: Conjunto de tags para categorizar a DAG. Dois valores padrão (`dou` e `generated_dag`) são sempre adicionados automaticamente.
* **owner** *(opcional)*: Lista de responsáveis/owners da DAG, utilizada para filtragem no Airflow.

(Quando uma chave não é informada, é utilizada a configuração padrão definida pelo gerador: veja o código-fonte em `src/schemas.py` para os valores e comportamentos.)

## Parâmetros da Pesquisa (Search)

* **search** *(obrigatório)*: Seção que define um conjunto de filtros a serem executados em sequência. Pode ser uma única pesquisa ou uma lista de pesquisas aninhadas.

Para cada item de `search` aplica‑se o conjunto de parâmetros abaixo. Nem todos precisam ser informados, mas existe uma **validação interna** que exige pelo menos um dos critérios `terms`, `department` ou `pubtype`. Além disso, se `sources` incluir `QD` (Querido Diário), o uso de `terms` torna‑se obrigatório.

- **date** *(opcional)*: Intervalo de data para busca. Valores: DIA, SEMANA, MES, ANO. Default: DIA.
- **department** *(opcional)*: Lista de unidades a serem filtradas na busca. O nome deve ser idêntico ao da publicação.
- **department_ignore** *(opcional)*: Lista de unidades e subordinadas a serem desconsideradas na busca. O nome deve ser idêntico ao da publicação.
- **terms_ignore** *(opcional)*: Lista de termos serem desconsideradas na busca. O nome deve ser idêntico ao da publicação. **(O recurso está disponível para DOU – limitado ao excerto – e INLABS)**
- **dou_sections** *(opcional)*: Lista de seções do DOU onde a busca deverá ser realizada. Valores aceitos: SECAO_1, SECAO_2, SECAO_3, EDICAO_EXTRA, EDICAO_SUPLEMENTAR, TODOS. Default: TODOS.
- **field** *(opcional)*: Campos dos quais os termos devem ser pesquisados. Valores: TUDO, TITULO, CONTEUDO. Default: TUDO.
- **force_rematch** *(opcional)*: Indica que a busca deve ser forçada, mesmo que já tenha sido feita anteriormente. Valores: True ou False. Default: False.
- **full_text** *(opcional)*: Define se no relatório será exibido o texto completo, ao invés de um resumo. Valores: True ou False. Default: False. (Funcionalidade disponível apenas no INLABS)
- **text_length** *(opcional)*: Tamanho do texto que será enviado na mensagem. O padrão é 400. (INLABS)
- **use_summary** *(opcional)*: Define se no relatório será exibido a ementa, se existir. Valores: True ou False. Default: False. (Funcionalidade disponível apenas no INLABS)
- **ignore_signature_match** *(opcional)*: Ignora a correspondência de assinatura ao realizar a busca. Valores: True ou False. Default: False.
- **is_exact_search** *(opcional)*: Busca somente o termo exato. Valores: True ou False. Default: True.
- **pubtype** *(opcional)*: Lista de tipos de publicações a serem filtradas na busca. Valores: [Lista de tipos de publicações](tipos_de_publicacoes.md).
- **sources** *(opcional)*: Fontes de pesquisa dos diários oficiais. Pode ser uma ou uma lista. Opções disponíveis: DOU, QD, INLABS. Default: DOU.
- **terms** *(condicionalmente obrigatório)*: Lista de termos a serem buscados. Para o INLABS podem ser utilizados operadores avançados de busca. Veja nota acima sobre validação: se `QD` estiver na lista de `sources`, os termos são exigidos; caso contrário basta informar pelo menos um dos critérios `terms`, `department` ou `pubtype`.
- **territory_id** *(opcional)*: Lista de identificadores do id do município. Necessário para buscar no Querido Diário. Este parâmetro só deve ser utilizado exclusivamente quando a fonte de dados for o Querido Diário‑QD.
- **excerpt_size** *(opcional)*: Número máximo de caracteres exibidos no trecho onde o termo de busca foi localizado. (Funcionalidade disponível apenas no Querido Diário‑QD)
- **number_of_excerpts** *(opcional)*: Número máximo de ocorrências do termo de busca em uma mesma edição. (Funcionalidade disponível apenas no Querido Diário‑QD)

## Parâmetros do Relatório (Report)
O bloco `report` contém as informações de notificação. Não há validação estrita no esquema, mas **deve existir pelo menos um mecanismo de envio** (por exemplo `emails`, `slack_webhook`, `discord_webhook` ou `notification`).

- **attach_csv** *(opcional)*: Anexar no email o resultado da pesquisa em CSV. Default: False.
- **discord_webhook** *(opcional)*: URL de Webhook para integração com o Discord.
- **notification** *(opcional)*: Integração com aplicativos de mensagens via [Apprise](https://github.com/caronc/apprise).
- **emails** *(opcional)*: Lista de emails dos destinatários. Normalmente ao menos este campo ou um webhook deve ser preenchido.
- **footer_text** *(opcional)*: Texto em HTML do rodapé do relatório.
- **header_text** *(opcional)*: Texto em HTML de cabeçalho do relatório.
- **hide_filters** *(opcional)*: Omite no relatório os filtros de pesquisa. Default: False.
- **no_results_found_text** *(opcional)*: Texto padrão para quando não há resultados encontrados. Default: "Nenhum dos termos pesquisados foi encontrado nesta consulta".
- **skip_null** *(opcional)*: Dispensa o envio de email quando não há resultados encontrados em todas as pesquisas. Valores: True ou False. Default: True.
- **slack_webhook** *(opcional)*: URL de Webhook para integração com o Slack.
- **subject** *(opcional)*: Texto de assunto do email. Se não for fornecido o gerador define um texto padrão.

## Como utilizar Slack ou Discord para envio do clippings

Baseado no que foi visto anteriormente nesta seção, o vídeo abaixo demonstra como utilizar outras plataformas para envio dos clippings de pesquisa:

<iframe width="560" height="315" src="https://www.youtube.com/embed/nHV_eH91fKE?si=6ezax8UaQjbkrSKr" title="Utilizando o Slack ou Discord para envio do clipping" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Como filtrar por unidade ou por tipo de publicação

O vídeo abaixo demonstra como refinar as buscas utilizando os filtros de unidade e tipo de publicação.

<iframe width="560" height="315" src="https://www.youtube.com/embed/3I_wXZ_EUBg?si=qZnzljgo3akGFCpY" title="yFiltro por unidade e por tipo de publicação" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Como criar múltiplas buscas

O vídeo abaixo demonstra como criar DAGs com múltiplas buscas (search) no mesmo arquivo

<iframe width="560" height="315" src="https://www.youtube.com/embed/HazhpYuComw?si=daHkk0epEe8CK7Ms" title="Criando uma DAG com múltiplas pesquisas" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

