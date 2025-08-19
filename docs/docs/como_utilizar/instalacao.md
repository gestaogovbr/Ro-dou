## Instalação e configuração

**⚠️Observação:** Para instalar e executar este projeto no Windows, recomenda-se utilizar o [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/pt-br/windows/wsl/).   Certifique-se de que o WSL está devidamente instalado e configurado em seu sistema antes de prosseguir com oa passos de instalação, certifique-se também de habilitar o [docker no WSL](https://learn.microsoft.com/pt-br/windows/wsl/tutorials/wsl-containers)

* [Como instalar e configurar o WSL](instalacao_wsl_windows)
* [Como habilitar no docker no WSL](habilitacao_docker_no_wsl.md)

### Configurando o ambiente local (desenvolvimento)

#### Requisitos

* 4Gb de memória RAM
* 2Gb de espaço em disco
* Sistema operacional Linux ou Windows com WSL

O código-fonte está disponibilizado no [perfil do GitHub do Ministério da Gestão e da Inovação em Serviços Públicos](https://github.com/gestaogovbr/Ro-dou).

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

3. O repositório já vem com comandos pré-definidos no Makefile. Para rodar o sistema, basta:

```bash
make run
```

Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários.

4. Verificar se o serviço do Airflow, no qual o Ro-DOU depende, está acessível via navegador, acessando:

    [http://localhost:8080/](http://localhost:8080/)

O Apache Airflow, que também é usado para rodar o Ro-DOU, pode demorar alguns minutos para se configurar na primeira vez. Para se autenticar e acessar o Apache Airflow, entre no link e utilize login `airflow` e senha `airflow`.

5. Ativar a DAG de clipping:

Na tela inicial do Airflow, são fornecidos clippings de exemplo. A partir dos arquivos YAML (.yaml) do diretório `dag_confs/`, é possível manipular e customizar as pesquisas de clipping desejadas nos diários oficiais. Dentro dos arquivos YAML, é possível, por exemplo, definir palavras-chave de busca e um endereço de e-mail para recebimento de uma mensagem com os resultados da busca no(s) diário(s) oficial(is).

Para executar qualquer DAG do Airflow, é necessário ligá-la. Inicialmente, todas as DAGs ficam pausadas por padrão. Sugerimos começar testando o clipping **all_parameters_example**. Utilize o botão _toggle_ para ligá-lo. Após ativá-lo, o Airflow executará a DAG uma única vez. Clique no [nome da DAG](http://localhost:8080/tree?dag_id=all_parameters_example)
para visualizar o detalhe da execução.

Você observará que, tanto na visualização em árvore (**Tree**) como na visualização em Grafo (**Graph**) dentro do Apache Airflow, é possível constatar se houve algum resultado encontrado na API da Imprensa Nacional para os termos e demais parâmetros deste clipping. Se a tarefa chamada **"send_report"** estiver na cor verde, significa que foi encontrado um resultado e que uma mensagem de e-mail foi enviada para o endereço configurado no arquivo YAML.

6. Visualizar clipping:

Para visualizar a mensagem de e-mail, acesse o endereço http://localhost:5001/. Este é um serviço que simula uma caixa de e-mail (servidor SMTP) para fins de experimentação. **_Voilà!_**.

### Configuração SMTP e uso rápido para testes

As configurações sensíveis (SMTP, senhas, chaves) devem ser definidas em um arquivo `.env` na raiz do projeto, seguindo o modelo em `.env.example`. Evite editar `docker-compose.yml` diretamente para inserir segredos.

Se precisar testar envio de e‑mails localmente, há um serviço de desenvolvimento opcional (`smtp4dev`). Ele é apenas para testes; não é necessário para executar o sistema. Para ativá‑lo rapidamente use um dos comandos abaixo:

```bash
# via Makefile helper
make smtp4dev-up

# ou diretamente com docker compose (opcional)
docker compose --profile dev up -d smtp4dev
```

No `.env` local (copiado de `.env.example`) você pode apontar:

```ini
#AIRFLOW__SMTP__SMTP_HOST=smtp4dev
#AIRFLOW__SMTP__SMTP_PORT=25
#AIRFLOW__SMTP__SMTP_MAIL_FROM='airflow@example.local'
```

Em produção, defina as mesmas variáveis apontando para o servidor SMTP real e não ative o profile `dev`.

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



1. Clonar o repositório do código no Github
[https://github.com/gestaogovbr/Ro-dou](https://github.com/gestaogovbr/Ro-dou). Abra o terminal e execute os comandos abaixo:

```bash
git clone https://github.com/gestaogovbr/Ro-dou
cd Ro-Dou
```
Para utilizar o Ro-DOU em ambiente de produção, é necessário que o servidor tenha disponível um serviço SMTP que será utilizado pelo Apache Airflow para envio de mensagens de e-mail pela Internet, ou configurar um webhook com Slack ou Discord. Siga os seguintes passos:

2. Em produção, forneça as credenciais do serviço SMTP definindo as variáveis correspondentes em um arquivo `.env` (veja `.env.example`) ou no ambiente do servidor. Evite editar `docker-compose.yml` diretamente para inserir segredos.

3. O serviço `smtp4dev` é opcional e apenas para testes locais; em produção mantenha-o desabilitado (não use o profile `dev`).

4. O repositório já vem com comandos pré-definidos no Makefile. Para rodar o sistema, basta:

```bash
make run
```
Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários.

5. Opcional: Configurando o INLABS como fonte de dados:

**Observação:** Para utilizar o `source: - INLABS`, é necessário alterar a conexão `inlabs_portal` no Apache Airflow, apontando o usuário e senha de autenticação do portal. Um novo usuário pode ser cadastrado pelo portal [INLABS](https://inlabs.in.gov.br/acessar.php). A DAG
que realiza o download dos arquivos do INLABS é a **ro-dou_inlabs_load_pg**.