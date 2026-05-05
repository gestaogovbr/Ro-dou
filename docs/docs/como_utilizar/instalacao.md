## Instalação e configuração

**⚠️Observação:** Para instalar e executar este projeto no Windows, recomenda-se utilizar o [WSL (Windows Subsystem for Linux)](https://learn.microsoft.com/pt-br/windows/wsl/).   Certifique-se de que o WSL está devidamente instalado e configurado em seu sistema antes de prosseguir com os passos de instalação, certifique-se também de habilitar o [docker no WSL](https://learn.microsoft.com/pt-br/windows/wsl/tutorials/wsl-containers)

* [Como instalar e configurar o WSL](instalacao_wsl_windows.md)
* [Como habilitar o docker no WSL](habilitacao_docker_no_wsl.md)

### Configurando o ambiente local (desenvolvimento)

#### Requisitos

* 4Gb de memória RAM
* 2Gb de espaço em disco
* Sistema operacional Linux ou Windows com WSL

O código-fonte está disponibilizado no perfil do <a href="https://github.com/gestaogovbr/Ro-dou"><img src="https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" style="vertical-align: middle; display: inline-block;"></a> do Ministério da Gestão e da Inovação em Serviços Públicos.


Neste material, apresentamos uma configuração de exemplo para que você possa instalar e executar o Ro-DOU em seu computador.

<iframe width="560" height="315" src="https://www.youtube.com/embed/6QUHxOe9v20?si=4O4hJhltwgOiUHgc" title="Como instalar o Ro-DOU" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

<iframe width="560" height="315" src="https://www.youtube.com/embed/WWt6lrnfEXE?si=uV_tKSfHHDolufgm" title="Vídeo orientado para instalação" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

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


**Observação:** Ao executar o comando, uma mensagem será exibida confirmando a criação das variáveis de ambiente e das conexões. Caso isso não ocorra automaticamente, você pode executar cada função separadamente a partir do arquivo `Makefile`.

<!-- Este comando baixa as imagens Docker necessárias, efetua o build do container Docker do Ro-DOU e executa todos os demais passos necessários. -->

Como mostrado na imagem, após executar o comando no terminal e realizar o build dos containers, as conexões com os ambientes necessários serão iniciadas automaticamente. No exemplo apresentado, os containers e conexões já haviam sido criados, por isso as mensagens exibidas no retorno.

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

4. Confirme se o serviço do Airflow — do qual o Ro-DOU depende — está funcionando, acessando-o pelo navegador no endereço:

    [http://localhost:8080/](http://localhost:8080/)

O Apache Airflow, utilizado também para executar o Ro-DOU, pode levar alguns minutos para ser configurado na primeira inicialização. Para acessar e se autenticar no Airflow, abra o link e utilize o usuário `airflow` e a senha `airflow`.

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

8. Opcional: Configurando variáveis de ambiente para IA (resumo com IA):

O Ro-DOU suporta geração de resumos automáticos de publicações utilizando modelos de linguagem (LLMs). Para habilitar essa funcionalidade, é necessário buildar a imagem com o(s) provedor(es) desejado(s) e configurar as variáveis de API no Apache Airflow.

**Provedores suportados: Azure, OpenAI, Gemini e Claude**

**1. Build com o provedor desejado:**

```bash
# Build com um provedor
make build AI_PROVIDERS="openai"

# Build com múltiplos provedores
make build AI_PROVIDERS="openai gemini"
```

Provedores disponíveis: `openai`, `gemini`, `claude`. Se nenhum provedor for especificado, as dependências de IA são ignoradas e a funcionalidade não estará disponível.

**2. Configurando as variáveis de API no Airflow:**

Para os provedores **OpenAI**, **Gemini** e **Claude**, basta criar uma variável no Airflow com a chave de API do provedor escolhido:

| Variável | Descrição |
|---|---|
| `OPENAI_API_KEY` | Chave de API do OpenAI |
| `GEMINI_API_KEY` | Chave de API do Gemini |
| `ANTHROPIC_API_KEY` | Chave de API do Claude (Anthropic) |

Para criar a variável, acesse a interface do Airflow em [http://localhost:8080/variable/list/](http://localhost:8080/variable/list/) e adicione a variável com o valor da sua chave.

Para o provedor **Azure**, são necessárias variáveis adicionais:

| Variável | Descrição | Exemplo |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | URL do endpoint do Azure OpenAI | `https://seu-recurso.openai.azure.com/` |
| `AZURE_OPENAI_API_VERSION` | Versão da API | `2024-02-01` |
| `AZURE_OPENAI_DEPLOYMENT` | Nome do deployment do modelo | `gpt-4o-mini` |
| `AZURE_OPENAI_API_KEY` | Chave de API do Azure OpenAI | `<sua-chave>` |

**Criando as variáveis do Azure automaticamente via Makefile:**

```bash
make create-azure-openai-variables
```

A variável `AZURE_OPENAI_API_KEY` será criada com o valor `<your-api-key>`. Para inserir sua chave real, acesse [http://localhost:8080/variable/list/](http://localhost:8080/variable/list/), localize a variável e edite o valor.

**3. Configurando a DAG para usar IA:**

No arquivo YAML da DAG, adicione o bloco `ai_config` com o provedor e o nome da variável que contém a chave de API:

```yaml
search:
  use_ai_summary: True
  ai_pub_limit: 5
  ai_custom_prompt: |
    Você é um assistente que cria resumos concisos de publicações oficiais.
ai_config:
  provider: openai  # openai | gemini | claude | azure
  api_key_var: OPENAI_API_KEY
```

9. Desligando o ambiente:

Quando tiver terminado de utilizar o ambiente de teste do Ro-DOU, desligue-o por meio do seguinte comando:

```bash
make down
```


<iframe width="560" height="315" src="https://www.youtube.com/embed/NpumeNLBuI8?si=g_i99R2d2k23yISX" title="Utilizando o INLABS como fonte de dados-pt1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

<iframe width="560" height="315" src="https://www.youtube.com/embed/0bppPCACs5Q?si=SQUs2fBJ9bOArwJD" title="Utilizando o INLABS como fonte de dados-pt2" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>