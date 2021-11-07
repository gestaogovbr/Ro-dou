"""Abstract and concrete classes to parse DAG configuration from a file.
"""

from abc import ABC, abstractmethod
import ast
import yaml

from airflow.models import Variable



class FileParser(ABC):
    """Abstract class to build file parsers with DAG configuration.
    """
    @abstractmethod
    def parse(self):
        pass

    def _hash_dag_id(self, dag_id: str, size: int) -> int:
        """Hashes the `dag_id` into a integer between 0 and `size`"""
        buffer = 0
        for _char in dag_id:
            buffer += (ord(_char))
        try:
            _hash = buffer % size
        except ZeroDivisionError:
            raise ValueError('`size` deve ser maior que 0.')
        return _hash

    def _get_safe_schedule(self, dag: dict, default_schedule: str) -> str:
        """Retorna um novo valor de `schedule_interval` randomizando o
        minuto de execução baseado no `dag_id`, caso a dag utilize o
        schedule_interval padrão. Aplica uma função de hash na string
        dag_id que retorna valor entre 0 e 60 que define o minuto de
        execução.
        """
        schedule = dag.get('schedule_interval', default_schedule)
        if schedule == default_schedule:
            id_based_minute = self._hash_dag_id(dag['id'], 60)
            schedule_without_min = ' '.join(schedule.split(" ")[1:])
            schedule = f'{id_based_minute} {schedule_without_min}'
        return schedule

class YAMLParser(FileParser):
    """Parses YAML file and get the DAG parameters.

    It guarantees that mandatory fields are in place and are properly
    defined providing clear error messages.
    """
    DEFAULT_SCHEDULE = '0 5 * * *'

    def __init__(self, filepath: str):
        self.filepath = filepath

    def parse(self):
        return self._parse_yaml()

    def _parse_yaml(self):
        """Processes the config file in order to instantiate the DAG in
        Airflow.
        """
        with open(self.filepath, 'r') as file:
            dag_config_dict = yaml.safe_load(file)

        dag = self._try_get(dag_config_dict, 'dag')
        dag_id = self._try_get(dag, 'id')
        description = self._try_get(dag, 'description')
        report = self._try_get(dag, 'report')
        emails = self._try_get(report, 'emails')
        search = self._try_get(dag, 'search')
        terms, sql, conn_id = self._get_terms_params(search)

        # Optional fields
        dou_sections = search.get('dou_sections', ['TODOS'])
        search_date = search.get('date', 'DIA')
        field = search.get('field', 'TUDO')
        is_exact_search = search.get('is_exact_search', True)
        ignore_signature_match = search.get('ignore_signature_match', False)
        force_rematch = search.get('force_rematch', False)
        schedule = self._get_safe_schedule(dag, self.DEFAULT_SCHEDULE)
        dag_tags = dag.get('tags', [])
        # add default tags
        dag_tags.append('dou')
        dag_tags.append('generated_dag')
        subject = report.get('subject', 'Extraçao do DOU')
        attach_csv = report.get('attach_csv', False)

        return (
            dag_id,
            dou_sections,
            search_date,
            field,
            is_exact_search,
            ignore_signature_match,
            force_rematch,
            terms,
            sql,
            conn_id,
            emails,
            subject,
            attach_csv,
            schedule,
            description,
            set(dag_tags),
            )

    def _get_terms_params(self, search):
        """Parses the `terms` config property handling different options.
        """
        terms = self._try_get(search, 'terms')
        sql = None
        conn_id = None
        if isinstance(terms, dict):
            if 'from_airflow_variable' in terms:
                var_value = Variable.get(terms.get('from_airflow_variable'))
                try:
                    terms = ast.literal_eval(var_value)
                except (ValueError, SyntaxError):
                    terms = var_value.splitlines()
            elif 'from_db_select' in terms:
                from_db_select = terms.get('from_db_select')
                terms = []
                sql = self._try_get(from_db_select, 'sql')
                conn_id = self._try_get(from_db_select, 'conn_id')
            else:
                raise ValueError(
                    'O campo `terms` aceita como valores válidos '
                    'uma lista de strings ou parâmetros do tipo '
                    '`from_airflow_variable` ou `from_db_select`.')
        return terms, sql, conn_id

    def _try_get(self, variable: dict, field, error_msg=None):
        """Tries to retrieve the property named as `field` from
        `variable` dict and raises apropriate message"""
        try:
            return variable[field]
        except KeyError:
            if not error_msg:
                error_msg = f'O campo `{field}` é obrigatório.'
            file_name = self.filepath.split('/')[-1]
            error_msg = f'Erro no arquivo {file_name}: {error_msg}'
            raise ValueError(error_msg)
