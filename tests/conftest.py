"""All unit tests
"""

import os

import pytest
from typing import Tuple

from dags.ro_dou_src.dou_dag_generator import (DouDigestDagGenerator,
                                           SearchResult)
from dags.ro_dou_src.parsers import YAMLParser
from dags.ro_dou_src.searchers import DOUSearcher, INLABSSearcher
from dags.ro_dou_src.hooks.inlabs_hook import INLABSHook

TEST_AIRFLOW_HOME = '/opt/airflow'

TEST_ENV_VARS = {
    'AIRFLOW_HOME': TEST_AIRFLOW_HOME
}

APP_NAME = 'pytest-airflow-dou_dag_generator'


def pytest_configure(config):
    """Configure and init envvars for airflow."""
    config.old_env = {}
    for key, value in TEST_ENV_VARS.items():
        config.old_env[key] = os.getenv(key)
        os.environ[key] = value

def pytest_unconfigure(config):
    """Restore envvars to old values."""
    for key, value in config.old_env.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value

@pytest.fixture(scope='module')
def dag_gen() -> DouDigestDagGenerator:
    return DouDigestDagGenerator()

@pytest.fixture()
def yaml_parser()-> YAMLParser:
    filepath = os.path.join(DouDigestDagGenerator().YAMLS_DIR,
                            "examples_and_tests",
                            'basic_example.yaml')
    return YAMLParser(filepath=filepath)

@pytest.fixture()
def dou_searcher()-> DOUSearcher:
    return DOUSearcher()

@pytest.fixture()
def inlabs_searcher()-> INLABSSearcher:
    return INLABSSearcher()

@pytest.fixture()
def inlabs_hook()-> INLABSHook:
    return INLABSHook()

