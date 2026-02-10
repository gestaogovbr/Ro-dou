# Parâmetros de pesquisa disponíveis

A página abaixo lista os parâmetros configuráveis nos arquivos YAML:

## Parâmetros da DAG
* **id**: Nome identificador da DAG a ser gerada.
* **description**: Descrição da DAG de pesquisa.
* **doc_md**: Documentação em markdown da DAG para uma descrição mais completa.
* **schedule**: Agendamento da periodicidade de execução da DAG. Padrão cron (0 8 * * MON-FRI)
* **dataset**: Agendamento da DAG baseado na atualização de um Dataset do Airflow. Em conjunto com o schedule a execução é condicionada ao schedule e dataset.
* **callback**: Notificações técnicas do sistema.
  * **on_failure_callback**: Lista de email para recebimento de avisos de falhas nas execuções da DAG.
* **tags**: Tags para categorizar a DAG.
* **owner**: Responsável pela DAG.

## Parâmetros da Pesquisa (Search)

* **search**: Pode ser uma ou uma lista de pesquisas.
- **date**: Intervalo de data para busca. Valores: DIA, SEMANA, MES, ANO. Default: DIA
- **department**: Lista de unidades a serem filtradas na busca. O nome deve ser idêntico ao da publicação.
- **department_ignore**: Lista de unidades e subordinadas a serem desconsideradas na busca. O nome deve ser idêntico ao da publicação.
- **terms_ignore**: Lista de termos serem desconsideradas na busca. O nome deve ser idêntico ao da publicação. **(O recurso esta disponível para DOU (limitado ao excerto) e INLABS)**
- **dou_sections**: Lista de seções do DOU onde a busca deverá ser realizada. Valores aceitos: SECAO_1, SECAO_2, SECAO_3, EDICAO_EXTRA, EDICAO_SUPLEMENTAR, TODOS.
- **field**: Campos dos quais os termos devem ser pesquisados. Valores: TUDO, TITULO, CONTEUDO. Default: TUDO
- **force_rematch**: Indica que a busca deve ser forçada, mesmo que já tenha sido feita anteriormente. Valores: True ou False.
- **full_text**: Define se no relatório será exibido o texto completo, ao invés de um resumo. Valores: True ou False. Default: False. (Funcionalidade disponível apenas no INLABS)
- **text_length**: Tamanho do texto que será enviado na mensagem. O padrão é 400.
- **use_summary**: Define se no relatório será exibido a ementa, se existir. Valores: True ou False. Default: False. (Funcionalidade disponível apenas no INLABS)
- **ignore_signature_match**: Ignora a correspondência de assinatura ao realizar a busca. Valores: True ou False. Default: False.
- **is_exact_search**: Busca somente o termo exato. Valores: True ou False. Default: True.
- **pubtype**: Lista de tipos de publicações a serem filtradas na busca. Valores: [Lista de tipos de publicações](tipos_de_publicacoes.md).
- **sources**: Fontes de pesquisa dos diários oficiais. Pode ser uma ou uma lista. Opções disponíveis: DOU, QD, INLABS.
- **terms**: Lista de termos a serem buscados. Para o INLABS podem ser utilizados operadores avançados de busca.
- **territory_id**: Lista de identificadores do id do município. Necessário para buscar no Querido Diário. Este parâmetro só deve ser utilizado exclusivamente quando a fonte de dados for o Querido Diário-QD
- **excerpt_size**: Número máximo de caracteres exibidos no trecho onde o termo de busca foi localizado. (Funcionalidade disponível apenas no Querido Diário-QD)
- **number_of_excerpts**: Número máximo de ocorrências do termo de busca em uma mesma edição. (Funcionalidade disponível apenas no Querido Diário-QD)

## Parâmetros do Relatório (Report)
- **attach_csv**: Anexar no email o resultado da pesquisa em CSV.
- **discord_webhook**: URL de Webhook para integração com o Discord.
- **notification**: Integração com aplicativos de mensagens via [Apprise](https://github.com/caronc/apprise).
- **emails**: Lista de emails dos destinatários.
- **footer_text**: Texto em HTML do rodapé do relatório.
- **header_text**: Texto em HTML de cabeçalho do relatório.
- **hide_filters**: Omite no relatório os filtros de pesquisa.
- **no_results_found_text**: Texto padrão para quando não há resultados encontrados. Default: Nenhum dos termos pesquisados foi encontrado nesta consulta.
- **report**: Parâmetros de notificação de relatório.
- **skip_null**: Dispensa o envio de email quando não há resultados encontrados em todas as pesquisas. Valores: True ou False. Default: True.
- **slack_webhook**: URL de Webhook para integração com o Slack.
- **subject**: Texto de assunto do email.

## Como utilizar Slack ou Discord para envio do clippings

Baseado no que foi visto anteriormente nesta seção, o vídeo abaixo demonstra como utilizar outras plataformas para envio dos clippings de pesquisa:

<iframe width="560" height="315" src="https://www.youtube.com/embed/nHV_eH91fKE?si=6ezax8UaQjbkrSKr" title="Utilizando o Slack ou Discord para envio do clipping" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Como filtrar por unidade ou por tipo de publicação

O vídeo abaixo demonstra como refinar as buscas utilizando os filtros de unidade e tipo de publicação.

<iframe width="560" height="315" src="https://www.youtube.com/embed/3I_wXZ_EUBg?si=qZnzljgo3akGFCpY" title="yFiltro por unidade e por tipo de publicação" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

## Como criar múltiplas buscas

O vídeo abaixo demonstra como criar DAGs com múltiplas buscas (search) no mesmo arquivo

<iframe width="560" height="315" src="https://www.youtube.com/embed/HazhpYuComw?si=daHkk0epEe8CK7Ms" title="Criando uma DAG com múltiplas pesquisas" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

