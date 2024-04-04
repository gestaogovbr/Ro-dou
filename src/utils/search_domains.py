from enum import Enum
from datetime import datetime, timedelta

class Section(Enum):
    """Define the section options to be used as parameter in the search"""

    SECAO_1 = "do1"
    SECAO_2 = "do2"
    SECAO_3 = "do3"
    EDICAO_EXTRA = "doe"
    EDICAO_EXTRA_1A = "do1_extra_a"
    EDICAO_EXTRA_1B = "do1_extra_b"
    EDICAO_EXTRA_1D = "do1_extra_d"
    EDICAO_EXTRA_2A = "do2_extra_a"
    EDICAO_EXTRA_2B = "do2_extra_b"
    EDICAO_EXTRA_2D = "do2_extra_d"
    EDICAO_EXTRA_3A = "do3_extra_a"
    EDICAO_EXTRA_3B = "do3_extra_b"
    EDICAO_EXTRA_3D = "do3_extra_d"
    EDICAO_SUPLEMENTAR = "do1a"
    TODOS = "todos"

class SectionINLABS(Enum):
    """Define the section options to be used as parameter in the search"""

    SECAO_1 = "DO1"
    SECAO_2 = "DO2"
    SECAO_3 = "DO3"
    EDICAO_EXTRA = "DO1E"
    EDICAO_EXTRA_1 = "DO1E"
    EDICAO_EXTRA_2 = "DO2E"
    EDICAO_EXTRA_3 = "DO3E"
    EDICAO_EXTRA_1A = "DO1E"
    EDICAO_EXTRA_1B = "DO1E"
    EDICAO_EXTRA_1D = "DO1E"
    EDICAO_EXTRA_2A = "DO2E"
    EDICAO_EXTRA_2B = "DO2E"
    EDICAO_EXTRA_2D = "DO2E"
    EDICAO_EXTRA_3A = "DO3E"
    EDICAO_EXTRA_3B = "DO3E"
    EDICAO_EXTRA_3D = "DO3E"
    EDICAO_SUPLEMENTAR = "DO1E"

class SearchDate(Enum):
    """Define the search date options to be used as parameter in the search"""

    DIA = "dia"
    SEMANA = "semana"
    MES = "mes"
    ANO = "ano"


class Field(Enum):
    """Define the search field options to be used as parameter in the search"""

    TUDO = "tudo"
    TITULO = "title_pt_BR"
    CONTEUDO = "ddm__text__21040__texto_pt_BR"


def calculate_from_datetime(publish_to_date: datetime, search_date: SearchDate):
    """
    Calculate parameter `publishFrom` to be passed to the API based
    on publishTo parameter and `search_date`. Perform especial
    calculation to the MES (month) parameter option
    """

    if search_date == SearchDate.DIA:
        return publish_to_date

    elif search_date == SearchDate.SEMANA:
        return publish_to_date - timedelta(days=6)

    elif search_date == SearchDate.MES:
        end_prev_month = publish_to_date.replace(day=1) - timedelta(days=1)
        publish_from_date = end_prev_month.replace(day=publish_to_date.day)
        return publish_from_date - timedelta(days=1)

    elif search_date == SearchDate.ANO:
        return publish_to_date - timedelta(days=364)