@pytest.fixture()
def report_example() -> list:
    report = [
        {
            "result": {
                "single_group": {
                    "antonio de oliveira": {
                        "single_department":[
                            {
                                "section": "Seção 3",
                                "title": "EXTRATO DE COMPROMISSO",
                                "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
                                "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS "
                                    "- Secretário-Executivo Adjunto do Ministério da "
                                    "Saúde; REGINALDO <span class='highlight' style="
                                    "'background:#FFA;'>ANTONIO</span> ... DE <span "
                                    "class='highlight' style='background:#FFA;'>OLIVEIRA"
                                    "</span> FREITAS JUNIOR - Diretor Geral.EXTRATO DE "
                                    "COMPROMISSO PRONAS/PCD: Termo de Compromisso que "
                                    "entre si celebram a União, por intermédio do "
                                    "Ministério da Saúde,...",
                                "date": "02/09/2021",
                            },
                            {
                                "section": "Seção 3",
                                "title": "EXTRATO DE INEXIGIBILIDADE DE LICITAÇÃO Nº 4/2021 - UASG 160454",
                                "href": "https://www.in.gov.br/web/dou/-/extrato-de-inexigibilidade-de-licitacao-n-4/2021-uasg-160454-342420638",
                                "abstract": "CPF CONTRATADA : 013.872.545-45 MARCOS <span"
                                    " class='highlight' style='background:#FFA;'>ANTONIO"
                                    "</span> DE <span class='highlight' style='background"
                                    ":#FFA;'>OLIVEIRA</span> CARDOSO. Valor: R$ 160.000"
                                    ",00.000,00. CPF CONTRATADA : 000.009.405-69 LEANDRO "
                                    "MACEDO DE FRANCA. Valor: R$ 160.000,00. CPF CONTRATADA"
                                    " : 000.071.195-00 GILMAR DE OLIVEIRA DANTAS. Valor: "
                                    "R$ 160.000,00. CPF CONTRATADA : 000.241.585-2...",
                                "date": "02/09/2021",
                            },
                            {
                                "section": "Seção 3",
                                "title": "EXTRATO DE INEXIGIBILIDADE DE LICITAÇÃO Nº 16/2021 - UASG 160173",
                                "href": "https://www.in.gov.br/web/dou/-/extrato-de-inexigibilidade-de-licitacao-n-16/2021-uasg-160173-342420560",
                                "abstract": "CPF CONTRATADA : 066.751.274-89 LUIS <span "
                                    "class='highlight' style='background:#FFA;'>ANTONIO"
                                    "</span> DE <span class='highlight' style='background"
                                    ":#FFA;'>OLIVEIRA</span>. Valor: R$ 80.000,00.EXTRATO "
                                    "DE INEXIGIBILIDADE DE LICITAÇÃO Nº 16/2021 - UASG "
                                    "160173 Nº Processo: 64097007173202061 . Objeto: "
                                    "Contratação de prestadores de serviço de coleta, "
                                    "transporte e distribuição de água potável no contexto d...",
                                "date": "02/09/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA DE PESSOAL SEGES/ME Nº 10.063, DE 31 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-de-pessoal-seges/me-n-10.063-de-31-de-agosto-de-2021-342182206",
                                "abstract": "que constam do Processo nº 14022.109097/"
                                    "2021-12, resolve: Art. 1º Efetivar o exercício do "
                                    "servidor <span class='highlight' style='background"
                                    ":#FFA;'>ANTONIO</span> ... GABRIEL <span class="
                                    "'highlight' style='background:#FFA;'>OLIVEIRA</span>"
                                    " DOS SANTOS, Analista de Infraestrutura, matrícula "
                                    "SIAPE nº 1664961, na Superintendência competência "
                                    "subdelegada pelo art. 5º da Portaria SEDGG nº "
                                    "17.472, de 21 ...",
                                "date": "01/09/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA PRT-3/DPR Nº 337, DE 30 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-prt-3/dpr-n-337-de-30-de-agosto-de-2021-341729221",
                                "abstract": "mpt.mp.br 12 20/09/2021 27/09/2021 Fabrício "
                                    "Borela Pena fabricio.pena@mpt.mp.br 13 27/09/2021 "
                                    "04/10/2021 <span class='highlight' style='background"
                                    ":#FFA;'>Antonio</span> ... Carlos <span class="
                                    "'highlight' style='background:#FFA;'>Oliveira</span>"
                                    " Pereira antonio.pereira@mpt.mp.br 14 04/10/2021 "
                                    "11/10/2021 Rafael Albernaz Carvalho uso das "
                                    "atribuições que lhe foram delegadas pelo artigo "
                                    "1º, §§1º, 2º, X...",
                                "date": "31/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA Nº 291, DE 27 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-n-291-de-27-de-agosto-de-2021-341719697",
                                "abstract": "Considerando o que consta no Processo 23282."
                                    "011034/2021-49, resolve: Art. 1º Designar o servidor "
                                    "SAMUEL <span class='highlight' style='background:"
                                    "#FFA;'>ANTÔNIO</span> ... AZEVEDO <span class="
                                    "'highlight' style='background:#FFA;'>OLIVEIRA</span>,"
                                    " matrícula SIAPE nº 2265755, para a função de Gerente"
                                    " da Divisão de Acompanhamento uso de suas atribuições"
                                    " legais, de acordo com a Lei nº 12.289, de 20 de ...",
                                "date": "31/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIAS DE 20 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portarias-de-20-de-agosto-de-2021-341686751",
                                "abstract": "da Lei nº 8.112/90, combinado com o art. 3º,"
                                    " § 1º da Emenda Constitucional nº 103/2019, ao "
                                    "servidor <span class='highlight' style='background"
                                    ":#FFA;'>ANTONIO</span> ... LIMA <span class="
                                    "'highlight' style='background:#FFA;'>OLIVEIRA"
                                    "</span>, matrícula SIAPE nº 30772, ocupante do cargo"
                                    " de Assistente Jurídico, Classe S, Padrão nº 71, de"
                                    " 13 de abril de 2018, resolve: Nº 245 - Conceder "
                                    "aposentadoria volu...",
                                "date": "31/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA PRESI Nº 123, de 26 de agosto de 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-presi-n-123-de-26-de-agosto-de-2021-341642203",
                                "abstract": "0007022-26.2021.6.07.8100, resolve: Designar,"
                                " ad referendum do Tribunal, o Juiz de Direito ROQUE "
                                "FABRÍCIO <span class='highlight' style='background:"
                                "#FFA;'>ANTONIO</span> ... DE <span class='highlight' "
                                "style='background:#FFA;'>OLIVEIRA</span> VIEL para "
                                "exercer, a partir da publicação deste ato, a função de "
                                "Juiz Substituto da 11ª Zona Eleitoral, ficando dispensada"
                                " a Juíza de Direito Catarina de Macedo Nogueira Lima e "
                                "Corrêa, a partir de 1º/08/2021. Des. HUMBERTO ADJUTO ULHÔA",
                                "date": "30/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA DRF/NAT Nº 54, DE 24 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-drf/nat-n-54-de-24-de-agosto-de-2021-341632367",
                                "abstract": "Araújo Filho ENGENHARIA ELETRÔNICA Leandro "
                                    "Mayron de Oliveira Pinto Leonardo de Barros e Silva "
                                    "Edson"" <span class='highlight' style='background:"
                                    "#FFA;'>Antônio</span> ... de <span class='highlight' "
                                    "style='background:#FFA;'>Oliveira</span> Flávio Gentil"
                                    " de Araújo Filho ENGENHARIA ELETRÔNICA Leandro Mayron"
                                    " de Oliveira Pinto Leonardo ... de Barros e Silva "
                                    "Edson <span class='highlight' style='background:"
                                    "#FFA;'>Antônio</span> de <span class='highlight' "
                                    "style='background:#FFA;'>Oliveira</span> Flávio "
                                    "Gentil de Araújo Filho ENGENHARIA DOS MATERIAIS Gelsoneide",
                                "date": "30/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "PORTARIA nº 1.664 - GAB/REI/IFPI, de 26 de agosto de 2021",
                                "href": "https://www.in.gov.br/web/dou/-/portaria-n-1.664-gab/rei/ifpi-de-26-de-agosto-de-2021-341621247",
                                "abstract": "EDUCAÇÃO, CIÊNCIA E TECNOLOGIA DO PIAUÍ, no"
                                    " uso de suas atribuições legais, resolve: Nomear o "
                                    "servidor <span class='highlight' style='background"
                                    ":#FFA;'>ANTÔNIO</span> ... LUÍS <span class="
                                    "'highlight' style='background:#FFA;'>OLIVEIRA</span> "
                                    "DOS REIS, Assistente em Administração, Nível de "
                                    "Classificação D, Nível de Capacitaçãosto de 2021 O "
                                    "REITOR DO INSTITUTO FEDERAL DE EDUCAÇÃO, CIÊNCIA E TECNOLOGI...",
                                "date": "30/08/2021",
                            },
                            {
                                "section": "Seção 3",
                                "title": "AVISO DE LICITAÇÃO Tomada de Preço nº 1/2021",
                                "href": "https://www.in.gov.br/web/dou/-/aviso-de-licitacao-tomada-de-preco-n-1/2021-341567981",
                                "abstract": "Nacip Raydan-MG, 25 de agosto de 2021 Eduardo"
                                    " <span class='highlight' style='background:#FFA;'>"
                                    "Antônio</span> de <span class='highlight' style="
                                    "'background:#FFA;'>Oliveira</span> Prefeitorna "
                                    "público que realizar. Objeto: Contratação de empresa "
                                    "especializada para Pavimentação em blocos sextavado "
                                    "de concreto nas ruas Ataíde Moreira, Rua Peçanha, "
                                    "Travessa Tiradentes e Ademar Alvarenga, Convênio n°. 88...",
                                "date": "30/08/2021",
                            },
                            {
                                "section": "Seção 3",
                                "title": "EDITAL",
                                "href": "https://www.in.gov.br/web/dou/-/edital-341218450",
                                "abstract": "TAMARA SILVA DAIELLO ES-017002/O 5 CONTADOR "
                                    "KLAUS XAVIER DE OLIVEIRA ES-011491/O 6 CONTADOR "
                                    "MARCOS <span class='highlight' style='background:"
                                    "#FFA;'>ANTÔNIO</span> ... DE <span class='highlight'"
                                    " style='background:#FFA;'>OLIVEIRA</span> ES-008492/O"
                                    " 7 CONTADOR EDUARDO TRESENA PORCHERA ES-021302/O 8 "
                                    "CONTADOR JOSÉ JOCIMAR PINHEIROEDITAL RELAÇÃO DA "
                                    "CHAPA HABILITADA A CONCORRER AO PLEITO DE RENOVAÇÃO DE ...",
                                "date": "27/08/2021",
                            },
                            {
                                "section": "Seção 2",
                                "title": "RESOLUÇÃO ADMINISTRATIVA Nº 208, de 18 de agosto de 2021",
                                "href": "https://www.in.gov.br/web/dou/-/resolucao-administrativa-n-208-de-18-de-agosto-de-2021-341078554",
                                "abstract": "Art. 1º Retificar a Resolução Administrativa "
                                    "nº 74/2021/TRT11, referente à aposentadoria do "
                                    "servidor <span class='highlight' style='background:"
                                    "#FFA;'>ANTÔNIO</span> ... JOSÉ <span class="
                                    "'highlight' style='background:#FFA;'>OLIVEIRA</span>"
                                    " DA SILVA, para incluir a vantagem \"opção\" deferida"
                                    " com base no art. 193 da Lei 8.112/90 ... a seguinte"
                                    " redação: \"Art. 1º Conceder aposentadoria voluntária"
                                    " com proventos integrais ao servidor <span class="
                                    "'highlight' style='background:#FFA;'>ANTONIO</span>"
                                    " ... JOSÉ <span class='highlight' style="
                                    "'background:#FFA;'>OLIVEIRA</span> DA SILVA, "
                                    "ocupante do cargo de Técnico Judiciário, Área"
                                    " Administrativa, Sem Especialidade",
                                "date": "27/08/2021",
                            },
                        ],
                    },
                    "dados abertos": {
                        "single_department": [
                            {
                                "section": "Seção 1",
                                "title": "RESOLUÇÃO CEPPDP/ME Nº 1, DE 31 DE AGOSTO DE 2021",
                                "href": "https://www.in.gov.br/web/dou/-/resolucao-ceppdp/me-n-1-de-31-de-agosto-de-2021-341971457",
                                "abstract": "revisados Dez/21-Jan/22 3 Produto 11 "
                                    "Definição de diretrizes para elaboração e revisão do "
                                    "Plano de <span class='highlight' style='background:"
                                    "#FFA;'>Dados</span> ... <span class='highlight' "
                                    "style='background:#FFA;'>Abertos</span> do ME, no"
                                    " que diz respeito à divulgação de dados pessoais "
                                    "Dez/21-Jan/22 3 Produto 12 Detalhamentova o Plano "
                                    "de Ações Estruturantes e Entregas do Comitê "
                                    "Estratégico de Priv...",
                                "date": "01/09/2021",
                            },
                            {
                                "section": "Seção 1",
                                "title": "RETIFICAÇÃO",
                                "href": "https://www.in.gov.br/web/dou/-/retificacao-341676133",
                                "abstract": "de Textos no Sistema Braille Vigente Portaria"
                                    " nº 380 de 27 de novembro de 2018 Publicar o Plano "
                                    "de <span class='highlight' style='background:#FFA;'"
                                    ">Dados</span> ... <span class='highlight' style="
                                    "'background:#FFA;'>Abertos</span> - PDA Vigente "
                                    "Portaria nº 440 de 28 de dezembro de 2018 Instituir"
                                    " a Comissão para ElaboraçãoRETIFICAÇÃO A Portaria nº"
                                    " 15, de 24 de agosto de 2021, publicada no Diário Ofic...",
                                "date": "31/08/2021",
                            },
                        ],
                    }
                }
            },
            "header": "Teste Report",
            "department": None,
        }
    ]
    return report

