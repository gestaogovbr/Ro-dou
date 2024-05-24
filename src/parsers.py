"""Abstract and concrete classes to parse DAG configuration from a file.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
import ast
import yaml
import textwrap

from airflow.models import Variable


@dataclass
class SearchConfig:
    header: str
    sources: List[str]
    territory_id: int
    dou_sections: List[str]
    field: str
    search_date: str
    is_exact_search: bool
    ignore_signature_match: bool
    force_rematch: bool
    full_text: bool
    terms: List[str]
    sql: str
    conn_id: str
    department: List[str]


@dataclass
class DAGConfig:
    dag_id: str
    search: List[SearchConfig]
    emails: List[str]
    subject: str
    attach_csv: bool
    discord_webhook: str
    slack_webhook: str
    schedule: str
    description: str
    skip_null: bool
    doc_md: str
    dag_tags: Set[str]
    owner: str


class FileParser(ABC):
    """Abstract class to build file parsers with DAG configuration."""

    @abstractmethod
    def parse(self):
        pass

    def _hash_dag_id(self, dag_id: str, size: int) -> int:
        """Hashes the `dag_id` into a integer between 0 and `size`"""
        buffer = 0
        for _char in dag_id:
            buffer += ord(_char)
        try:
            _hash = buffer % size
        except ZeroDivisionError:
            raise ValueError("`size` deve ser maior que 0.")
        return _hash

    def _get_safe_schedule(self, dag: dict, default_schedule: str) -> str:
        """Retorna um novo valor de `schedule` randomizando o
        minuto de execução baseado no `dag_id`, caso a dag utilize o
        schedule padrão. Aplica uma função de hash na string
        dag_id que retorna valor entre 0 e 60 que define o minuto de
        execução.
        """
        schedule = dag.get("schedule", default_schedule)
        if schedule == default_schedule:
            id_based_minute = self._hash_dag_id(dag["id"], 60)
            schedule_without_min = " ".join(schedule.split(" ")[1:])
            schedule = f"{id_based_minute} {schedule_without_min}"
        return schedule


class YAMLParser(FileParser):
    """Parses YAML file and get the DAG parameters.

    It guarantees that mandatory fields are in place and are properly
    defined providing clear error messages.
    """

    DEFAULT_SCHEDULE = "0 5 * * *"

    def __init__(self, filepath: str):
        self.filepath = filepath

    def parse(self) -> DAGConfig:
        return self._parse_yaml()

    def _parse_yaml(self) -> DAGConfig:
        """Processes the config file in order to instantiate the DAG in
        Airflow.
        """
        with open(self.filepath, "r") as file:
            dag_config_dict = yaml.safe_load(file)

        # Mandatory fields
        dag = self._try_get(dag_config_dict, "dag")
        dag_id = self._try_get(dag, "id")
        description = self._try_get(dag, "description")
        report = self._try_get(dag, "report")
        search = self._try_get(dag, "search")

        search_dict = {}
        if isinstance(search, dict):
            for key, subsearch in search.items():
                search_dict[key] = {}
                search_dict[key]["sources"] = search.get("sources", ["DOU"])
                (
                    search_dict[key]["terms"],
                    search_dict[key]["sql"],
                    search_dict[key]["conn"],
                ) = self._get_terms_params(subsearch)
                search_dict[key]["territory_id"] = subsearch.get("territory_id", None)
                search_dict[key]["dou_sections"] = subsearch.get(
                    "dou_sections", ["TODOS"]
                )
                search_dict[key]["search_date"] = subsearch.get("date", "DIA")
                search_dict[key]["field"] = subsearch.get("field", "TUDO")
                search_dict[key]["is_exact_search"] = subsearch.get(
                    "is_exact_search", True
                )
                search_dict[key]["ignore_signature_match"] = subsearch.get(
                    "ignore_signature_match", False
                )
                search_dict[key]["force_rematch"] = subsearch.get("force_rematch", None)
                search_dict[key]["full_text"] = subsearch.get("full_text", None)
                search_dict[key]["department"] = subsearch.get("department", None)

        # Optional fields
        owner = ", ".join(dag.get("owner", []))
        discord_webhook = (
            report["discord"]["webhook"] if report.get("discord") else None
        )
        slack_webhook = report["slack"]["webhook"] if report.get("slack") else None

        schedule = self._get_safe_schedule(dag, self.DEFAULT_SCHEDULE)
        doc_md = dag.get("doc_md", None)
        if doc_md:
            doc_md = textwrap.dedent(doc_md)
        dag_tags = dag.get("tags", [])
        # add default tags
        dag_tags.append("dou")
        dag_tags.append("generated_dag")
        skip_null = report.get("skip_null", True)
        emails = report.get("emails")
        subject = report.get("subject", "Extraçao do DOU")
        attach_csv = report.get("attach_csv", False)

        return DAGConfig(
            dag_id=dag_id,
            search_dict=search_dict,
            emails=emails,
            subject=subject,
            attach_csv=attach_csv,
            discord_webhook=discord_webhook,
            slack_webhook=slack_webhook,
            schedule=schedule,
            description=description,
            skip_null=skip_null,
            doc_md=doc_md,
            dag_tags=set(dag_tags),
            owner=owner,
        )

    def _get_terms_params(self, search) -> Tuple[List[str], str, str]:
        """Parses the `terms` config property handling different options."""
        terms = self._try_get(search, "terms")
        sql = None
        conn_id = None
        if isinstance(terms, dict):
            if "from_airflow_variable" in terms:
                var_value = Variable.get(terms.get("from_airflow_variable"))
                try:
                    terms = ast.literal_eval(var_value)
                except (ValueError, SyntaxError):
                    terms = var_value.splitlines()
            elif "from_db_select" in terms:
                from_db_select = terms.get("from_db_select")
                terms = []
                sql = self._try_get(from_db_select, "sql")
                conn_id = self._try_get(from_db_select, "conn_id")
            else:
                raise ValueError(
                    "O campo `terms` aceita como valores válidos "
                    "uma lista de strings ou parâmetros do tipo "
                    "`from_airflow_variable` ou `from_db_select`."
                )
        return terms, sql, conn_id

    def _try_get(self, variable: dict, field, error_msg=None):
        """Tries to retrieve mandatory property named `field` from
        `variable` dict and raises appropriate message"""
        try:
            return variable[field]
        except KeyError:
            if not error_msg:
                error_msg = f"O campo `{field}` é obrigatório."
            file_name = self.filepath.split("/")[-1]
            error_msg = f"Erro no arquivo {file_name}: {error_msg}"
            raise ValueError(error_msg)
