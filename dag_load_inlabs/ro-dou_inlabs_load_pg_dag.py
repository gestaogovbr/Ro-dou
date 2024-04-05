"""Airflow DAG to download yml files from INLABS and store data into
Postgres db.
"""

import os
import sys
import subprocess
import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models import Variable

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Constants

DEST_DIR = "download_inlabs"
#XXX update here
DEST_CONN_ID = "database_to_load_inlabs_data"
#XXX connection to https://inlabs.in.gov.br/
INLABS_CONN_ID = "inlabs_portal"
#XXX remember to create schema `dou_inlabs` on db
STG_TABLE = "dou_inlabs.article_raw"


# DAG

default_args = {
    #XXX update here
    "owner": "your-name",
    "start_date": datetime(2024, 4, 1),
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="ro-dou_inlabs_load_pg",
    default_args=default_args,
    schedule="59 3,23 * * *",
    catchup=False,
    description=__doc__,
    max_active_runs=1,
    params={"trigger_date": "YYYY-MM-DD"},
    tags=["ro-dou", "inlabs"],
)
def load_inlabs():

    @task
    def get_date() -> str:
        """Returns DAG trigger_date in YYYY-MM-DD"""
        from airflow.operators.python import get_current_context
        from utils.date import get_trigger_date

        context = get_current_context()
        return get_trigger_date(context, local_time=True).strftime("%Y-%m-%d")

    @task
    def download_n_unzip_files(trigger_date: str):
        import requests
        from bs4 import BeautifulSoup
        import zipfile
        from urllib.parse import urljoin
        from airflow.hooks.base import BaseHook

        def _create_directories():
            subprocess.run(f"mkdir -p {dest_path}", shell=True, check=True)
            logging.info("Directory %s avaliable.", dest_path)

        def _get_session():
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            session = requests.Session()
            session.request(
                "POST",
                urljoin(inlabs_conn.host, "logar.php"),
                data={"email": inlabs_conn.login, "password": inlabs_conn.password},
                headers=headers,
            )
            # Test if logged
            if not session.cookies.get("inlabs_session_cookie", False):
                raise ValueError("Auth failed")
            return session

        def _find_files(session, headers):
            response = session.request(
                "GET",
                urljoin(inlabs_conn.host, f"index.php?p={trigger_date}"),
                headers=headers,
            )
            soup = BeautifulSoup(response.text, "html.parser")
            a_tags = soup.find_all("a", title="Baixar Arquivo")
            files = [
                tag.get("href") for tag in a_tags if tag.get("href").endswith(".zip")
            ]
            return files

        def _download_files():
            session = _get_session()
            cookie = session.cookies.get("inlabs_session_cookie")
            headers = {
                "Cookie": f"inlabs_session_cookie={cookie}",
                "origem": "736372697074",
            }
            files = _find_files(session, headers)
            for file in files:
                r = session.request(
                    "GET",
                    urljoin(inlabs_conn.host, f"index.php{file}"),
                    headers=headers,
                )
                with open(os.path.join(dest_path, file.split("dl=")[1]), "wb") as f:
                    f.write(r.content)

            logging.info("Downloaded files: %s", files)

        def _unzip_files():
            all_files = os.listdir(dest_path)
            # filter zip files
            zip_files = [file for file in all_files if file.endswith(".zip")]
            for zip_file in zip_files:
                zip_file_path = os.path.join(dest_path, zip_file)
                with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                    zip_ref.extractall(os.path.join(dest_path, trigger_date))
            logging.info("Unzipped files: %s", zip_files)

        inlabs_conn = BaseHook.get_connection(INLABS_CONN_ID)
        dest_path = os.path.join(Variable.get("path_tmp"), DEST_DIR)
        _create_directories()
        _download_files()
        _unzip_files()

    @task
    def load_data(trigger_date: str):
        from bs4 import BeautifulSoup
        import glob
        import pandas as pd
        from slugify import slugify
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        def _read_files():
            dest_path = os.path.join(Variable.get("path_tmp"), DEST_DIR)
            df = pd.DataFrame()
            for xml_file in glob.glob(
                os.path.join(dest_path, trigger_date, "**/*.xml"), recursive=True
            ):
                df1 = pd.read_xml(xml_file)
                df2 = pd.read_xml(xml_file, xpath="//body")
                df = pd.concat([df, df1.join(df2)], ignore_index=True)

            df.columns = [slugify(col, separator="_") for col in df.columns]
            df.drop(columns=["body"], inplace=True)
            df["pubdate"] = pd.to_datetime(df["pubdate"], format="%d/%m/%Y")
            df["assina"] = df["texto"].apply(_get_assina)

            return df

        def _get_assina(text):
            soup = BeautifulSoup(text, "html.parser")
            p_tags = soup.find_all("p", class_="assina")
            return ", ".join([p.text for p in p_tags]) if p_tags else None

        def _clean_db(hook: PostgresHook):
            table_exists = hook.get_first(
                f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = '{STG_TABLE.split(".")[1]}'
                );
            """
            )
            if table_exists[0]:
                hook.run(
                    f"DELETE FROM {STG_TABLE} WHERE DATE(pubdate) = '{trigger_date}'"
                )

        df = _read_files()
        hook = PostgresHook(DEST_CONN_ID)
        _clean_db(hook)
        df.to_sql(
            name=STG_TABLE.split(".")[1],
            schema=STG_TABLE.split(".", maxsplit=1)[0],
            con=hook.get_sqlalchemy_engine(),
            if_exists="append",
            index=False,
        )
        logging.info("Table `%s` updated with %s lines.", STG_TABLE, len(df))

    @task
    def remove_directory():
        dest_path = os.path.join(Variable.get("path_tmp"), DEST_DIR)
        subprocess.run(f"rm -rf {dest_path}", shell=True, check=True)
        logging.info("Directory %s removed.", dest_path)

    ## Orchestration
    trigger_date = get_date()
    download_n_unzip_files(trigger_date) >> \
    load_data(trigger_date) >> \
    remove_directory()


load_inlabs()
