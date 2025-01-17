## Instalação e configuração

### Configurando o ambiente local 'Hello World'

O código-fonte está disponibilizado no [perfil do GitHub do Ministério da Gestão e da Inovação em Serviços Públicos](https://github.com/gestaogovbr/Ro-dou).

Neste título, fornecemos abaixo uma configuração demonstrativa para que você possa executar o Ro-DOU no seu computador. Para isso, é necessário ter o Docker Compose na versão 1.29 ou maior instalado. Os passos para a instalação estão disponíveis em [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/) ou em tutoriais no YouTube.

Após clonar o repositório do Ro-DOU para o seu computador com o comando `git clone`, acesse o diretório pelo terminal e execute os comandos a seguir:

```bash
make run
```

Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários.

O Apache Airflow, que também é usado para rodar o Ro-DOU, pode demorar alguns minutos para se configurar na primeira vez. Posteriormente, ele estará disponível em http://localhost:8080/. Para se autenticar e acessar o Apache Airflow, entre no link e utilize login `airflow` e senha `airflow`.

Na página sobre [o que é o Ro-DOU](rodou.md), explicamos o que é um grafo acíclico dirigido (DAG) do Airflow e como obter mais informações sobre este conceito.

Na tela inicial do Airflow, são fornecidos clippings de exemplo. A partir dos arquivos YAML (.yaml) do diretório `dag_confs/`, é possível manipular e customizar as pesquisas de clipping desejadas nos diários oficiais. Dentro dos arquivos YAML, é possível, por exemplo, definir palavras-chave de busca e um endereço de e-mail para recebimento de uma mensagem com os resultados da busca no(s) diário(s) oficial(is).

Para executar qualquer DAG do Airflow, é necessário ligá-la. Inicialmente, todas as DAGs ficam pausadas por padrão. Sugerimos começar testando o clipping **all_parameters_example**. Utilize o botão _toggle_ para ligá-lo. Após ativá-lo, o Airflow executará a DAG uma única vez. Clique no [nome da DAG](http://localhost:8080/tree?dag_id=all_parameters_example)
para visualizar o detalhe da execução.

Você observará que, tanto na visualização em árvore (**Tree**) como na visualização em Grafo (**Graph**) dentro do Apache Airflow, é possível constatar se houve algum resultado encontrado na API da Imprensa Nacional para os termos e demais parâmetros deste clipping. Se a tarefa chamada **"send_report"** estiver na cor verde, significa que foi encontrado um resultado e que uma mensagem de e-mail foi enviada para o endereço configurado no arquivo YAML.

Para visualizar a mensagem de e-mail, acesse o endereço http://localhost:5001/. Este é um serviço que simula uma caixa de e-mail (servidor SMTP) para fins de experimentação. **_Voilà!_**.

Lembre-se que o arquivo de configuração deste clipping está na pasta `dag_confs/`. Confira [aqui no GitHub](https://github.com/gestaogovbr/Ro-dou/blob/main/dag_confs/all_parameters_example.yaml) o conteúdo do arquivo YAML.

Agora, faremos um segundo teste: o clipping **terms_from_variable**, seguindo os mesmo passos. Neste caso, os termos pesquisados estão listados em uma variável do Airflow e podem ser modificados pela interface gráfica. Acesse no menu **Admin >> Variables** ou pela URL http://localhost:8080/variable/list/.

Leia a seção **Configurando em Produção** para instalar o Ro-dou utilizando um provedor SMTP real que enviará os e-mails para os destinatários verdadeiros.

**Observação:** Para utilizar o `source: - INLABS`, é necessário alterar a conexão `inlabs_portal` no Apache Airflow, apontando o usuário e senha de autenticação do portal. Um novo usuário pode ser cadastrado pelo portal [INLABS](https://inlabs.in.gov.br/acessar.php). A DAG
que realiza o download dos arquivos do INLABS é a **ro-dou_inlabs_load_pg**.

Quando tiver terminado de utilizar o ambiente de teste do Ro-DOU, desligue-o por meio do seguinte comando:

```bash
make down
```

### Configurando o ambiente de produção

Para utilizar o Ro-DOU em ambiente de produção, é necessário que o servidor tenha disponível um serviço SMTP que será utilizado pelo Apache Airflow para envio de mensagens de e-mail pela Internet. Siga os seguintes passos:

1. Utilize as credenciais do serviço SMTP (host, usuário, senha, porta etc.)
para editar o arquivo `docker-compose.yml`, substituindo as variáveis referentes ao serviço SMTP, a exemplo de `AIRFLOW__SMTP__SMTP_HOST`.

2. Ao final do arquivo `docker-compose.yml`, remova as linhas que declaram o
serviço **smtp4dev**, uma vez que ele não será mais necessário.

Uma vez executados esses passos, basta agora inicializar o Ro-DOU por meio do comando:

```bash
make run
```