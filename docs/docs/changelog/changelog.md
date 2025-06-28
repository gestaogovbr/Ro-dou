
## Changelog

As principais mudanças realizadas no repositório do [Ro-ou](https://github.com/gestaogovbr/Ro-dou) estão documentadas aqui a partir de 31/08/2023.

## [0.1.0] - 2023-08-31

Altera a forma de encontrar os arquivos de configuração das DAGs (`dag_confs/*.yml`).

Antes considerava que a pasta `dag_confs/` estava na mesma raiz que os arquivos do ro-dou em `./src`. Agora o caminho da(s) pasta(s) deve ser informado pela variável de ambiente `RO_DOU__DAG_CONF_DIR` e separado por `:` quando mais de um.

**Exemplo:**

As pastas `/opt/airflow/dags/repo1/dag_confs` e `/opt/airflow/dags/repo2/dag_confs` possuem arquivos de configuração (yaml) para geração das DAGs do rodou. A variável de ambiente `RO_DOU__DAG_CONF_DIR` deve ser atribuída assim:

```shell
RO_DOU__DAG_CONF_DIR=/opt/airflow/dags/repo1/dag_confs:/opt/airflow/dags/repo2/dag_confs
```

Esta alteração permite que os arquivos de configuração das DAGs (`dag_confs/*.yml`) estejam em qualquer pasta da máquina ou container.