## Instalação e configuração

**⚠️Observação:** Para instalar e executar este projeto no Windows, recomenda-se utilizar o [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/pt-br/windows/wsl/).   Certifique-se de que o WSL está devidamente instalado e configurado em seu sistema antes de prosseguir com oa passos de instalação, certifique-se também de habilitar o [docker no WSL](https://learn.microsoft.com/pt-br/windows/wsl/tutorials/wsl-containers)

* [Como instalar e configurar o WSL](instalacao_wsl_windows.md)
* [Como habilitar no docker no WSL](habilitacao_docker_no_wsl.md)

### Configurando o ambiente local (desenvolvimento)

#### Requisitos

* 4Gb de memória RAM
* 2Gb de espaço em disco
* Sistema operacional Linux ou Windows com WSL

O código-fonte está disponibilizado no <a href="https://github.com/gestaogovbr/Ro-dou"><img src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" style="vertical-align: middle; display: inline-block;"></a> perfil do GitHub do Ministério da Gestão e da Inovação em Serviços Públicos.


Neste título, fornecemos abaixo uma configuração demonstrativa para que você possa executar o Ro-DOU no seu computador.

Passo a passo:

1. Instalar na máquina o Docker e Docker Compose (versão 1.29 ou superior):

    [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/)

2. Clonar o repositório do código no Github
[https://github.com/gestaogovbr/Ro-dou](https://github.com/gestaogovbr/Ro-dou). Abra o terminal e execute os comandos abaixo:

```bash
git clone https://github.com/gestaogovbr/Ro-dou
cd Ro-Dou
```

3. O repositório já vem com comandos pré-definidos no Makefile para facilitar a execução.

**Para iniciar o sistema, execute:**

```bash
make run
```

**💡 Dica:** Este comando irá inicializar todos os serviços necessários do projeto.

Você deverá ver uma saída similar a esta:

!['makerun.png'](https://raw.githubusercontent.com/gestaogovbr/Ro-dou/8edc3e3d567a4d2f182100db103316dc312fb241/docs/img/makerunwsl.png)


**Observação:** Ao executar o comando, você verá uma mensagem confirmando a criação das variáveis de ambiente e das conexões. Caso não sejam criadas automaticamente, você pode executar cada função individualmente a partir do arquivo `Makefile`.

Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários.

Como observado na imagem, após executar o comando no terminal e efetura o build dos containers, ele também iniciará as conexões com os ambientes necessários automaticamente! No exemplo representado pela imagem, os containers e conexões já foram criados, e por isso o retorno das mensagens:

```bash
psql:/sql/init-db.sql:1: ERROR:  database "inlabs" already exists
psql:/sql/init-db.sql:5: NOTICE:  schema "dou_inlabs" already exists, skipping
psql:/sql/init-db.sql:35: NOTICE:  relation "article_raw" already exists, skipping
```

Ao ser executado pela primeira vez a mensagem retornada será:

```bash
Creating 'inlabs' database
Creating 'dou_inlabs' schema
```

1. Verificar se o serviço do Airflow, no qual o Ro-DOU depende, está acessível via navegador, acessando:

    [http://localhost:8080/](http://localhost:8080/)

O Apache Airflow, que também é usado para rodar o Ro-DOU, pode demorar alguns minutos para se configurar na primeira vez. Para se autenticar e acessar o Apache Airflow, entre no link e utilize login `airflow` e senha `airflow`.

5. Ativar a DAG de clipping:

Na tela inicial do Airflow, são fornecidos clippings de exemplo. A partir dos arquivos YAML (.yaml) do diretório `dag_confs/`, é possível manipular e customizar as pesquisas de clipping desejadas nos diários oficiais. Dentro dos arquivos YAML, é possível, por exemplo, definir palavras-chave de busca e um endereço de e-mail para recebimento de uma mensagem com os resultados da busca no(s) diário(s) oficial(is).

Para executar qualquer DAG do Airflow, é necessário ligá-la. Inicialmente, todas as DAGs ficam pausadas por padrão. Sugerimos começar testando o clipping **all_parameters_example**. Utilize o botão _toggle_ para ligá-lo. Após ativá-lo, o Airflow executará a DAG uma única vez. Clique no [nome da DAG](http://localhost:8080/tree?dag_id=all_parameters_example)
para visualizar o detalhe da execução.

Você observará que, tanto na visualização em árvore (**Tree**) como na visualização em Grafo (**Graph**) dentro do Apache Airflow, é possível constatar se houve algum resultado encontrado na API da Imprensa Nacional para os termos e demais parâmetros deste clipping. Se a tarefa chamada **"send_report"** estiver na cor verde, significa que foi encontrado um resultado e que uma mensagem de e-mail foi enviada para o endereço configurado no arquivo YAML.

6. Visualizar clipping:

Para visualizar a mensagem de e-mail, acesse o endereço http://localhost:5001/. Este é um serviço que simula uma caixa de e-mail (servidor SMTP) para fins de experimentação. **_Voilà!_**.

7. Opcional: Configurando o INLABS como fonte de dados:

**Observação:** Para utilizar o `source: - INLABS`, é necessário alterar a conexão `inlabs_portal` no Apache Airflow, apontando o usuário e senha de autenticação do portal. Um novo usuário pode ser cadastrado pelo portal [INLABS](https://inlabs.in.gov.br/acessar.php). A DAG
que realiza o download dos arquivos do INLABS é a **ro-dou_inlabs_load_pg**.

8. Desligando o ambiente:

Quando tiver terminado de utilizar o ambiente de teste do Ro-DOU, desligue-o por meio do seguinte comando:

```bash
make down
```

### Configurando o ambiente de produção

#### Requisitos

* 4Gb de memória RAM
* 2Gb de espaço em disco
* Sistema operacional Linux ou Windows com WSL
* Docker

Para instalação em um cluster kubernetes, [clique aqui](instalacao_k8s.md)


1. Clonar o repositório do código no Github
[https://github.com/gestaogovbr/Ro-dou](https://github.com/gestaogovbr/Ro-dou). Abra o terminal e execute os comandos abaixo:

```bash
git clone https://github.com/gestaogovbr/Ro-dou
cd Ro-Dou
```
Para utilizar o Ro-DOU em ambiente de produção, é necessário que o servidor tenha disponível um serviço SMTP que será utilizado pelo Apache Airflow para envio de mensagens de e-mail pela Internet, ou configurar um webhook com Slack ou Discord. Siga os seguintes passos:

2. Utilize as credenciais do serviço SMTP (host, usuário, senha, porta etc.)
para editar o arquivo `docker-compose.yml`, substituindo as variáveis referentes ao serviço SMTP, a exemplo de `AIRFLOW__SMTP__SMTP_HOST`.

3. Ao final do arquivo `docker-compose.yml`, remova as linhas que declaram o serviço **smtp4dev**, uma vez que ele não será mais necessário.

4. O repositório já vem com comandos pré-definidos no Makefile. Para rodar o sistema, basta:

```bash
make run
```
Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários.

5. Opcional: Configurando o INLABS como fonte de dados:

**Observação:** Para utilizar o `source: - INLABS`, é necessário alterar a conexão `inlabs_portal` no Apache Airflow, apontando o usuário e senha de autenticação do portal. Um novo usuário pode ser cadastrado pelo portal [INLABS](https://inlabs.in.gov.br/acessar.php). A DAG
que realiza o download dos arquivos do INLABS é a **ro-dou_inlabs_load_pg**.