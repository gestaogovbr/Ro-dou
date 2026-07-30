# Ro-DOU on Kubernetes

Instruções para subir o Ro-DOU em um cluster Kubernetes 🚀🚀🚀

## Helm deploy

Em breve...

## Manual deployment

1. **Deploy do PostgreSQL**

    1. Sobe os secrets e o statefulset:

        ```bash
        kubectl apply -f postgres/postgres-secrets.yml
        kubectl apply -f postgres/postgres-deployment.yml
        ```

    2. Cria o banco de dados para o INLABS:

        ```bash
        kubectl apply -f postgres/postgres-inlabsdb-configmap.yml
        kubectl apply -f postgres/postgres-createinlabsdb-job.yml
        ```

2. **Deploy do Airflow**

    1. Cria um volume PVC para a pasta de logs:

        ```bash
        kubectl apply -f airflow/airflow-pvc.yml
        ```

    2. Sobe as variáveis de ambiente:

        ```bash
        kubectl apply -f airflow/airflow-configmap.yml
        ```

    3. Edite o arquivo `airflow/airflow-secrets.yml`:
        - Crie um usuário no portal [INLABS](https://inlabs.in.gov.br/acessar.php) e inclua as credenciais no arquivo.
        - Altere as configurações referentes ao servidor de e-mail (SMTP).

        Depois, aplique o arquivo:

        ```bash
        kubectl apply -f airflow/airflow-secrets.yml
        ```

    4. Inicialize o banco do Airflow:

        ```bash
        kubectl apply -f airflow/airflow-init-db-job.yml
        ```

    5. Suba os serviços do Airflow:

        ```bash
        kubectl apply -f airflow/airflow-scheduler-deployment.yml
        kubectl apply -f airflow/airflow-web-deployment.yml
        ```

    6. Crie o usuário admin do Airflow:

        ```bash
        kubectl apply -f airflow/airflow-upgrade-db-job.yml
        ```

    7. Crie a conexão com o INLABS:

        ```bash
        kubectl apply -f airflow/airflow-create-inlabs-conn-job.yml
        ```

3. **Deploy do SMTP4dev** (opcional — para testes de envio de e-mail)

    1. Suba o deployment:

        ```bash
        kubectl apply -f smtp4dev/smtp4dev-deployment.yml
        ```

    2. Para acessar o smtp4dev, utilize o comando:

        ```bash
        kubectl -n airflow-rodou port-forward service/smtp4dev 5001:5001
        ```

4. **Acessando a interface web sem um host configurado**

    Use o port-forward:

    ```bash
    kubectl port-forward service/airflow-webserver 8080:8080
    ```

    Acesse [http://localhost:8080](http://localhost:8080) com usuário `admin@example.com` e senha `admin`.

5. **Criando suas próprias buscas**

    Para criar suas próprias buscas, o ideal é criar um script para sincronizar a pasta `dag_confs` a partir de um repositório do GitHub.
