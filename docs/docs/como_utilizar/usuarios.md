## Usuários internos e externos

**A gestão das buscas do RO-DOU é de responsabilidade exclusiva das unidades internas do MGI. Para entidades externas ao Ministério, a instalação e configuração do RO-DOU deve ser realizada na infraestrutura de TI própria. Nesses casos, oferecemos apenas suporte técnico para esclarecimento de dúvidas.**

### Usuários do Ministério da Gestão e da Inovação em Serviços Públicos

Para as unidades do Ministério da Gestão e da Inovação em Serviços Públicos que desejem solicitar a utilização de clippings via Ro-DOU, a Secretaria de Gestão e Inovação do MGI está disponível para auxiliá-las a configurar o serviço.

É preciso que a unidade interessada encaminhe as seguintes informações para o endereço [ro-dou-suporte@gestao.gov.br](mailto:ro-dou-suporte@gestao.gov.br):

**Sobre a pesquisa:**

* fonte(s) de pesquisa desejada(s): DOU, INLABS, Querido Diário (diários oficiais de municípios) e/ou DOE-SP (Diário Oficial do Estado de São Paulo). Por padrão, a pesquisa é realizada no DOU;
* lista de termos (palavras-chaves) para a pesquisa, separadas linha a linha;
* lista de termos a serem desconsiderados (ignorados) na busca, se necessário;
* indicação se a busca deve ser somente pelo termo exato ou também por variações;
* campo em que os termos devem ser pesquisados: tudo, apenas título ou apenas conteúdo;
* intervalo de data da busca: dia, semana, mês ou ano (por padrão, dia);
* seção ou seções do DOU que deverá(ão) ser pesquisada(s);
* inclusão ou exclusão da edição extra e/ou suplementar do DOU na pesquisa;
* lista de unidade(s) a serem filtradas na busca de cada seção, se necessário;
* lista de unidade(s) e subordinada(s) a serem desconsideradas (ignoradas) na busca, se necessário;
* lista de tipo de publicações a serem filtrados na busca de cada seção, se necessário;
* lista de municípios de interesse, caso a fonte de pesquisa seja o Querido Diário;
* caderno(s) de interesse, caso a fonte de pesquisa seja o DOE-SP.

**Sobre o conteúdo do relatório:**

* interesse em receber o texto completo da publicação ou a ementa, em vez do trecho resumido (disponível para a fonte INLABS);
* interesse na geração de resumos automáticos das publicações com uso de Inteligência Artificial (disponível para a fonte INLABS);
* interesse em exibir a relevância (classificação) de cada publicação encontrada (disponível para a fonte INLABS com OpenSearch);
* texto de cabeçalho e/ou rodapé personalizado do relatório, se necessário;
* necessidade ou dispensa de que um arquivo de planilha .CSV seja anexado ao e-mail com os resultados;
* interesse em receber o e-mail, mesmo se nenhum resultado da pesquisa for encontrado para um dia específico.

**Sobre o envio e agendamento:**

* texto do assunto do e-mail que conterá o relatório do Ro-DOU;
* horário e dias da semana para realização da pesquisa e envio do relatório (por padrão, ocorre às 8h da manhã, de segunda-feira a sexta-feira);
* lista com os endereços de e-mail que receberão o relatório do Ro-DOU;
* interesse em receber as notificações também em outros canais, como Slack, Discord, WhatsApp, Telegram e Microsoft Teams, entre outros.


Os termos de pesquisa devem ser registrados no Git ou em uma tabela no banco de dados? Depende.

* Se os termos de pesquisa são relativamente poucos e têm a expectativa de mudanças infrequentes, deixar no yaml (Git).
* Se os termos de pesquisa são muito numerosos e têm a expectativa de mudarem constantemente, usar uma tabela no banco de dados. Assim, uma outra DAG ou processo pode manter essa tabela sempre atualizada, sem que nada precise mudar no Git.

### Usuários externos (de fora do MGI)

Usuários de órgãos públicos que não sejam unidades do Ministério da Gestão e da Inovação em Serviços Públicos poderão enviar dúvidas ou comentários ao endereço [ro-dou-suporte@gestao.gov.br](mailto:ro-dou-suporte@gestao.gov.br).
