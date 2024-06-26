# Parâmetros de pesquisa disponíveis

A página abaixo lista os parâmetros configuráveis nos arquivos YAML:

## Parâmetros da DAG
* **id**: o nome identificador da DAG a ser gerada.
* **description**: descrição da DAG de pesquisa.
* **doc_md**: documentação em markdown da DAG para uma descrição mais completa.
* **schedule**: agendamento da periodicidade de execução da DAG. Padrão cron (0 8 * * MON-FRI)
* **tags**: tags para categorizar a DAG.
* **owner**: responsável pela DAG.

## Parâmetros da Pesquisa (Search)
* **search**: pode ser uma ou uma lista de pesquisas.
- **date**: intervalo de data para busca. Valores: DIA, SEMANA, MES, ANO. Default: DIA
- **department**: lista de unidades a serem filtradas na busca. O nome deve ser idêntico ao da publicação.
- **dou_sections**: lista de seções do DOU onde a busca deverá ser realizada. Valores aceitos: SECAO_1, SECAO_2, SECAO_3, EDICAO_EXTRA, EDICAO_SUPLEMENTAR, TODOS.
- **field**: campos dos quais os termos devem ser pesquisados. Valores: TUDO, TITULO, CONTEUDO. Default: TUDO
- **force_rematch**: indica que a busca deve ser forçada, mesmo que já tenha sido feita anteriormente. Valores: True ou False.
- **full_text**: define se no relatório será exibido o texto completo, ao invés de um resumo. Valores: True ou False. Default: False.
- **ignore_signature_match**: ignora a correspondência de assinatura ao realizar a busca. Valores: True ou False. Default: False.
- **is_exact_search**: busca somente o termo exato. Valores: True ou False. Default: True.
- **sources**: fontes de pesquisa dos diários oficiais. Pode ser uma ou uma lista. Opções disponíveis: DOU, QD, INLABS.
- **terms**: lista de termos a serem buscados. Para o INLABS podem ser utilizados operadores avançados de busca.
- **territory_id**: identificador do id do município. Necessário para buscar no Querido Diário.

## Parâmetros do Relatório (Report)
- **attach_csv**: Anexar no email o resultado da pesquisa em CSV.
- **discord_webhook**: URL de Webhook para integração com o Discord.
- **emails**: Lista de emails dos destinatários.
- **footer_text**: Texto em HTML do rodapé do relatório.
- **header_text**: Texto em HTML de cabeçalho do relatório.
- **hide_filters**: Omite no relatório os filtros de pesquisa.
- **no_results_found_text**: Texto padrão para quando não há resultados encontrados. Default: Nenhum dos termos pesquisados foi encontrado nesta consulta.
- **report**: parâmetros de notificação de relatório.
- **skip_null**: Dispensa o envio de email quando não há resultados encontrados em todas as pesquisas. Valores: True ou False. Default: True.
- **slack_webhook**: URL de Webhook para integração com o Slack.
- **subject**: Texto de assunto do email.

