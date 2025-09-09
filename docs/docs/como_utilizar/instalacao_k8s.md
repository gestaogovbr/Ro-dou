# Ro-dou on Kubernetes

Instruções para subir o Ro-DOU em um cluster kubernetes 🚀🚀🚀

## Helm deploy

Em breve...

## Manual deployment

1. Deploy do PostgreSQL
   1. Sobe os secrets e o statefulset
   ```
   kubectl apply -f postgres/postgres-secrets.yml
   kubectl apply -f postgres/postgres-deployment.yml
   ```
   2. Cria o banco de dados para o INLABS
   ```
   kubectl apply -f postgres/postgres-inlabsdb-configmap.yml
   kubectl apply -f postgres/postgres-createinlabsdb-job.yml
   ```

2. Deploy do Airflow
   1. Cria um volume PVC para a pasta de logs
   ```
    kubectl apply -f airflow/airflow-pvc.yml
   ```
   2. Sobe as variáveis de ambiente.
   ```
   kubectl apply -f airflow/airflow-configmap.yml
   ```
   3. Edite o arquivo secrets
   - Criar um usuário no portal
   https://inlabs.in.gov.br/acessar.php e incluir as credenciais no arquivo
   airflow/airflow-secrets.yml
   - Alterar as configurações referente ao servidor do email (SMTP)
   ```
   kubectl apply -f airflow/airflow-secrets.yml
   ```
   1. Inicializar o banco do airflow
   ```
   kubectl apply -f airflow/airflow-init-db-job.yml
   ```
   2. Subir os serviços do airflow
   ```
   kubectl apply -f airflow/airflow-scheduler-deployment.yml
   kubectl apply -f airflow/airflow-web-deployment.yml
   ```
   3. Criar usuário admin do airflow
   ```
   kubectl apply -f airflow/airflow-upgrade-db-job.yml
   ```
   4. Criar a conexão com o INLABS
   ```
   kubectl apply -f airflow/airflow-create-inlabs-conn-job.yml
   ```
3. Deploy do SMTP4dev (Opcional - para testes de envio de email)
   1. kubectl -f apply smtp4dev/smtp4dev-deployment.yml
   2. Para acessar o smtp4dev pode utilizar o comando:
   ```
   kubectl -n airflow-rodou port-forward  service/smtp4dev 5001:5001
   ```
4. Para acessar a interface web sem ainda ter um host pode usar o port-forward:
   ```
   kubectl port-forward service/airflow-webserver 8080:8080
   ```
   Acessar no navegador o endereço localhost:8080
   Usuário admin@example.com / Senha admin

5. Para poder criar suas próprias buscas, o ideal é criar um script para sincronizar a partir
   de um repositório do github com as buscas criadas com a pasta dag_confs.