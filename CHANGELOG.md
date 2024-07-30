## Change Log

As principais mudanças realizadas no repositório do [Ro-ou](https://github.com/gestaogovbr/Ro-dou) estão documentadas aqui a partir de 31/08/2023.
## [0.1.3] - 2024-07-25
- Cria a marca d'agua do Ro-DOU no template do email
- Adiciona quebra de linhas no texto no modo full_text (INLABS)
- Corrige bug quando a paginação de resultados é igual a 2 (DOU)

## [0.1.2]
# TODO

## [0.1.1]
# TODO

## [0.1.0] - 2023-08-31

Altera a forma de encontrar os arquivos de configuração das DAGs (`dag_confs/*.yml`).

Antes considerava que a pasta `dag_confs/` estava na mesma raiz que os arquivos do ro-dou em `./src`. Agora o caminho da(s) pasta(s) deve ser informado pela variável de ambiente `RO_DOU__DAG_CONF_DIR` e separado por `:` quando mais de um.

**Exemplo:**

As pastas `/opt/airflow/dags/repo1/dag_confs` e `/opt/airflow/dags/repo2/dag_confs` possuem arquivos de configuração (yaml) para geração das DAGs do rodou. A variável de ambiente `RO_DOU__DAG_CONF_DIR` deve ser atribuída assim:

```shell
RO_DOU__DAG_CONF_DIR=/opt/airflow/dags/repo1/dag_confs:/opt/airflow/dags/repo2/dag_confs
```

Esta alteração permite que os arquivos de configuração das DAGs (`dag_confs/*.yml`) estejam em qualquer pasta da máquina ou container.
## [1.0.0] - 2024-07-30
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec iaculis elementum mi, sed posuere augue. Mauris eget diam eu diam dictum tincidunt sed eget justo. Sed ante justo, luctus accumsan laoreet a, efficitur eget magna. Phasellus luctus neque vitae erat viverra euismod. Aliquam porttitor nisi sodales, vestibulum est nec, volutpat turpis. Aliquam vehicula pulvinar ipsum condimentum ultricies. Praesent faucibus accumsan ultricies. Duis felis justo, faucibus sed aliquet interdum, ornare ut metus. Quisque tortor nisi, tristique in placerat ultrices, dignissim eu nunc. Nulla et nibh congue, fringilla ante vel, viverra nisi. Integer tincidunt erat risus, quis dictum sapien vestibulum sit amet. Mauris massa dui, porttitor vel lectus in, scelerisque tincidunt nisl. Cras faucibus porta purus, pharetra sagittis ex egestas non.