@pytest.fixture()
def search_results() -> dict:
    result = {
        "ANTONIO DE OLIVEIRA": [
            {
                "section": "Seção 3",
                "title": "EXTRATO DE COMPROMISSO",
                "href": "https://www.in.gov.br/web/dou/-/extrato-de-compromisso-342504508",
                "abstract": "ALESSANDRO GLAUCO DOS ANJOS DE VASCONCELOS - Secretário-Executivo Adjunto do Ministério da Saúde; REGINALDO <span class='highlight' style='background:#FFA;'>ANTONIO</span> ... DE <span class='highlight' style='background:#FFA;'>OLIVEIRA</span> FREITAS JUNIOR - Diretor Geral.EXTRATO DE COMPROMISSO PRONAS/PCD: Termo de Compromisso que entre si celebram a União, por intermédio do Ministério da Saúde,...",
                "date": "02/09/2021",
            },
            {
                "section": "Seção 3",
                "title": "EXTRATO DE INEXIGIBILIDADE DE LICITAÇÃO Nº 4/2021 - UASG 160454",
                "href": "https://www.in.gov.br/web/dou/-/extrato-de-inexigibilidade-de-licitacao-n-4/2021-uasg-160454-342420638",
                "abstract": "CPF CONTRATADA : 013.872.545-45 MARCOS <span class='highlight' style='background:#FFA;'>ANTONIO</span> DE <span class='highlight' style='background:#FFA;'>OLIVEIRA</span> CARDOSO. Valor: R$ 160.000,00.000,00. CPF CONTRATADA : 000.009.405-69 LEANDRO MACEDO DE FRANCA. Valor: R$ 160.000,00. CPF CONTRATADA : 000.071.195-00 GILMAR DE OLIVEIRA DANTAS. Valor: R$ 160.000,00. CPF CONTRATADA : 000.241.585-2...",
                "date": "02/09/2021",
            },
            {
                "section": "Seção 3",
                "title": "EXTRATO DE INEXIGIBILIDADE DE LICITAÇÃO Nº 16/2021 - UASG 160173",
                "href": "https://www.in.gov.br/web/dou/-/extrato-de-inexigibilidade-de-licitacao-n-16/2021-uasg-160173-342420560",
                "abstract": "CPF CONTRATADA : 066.751.274-89 LUIS <span class='highlight' style='background:#FFA;'>ANTONIO</span> DE <span class='highlight' style='background:#FFA;'>OLIVEIRA</span>. Valor: R$ 80.000,00.EXTRATO DE INEXIGIBILIDADE DE LICITAÇÃO Nº 16/2021 - UASG 160173 Nº Processo: 64097007173202061 . Objeto: Contratação de prestadores de serviço de coleta, transporte e distribuição de água potável no contexto d...",
                "date": "02/09/2021",
            },
        ],
    "SILVA": [
            {
                "section": "Seção 3",
                "title": "EXTRATO DE CONTRATO",
                "href": "https://www.in.gov.br/web/dou/-/extrato-de-contrato-342647923",
                "abstract": "<span class='highlight' style='background:#FFA;'>Silva</span> Construções e Serviços Eireli.EXTRATO DE CONTRATO Tomada de Preços nº 01/2021. Contrato: 34/2021. Contratante: O Município de Itaporanga D'Ajuda, Estado de Sergipe. Contratada: R.S. Silva Construções e Serviços Eireli. Objeto: Contratação De Empresa Especializada Em Obras E Serviços De Engenharia Para Remanescente De Pavimentação E Dren...",
                "date": "02/09/2021",
            },
            {
                "section": "Seção 3",
                "title": "AVISO PREGÃO ELETRÔNICO Nº 264/2021- SEC SAÚDE",
                "href": "https://www.in.gov.br/web/dou/-/aviso-pregao-eletronico-n-264/2021-sec-saude-342647763",
                "abstract": "ANDREA ISABEL DA <span class='highlight' style='background:#FFA;'>SILVA</span> THOMÉ Secretária Municipal da AdministraçãoAVISO PREGÃO ELETRÔNICO Nº 264/2021- SEC SAÚDE PROCESSO Nº 438/2021 OBJETO: Aquisição de mobiliários em geral para a estruturação da Secretária Municipal da Saúde. DATA DA REALIZAÇÃO: 17/09/2021. RECEBIMENTO DAS PROPOSTAS ELETRÔNICAS: a partir do dia 02/09/2021 ao dia 17/09/202...",
                "date": "02/09/2021",
            },
            {
                "section": "Seção 3",
                "title": "AVISO DE REVOGAÇÃO",
                "href": "https://www.in.gov.br/web/dou/-/aviso-de-revogacao-342647681",
                "abstract": "ALVES DA <span class='highlight' style='background:#FFA;'>SILVA</span> PregoeiraAVISO DE REVOGAÇÃO Revogação do PREGÃO ELETRÔNICO BEC Nº 032/2021 - PROCESSO Nº 4646/2021 - OFERTA DE COMPRA Nº 874700801002021OC00035- Objeto - REGISTRO DE PREÇOS PARA AQUISIÇÃO DE MÁSCARAS DE PROTEÇÃO REUTILIZÁVEL. A Prefeitura Municipal de Holambra TORNA PÚBLICO a quem possa interessar, que a Comissão Permanente de ...",
                "date": "02/09/2021",
            },
            {
                "section": "Seção 3",
                "title": "AVISO DE ADJUDICAÇÃO E HOMOLOGAÇÃOTOMADA DE PREÇOS nº 3/2021",
                "href": "https://www.in.gov.br/web/dou/-/aviso-de-adjudicacao-e-homologacaotomada-de-precos-n-3/2021-342646709",
                "abstract": "HOMOLOGAÇÃOTOMADA DE PREÇOS nº 3/2021 Processo nº 108/2021 O Senhor Prefeito Municipal, LEANDRO PEREIRA DA <span class='highlight' style='background:#FFA;'>SILVA</span> ... LEANDRO PEREIRA DA <span class='highlight' style='background:#FFA;'>SILVA</span>VISO DE ADJUDICAÇÃO E HOMOLOGAÇÃOTOMADA DE PREÇOS nº 3/2021 Processo nº 108/2021 O Senhor Prefeito Municipal, LEANDRO PEREIRA DA SILVA, no uso de s...",
                "date": "02/09/2021",
            },
        ],
    }

    return result

@pytest.fixture()
def term_n_group():
    return """{
        "nome":{
            "0":"ANTONIO DE OLIVEIRA",
            "1":"SILVA"
        },
        "cargo":{
            "0":"EPPGG",
            "1":"ATI"
        }
    }"""


@pytest.fixture()
def merge_results_samples() -> Tuple[SearchResult, SearchResult, SearchResult]:
    results_dou = {
        'grupo_1': {
            'term_1': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_2': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_3': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
        },
        'grupo_2': {
            'term_4': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_5': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_6': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
        }
    }
    results_qd = {
        'grupo_1': {
            'term_2':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_3':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_10': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
        },
        'grupo_3': {
            'term_7':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_8':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_9':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}],
                        "mgi": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
        }
    }
    merged_results = {
        'grupo_2': {
            'term_4':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_5':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_6':  {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]}
        },
        'grupo_3': {
            'term_7': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_8': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_9': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}],
                        "mgi": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
        },
        'grupo_1': {
            'term_1': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_2': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}, {'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_3': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}, {'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]},
            'term_10': {"single_department": [{'key1': 'result1'}, {'key2': 'result2'}, {'key3': 'resultn'}]}
        }
    }

    return (results_dou, results_qd, merged_results)
