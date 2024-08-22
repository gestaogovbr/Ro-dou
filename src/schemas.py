"""
This module defines the Pydantic models for validating the structure of
the YAML files used in the application.

The main classes are:

- `SearchTerms`: search terms in the YAML file.
- `Search`: search configuration in the YAML file.
- `Report`: report configuration in the YAML file.
- `DAG`: DAG defined in the YAML file.
- `Config`: overall configuration in the YAML file.

These models are used to validate the YAML files using the Pydantic
library.
"""

import textwrap
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field


class DBSelect(BaseModel):
    """Represents the structure of the 'from_db_select' field in the YAML file."""

    sql: str = Field(description="SQL query to fetch the search terms")
    conn_id: str = Field(description="Airflow connection ID to use for the SQL query")


class SearchTerms(BaseModel):
    """Represents the search terms in the YAML file."""

    from_airflow_variable: Optional[str] = Field(
        default=None,
        description="Variável do Airflow a ser usada como termos de pesquisa",
    )
    from_db_select: Optional[DBSelect] = Field(
        default=None,
        description="Consulta SQL para buscar os termos de pesquisa em um "
        "banco de dados",
    )


class SearchField(BaseModel):
    """Represents the field for search in the YAML file."""

    description: str
    value: str


class SearchConfig(BaseModel):
    """Represents the search configuration in the YAML file."""

    header: Optional[str] = Field(
        default=None, description="Cabeçalho da consulta de pesquisa"
    )
    sources: Optional[List[str]] = Field(
        default=["DOU"],
        description="Lista de fontes de dados para pesquisar (Querido Diário [QD], "
        "Diário Oficial da União [DOU], INLABS). Default: DOU.",
    )
    territory_id: Optional[int] = Field(
        default=None,
        description="ID do território no Querido Diário para filtragem "
        "baseada em localização",
    )
    terms: Union[List[str], SearchTerms] = Field(
        description="Lista de termos de pesquisa ou uma forma de buscá-los"
    )
    field: Optional[str] = Field(
        default="TUDO",
        description="Campos dos quais os termos devem ser pesquisados. "
        "Valores: TUDO, TITULO, CONTEUDO. Default: TUDO",
    )
    is_exact_search: Optional[bool] = Field(
        default=True,
        description="Busca somente o termo exato. Valores: True ou False. "
        "Default: True.",
    )
    ignore_signature_match: Optional[bool] = Field(
        default=False,
        description="Busca somente o termo exato. Valores: True ou False. "
        "Default: True.",
    )
    date: Optional[str] = Field(
        default="DIA",
        description="Intervalo de data para busca. Valores: DIA, SEMANA, "
        "MES, ANO. Default: DIA",
    )
    dou_sections: Optional[List[str]] = Field(
        default=["TODOS"],
        description=textwrap.dedent(
            """
            Seção do Diário Oficial a procurar:

            - SECAO_1
            - SECAO_2
            - SECAO_3
            - EDICAO_EXTRA
            - EDICAO_EXTRA_1A
            - EDICAO_EXTRA_1B
            - EDICAO_EXTRA_1D
            - EDICAO_EXTRA_2A
            - EDICAO_EXTRA_2B
            - EDICAO_EXTRA_2D
            - EDICAO_EXTRA_3A
            - EDICAO_EXTRA_3B
            - EDICAO_EXTRA_3D
            - EDICAO_SUPLEMENTAR
            - TODOS

            Default: TODOS
        """
        ),
    )
    department: Optional[List[str]] = Field(
        default=None, description="Lista de departamentos para filtrar a pesquisa"
    )


class ReportConfig(BaseModel):
    """Represents the report configuration in the YAML file."""

    slack: Optional[dict] = Field(
        default=None, description="Configuração do webhook do Slack para relatórios"
    )
    discord: Optional[dict] = Field(
        default=None, description="Configuração do webhook do Discord para relatórios"
    )
    emails: Optional[List[EmailStr]] = Field(
        default=None, description="Lista de endereços de e-mail para enviar o relatório"
    )
    attach_csv: Optional[bool] = Field(
        default=None,
        description="Se deve anexar um arquivo CSV com os resultados da pesquisa",
    )
    subject: Optional[str] = Field(
        default=None, description="Assunto do relatório por e-mail"
    )
    skip_null: Optional[bool] = Field(
        default=None,
        description="Se deve pular a notificação de resultados nulos/vazios",
    )
    hide_filters: Optional[bool] = Field(
        default=None, description="Se deve ocultar os filtros aplicados no relatório"
    )
    header_text: Optional[str] = Field(
        default=None, description="Texto a ser incluído no cabeçalho do relatório"
    )
    footer_text: Optional[str] = Field(
        default=None, description="Texto a ser incluído no rodapé do relatório"
    )
    no_results_found_text: Optional[str] = Field(
        default=None, description="Texto a ser exibido quando não há resultados"
    )


class DAGConfig(BaseModel):
    """Represents the DAG configuration in the YAML file."""

    id: str = Field(description="Nome único da DAG")
    description: str = Field(description="Descrição da DAG")
    tags: Optional[List[str]] = Field(
        default=[], description="Lista de tags para filtragem da DAG no Airflow"
    )
    owner: Optional[List[str]] = Field(
        default=[], description="Lista de owners para filtragem da DAG no Airflow"
    )
    schedule: Optional[str] = Field(default=None, description="Expressão cron")
    dataset: Optional[str] = Field(default=None, description="Nome do Dataset")
    search: Union[List[SearchConfig], SearchConfig] = Field(
        description="Seção para definição da busca no Diário"
    )
    doc_md: Optional[str] = Field(default="", description="description")
    report: ReportConfig = Field(
        description="Aceita: `slack`, `discord`, `emails`, `attach_csv`, "
        "`subject`, `skip_null`"
    )


class RoDouConfig(BaseModel):
    """Represents the overall configuration in the YAML file."""

    dag: DAGConfig = Field(description="Instanciação da DAG")
