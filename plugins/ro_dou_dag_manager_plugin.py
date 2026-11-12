"""Plugin do Airflow que adiciona a tela de gestão das DAGs do Ro-DOU.

Só é ativado quando ``RO_DOU__DAG_MANAGER_DIR`` está definido: é nesse
diretório que a tela grava os YAMLs, e ele precisa constar também em
``RO_DOU__DAG_CONF_DIR`` para que o gerador crie as DAGs.
"""

import os

from airflow.plugins_manager import AirflowPlugin

URL_PREFIX = "/ro-dou-dags"


def _fastapi_apps() -> list:
    if not os.getenv("RO_DOU__DAG_MANAGER_DIR"):
        return []
    from ro_dou_dag_manager.api import create_app

    return [{"app": create_app(), "url_prefix": URL_PREFIX, "name": "Ro-DOU — DAGs"}]


def _external_views() -> list:
    if not os.getenv("RO_DOU__DAG_MANAGER_DIR"):
        return []
    # Botão próprio no primeiro nível do menu lateral (sem categoria: com
    # "browse" ele ficaria escondido no submenu Browse)
    return [
        {
            "name": "Ro-DOU DAGs",
            "href": f"{URL_PREFIX}/",
            "url_route": "ro-dou-dags",
            "destination": "nav",
            "nav_top_level": True,
            "icon": f"{URL_PREFIX}/icon.svg",
            "icon_dark_mode": f"{URL_PREFIX}/icon-dark.svg",
        }
    ]


class RoDouDagManagerPlugin(AirflowPlugin):
    name = "ro_dou_dag_manager"
    fastapi_apps = _fastapi_apps()
    external_views = _external_views()
