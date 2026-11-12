"""Testes da tela de gestão de DAGs (plugin ro_dou_dag_manager)."""

import os
import sys
import textwrap

import pytest
from fastapi.testclient import TestClient

_TESTS_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_TESTS_DIR, "..", "plugins")))

from ro_dou_dag_manager import api as manager_api  # noqa: E402
from ro_dou_dag_manager.storage import (  # noqa: E402
    ConflictError,
    DagConfStore,
    NotFoundError,
    ReadOnlyError,
    StoreError,
    etag_of,
)
from ro_dou_dag_manager.validation import mask_secrets, validate_content  # noqa: E402


def dag_yaml(dag_id="minha_dag", extra_report="", terms="- dados abertos"):
    """YAML mínimo válido; `terms` e `extra_report` entram já indentados."""
    terms = textwrap.indent(terms, " " * 6).lstrip()
    return (
        "dag:\n"
        f"  id: {dag_id}\n"
        "  description: DAG de teste\n"
        "  search:\n"
        "    terms:\n"
        f"      {terms}\n"
        "  report:\n"
        "    emails:\n"
        "      - destination@economia.gov.br\n"
        f"{extra_report}"
    )


TEAMS_URL = (
    "https://prod-00.westus.logic.azure.com:443/workflows/WorkflowID/triggers/"
    "manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=Signature"
)


@pytest.fixture()
def dirs(tmp_path):
    git_dir = tmp_path / "dag_confs"
    ui_dir = tmp_path / "dag_confs_ui"
    git_dir.mkdir()
    ui_dir.mkdir()
    (git_dir / "do_git.yaml").write_text(dag_yaml("dag_do_git"), encoding="utf-8")
    return git_dir, ui_dir


@pytest.fixture()
def store(dirs):
    git_dir, ui_dir = dirs
    return DagConfStore([str(git_dir), str(ui_dir)], str(ui_dir))


# ------------------------------------------------------------------ storage


def test_lista_dags_de_todas_as_fontes(store):
    store.create("nova_dag", dag_yaml("nova_dag"))
    entries = {e.dag_id: e for e in store.list_entries()}
    assert entries["dag_do_git"].editable is False
    assert entries["nova_dag"].editable is True
    assert entries["nova_dag"].path == "nova_dag.yaml"
    assert entries["nova_dag"].sources == ["DOU"]


def test_lista_usa_o_mesmo_criterio_de_arquivo_do_gerador(store, dirs):
    git_dir, _ = dirs
    # o gerador carrega por substring da extensão: a tela precisa enxergar
    (git_dir / "antiga.yaml.bak").write_text(dag_yaml("dag_bak"), encoding="utf-8")
    assert "dag_bak" in {e.dag_id for e in store.list_entries()}
    with pytest.raises(ConflictError):
        store.create("dag_bak", dag_yaml("dag_bak"))


def test_lista_ignora_symlink_para_fora(store, dirs, tmp_path):
    git_dir, _ = dirs
    fora = tmp_path / "segredo.txt"
    fora.write_text("conteudo: [secreto", encoding="utf-8")
    (git_dir / "link.yaml").symlink_to(fora)
    assert "link.yaml" not in {e.path for e in store.list_entries()}


def test_erro_de_escrita_vira_mensagem_clara(store, dirs):
    _, ui_dir = dirs
    os.chmod(ui_dir, 0o555)
    try:
        if os.access(ui_dir, os.W_OK):
            pytest.skip("usuário root ignora permissões de diretório")
        with pytest.raises(StoreError, match="permissão"):
            store.create("nova_dag", dag_yaml("nova_dag"))
    finally:
        os.chmod(ui_dir, 0o755)


def test_lista_marca_arquivo_invalido(store, dirs):
    git_dir, _ = dirs
    (git_dir / "quebrado.yml").write_text("dag: [", encoding="utf-8")
    entry = next(e for e in store.list_entries() if e.path == "quebrado.yml")
    assert entry.error and entry.dag_id is None


def test_cria_arquivo_sem_deixar_temporario(store, dirs):
    _, ui_dir = dirs
    store.create("nova_dag", dag_yaml("nova_dag"))
    names = sorted(p.name for p in ui_dir.iterdir())
    # o gerador seleciona por substring ".yaml"/".yml": nada auxiliar pode conter isso
    assert [n for n in names if ".yaml" in n or ".yml" in n] == ["nova_dag.yaml"]


def test_cria_recusa_dag_id_duplicado_em_outra_fonte(store):
    with pytest.raises(ConflictError, match="dag_do_git"):
        store.create("dag_do_git", dag_yaml("dag_do_git"))


def test_atualiza_com_etag_correto(store):
    store.create("nova_dag", dag_yaml("nova_dag"))
    source = store.managed_source.index
    _, content, etag = store.read(source, "nova_dag.yaml")
    novo = content.replace("DAG de teste", "Alterada")
    new_etag = store.update(source, "nova_dag.yaml", "nova_dag", novo, etag)
    _, lido, etag_lido = store.read(source, "nova_dag.yaml")
    assert "Alterada" in lido and new_etag == etag_lido == etag_of(novo.encode())


def test_atualiza_recusa_etag_desatualizado(store):
    store.create("nova_dag", dag_yaml("nova_dag"))
    source = store.managed_source.index
    with pytest.raises(ConflictError):
        store.update(source, "nova_dag.yaml", "nova_dag", dag_yaml("nova_dag"), "0" * 64)


def test_atualiza_recusa_trocar_para_id_existente(store):
    store.create("nova_dag", dag_yaml("nova_dag"))
    source = store.managed_source.index
    _, _, etag = store.read(source, "nova_dag.yaml")
    with pytest.raises(ConflictError):
        store.update(source, "nova_dag.yaml", "dag_do_git", dag_yaml("dag_do_git"), etag)


def test_fonte_git_e_somente_leitura(store):
    _, _, etag = store.read(0, "do_git.yaml")
    with pytest.raises(ReadOnlyError):
        store.update(0, "do_git.yaml", "dag_do_git", dag_yaml("dag_do_git"), etag)
    with pytest.raises(ReadOnlyError):
        store.delete(0, "do_git.yaml", etag)


def test_exclui(store, dirs):
    _, ui_dir = dirs
    store.create("nova_dag", dag_yaml("nova_dag"))
    source = store.managed_source.index
    _, _, etag = store.read(source, "nova_dag.yaml")
    store.delete(source, "nova_dag.yaml", etag)
    assert not (ui_dir / "nova_dag.yaml").exists()


@pytest.mark.parametrize(
    "relpath", ["../dag_confs/do_git.yaml", "/etc/passwd.yaml", "", "nao_existe.yaml", "x.txt"]
)
def test_resolve_bloqueia_caminhos_fora_da_fonte(store, relpath):
    with pytest.raises(NotFoundError):
        store.read(1, relpath)


def test_resolve_bloqueia_symlink_para_fora(store, dirs, tmp_path):
    _, ui_dir = dirs
    fora = tmp_path / "segredo.yaml"
    fora.write_text("dag: {}", encoding="utf-8")
    (ui_dir / "link.yaml").symlink_to(fora)
    with pytest.raises(NotFoundError):
        store.read(store.managed_source.index, "link.yaml")


def test_diretorio_gerenciado_fora_do_conf_dir_bloqueia_escrita(dirs):
    git_dir, ui_dir = dirs
    store = DagConfStore([str(git_dir)], str(ui_dir))
    assert store.misconfigured
    with pytest.raises(StoreError):
        store.create("nova_dag", dag_yaml("nova_dag"))


# --------------------------------------------------------------- validation


def test_valida_yaml_correto():
    result = validate_content(dag_yaml())
    assert result.valid, result.errors
    assert result.dag_id == "minha_dag"


def test_valida_erros_do_schema():
    result = validate_content("dag:\n  id: x\n")
    assert not result.valid
    assert any("description" in e for e in result.errors)


@pytest.mark.parametrize("dag_id", ["com espaço", "../x", ".oculto", "-x", "ação"])
def test_valida_dag_id(dag_id):
    result = validate_content(dag_yaml(f"'{dag_id}'"))
    assert any(e.startswith("dag.id") for e in result.errors)


def test_valida_recusa_aliases_yaml():
    content = "a: &x [1, 2]\nb: *x\n" + dag_yaml()
    result = validate_content(content)
    assert any("aliases" in e for e in result.errors)


def test_valida_recusa_yaml_grande():
    result = validate_content(dag_yaml() + "#" * (300 * 1024))
    assert any("limite" in e for e in result.errors)


@pytest.mark.parametrize(
    "url",
    [
        TEAMS_URL,
        "discord://1234/token",
        "slack://T1/B1/abc",
        "workflows://prod-00.westus.logic.azure.com:443/WorkflowID/Signature/",
    ],
)
def test_valida_aceita_canais_permitidos(url):
    extra = f"    notification:\n      - '{url}'\n"
    result = validate_content(dag_yaml(extra_report=extra))
    assert result.valid, result.errors


@pytest.mark.parametrize(
    "url",
    [
        "json://servico-interno:8080/x",
        "https://servico-interno.local/hook",
        # host livre no Apprise: só o do Teams é aceito
        "workflows://10.0.0.5:8080/WorkflowID/Signature/",
        # não existe no Apprise 1.13.1
        "msteams://token",
        "http://prod-00.westus.logic.azure.com/workflows/x/triggers/y?sig=z",
    ],
)
def test_valida_recusa_canais_nao_permitidos(url):
    extra = f"    notification:\n      - '{url}'\n"
    result = validate_content(dag_yaml(extra_report=extra))
    assert any("report.notification" in e for e in result.errors)


def test_valida_canais_configuraveis_por_ambiente(monkeypatch):
    monkeypatch.setenv("RO_DOU__DAG_MANAGER_NOTIFICATION_SCHEMES", "tgram")
    extra = "    notification:\n      - 'tgram://bot/chat'\n"
    assert validate_content(dag_yaml(extra_report=extra)).valid


@pytest.mark.parametrize("schedule", ["foo bar", "0 8 * *", "99 * * * *"])
def test_valida_recusa_cron_invalido(schedule):
    content = dag_yaml().replace("  description:", f"  schedule: '{schedule}'\n  description:")
    assert any(e.startswith("dag.schedule") for e in validate_content(content).errors)


@pytest.mark.parametrize("schedule", ["0 8 * * MON-FRI", "@daily"])
def test_valida_aceita_cron_valido(schedule):
    content = dag_yaml().replace("  description:", f"  schedule: '{schedule}'\n  description:")
    assert validate_content(content).valid


def test_mascara_tokens_de_webhook():
    extra = f"    notification:\n      - '{TEAMS_URL}'\n      - discord://1234/tokensecreto\n"
    content = dag_yaml(extra_report=extra)
    data = validate_content(content).data
    masked, masked_data = mask_secrets(content, data)
    assert "Signature" not in masked and "tokensecreto" not in masked
    assert "Signature" not in str(masked_data) and "tokensecreto" not in str(masked_data)
    assert "prod-00.westus.logic.azure.com/***" in masked


def test_valida_coleta_conexoes_e_variaveis():
    terms = "from_db_select:\n  sql: SELECT termo FROM termos\n  conn_id: minha_conexao"
    result = validate_content(dag_yaml(terms=terms))
    assert result.valid, result.errors
    assert result.connections == {"minha_conexao"}

    terms = "from_airflow_variable: minha_variavel"
    result = validate_content(dag_yaml(terms=terms))
    assert result.variables == {"minha_variavel"}


def test_valida_exemplo_do_teams():
    path = os.path.join(_TESTS_DIR, "..", "dags", "ro_dou", "dag_confs", "examples_and_tests", "teams_example.yaml")
    if not os.path.exists(path):
        path = os.path.join(_TESTS_DIR, "..", "dag_confs", "examples_and_tests", "teams_example.yaml")
    with open(path, encoding="utf-8") as file:
        assert validate_content(file.read()).valid


# ---------------------------------------------------------------------- API


class FakeUser:
    def get_name(self):
        return "maria"


class FakeAuthorizer:
    def __init__(self, read=True, write=True, connections=True, variables=True,
                 authenticated=True, readable_dags=None, writable_dags=None):
        """readable_dags/writable_dags: None libera todas; um conjunto restringe
        as checagens com dag_id (como as permissões por DAG do FAB)."""
        self.read, self.write = read, write
        self.readable_dags, self.writable_dags = readable_dags, writable_dags
        self.connections, self.variables = connections, variables
        self.authenticated = authenticated
        self.write_checks = []

    async def user(self, request):
        if not self.authenticated:
            raise manager_api.HTTPException(status_code=401, detail="Not authenticated")
        return FakeUser()

    def can_read(self, user, dag_id=None):
        if dag_id and self.readable_dags is not None:
            return dag_id in self.readable_dags
        return self.read

    def can_write(self, user, dag_id=None):
        self.write_checks.append(dag_id)
        if dag_id and self.writable_dags is not None:
            return dag_id in self.writable_dags
        return self.write

    def can_use_connection(self, user, conn_id):
        return self.connections

    def can_read_variable(self, user, key):
        return self.variables

    @staticmethod
    def user_name(user):
        return user.get_name()


HEADERS = {"X-Ro-Dou-Request": "1"}


@pytest.fixture()
def make_client(store, monkeypatch, tmp_path):
    gerador = tmp_path / "gerador_yaml.html"
    gerador.write_text("<html>gerador</html>", encoding="utf-8")
    monkeypatch.setenv("RO_DOU__GERADOR_HTML", str(gerador))

    def factory(**perms):
        app = manager_api.create_app()
        authorizer = FakeAuthorizer(**perms)
        app.dependency_overrides[manager_api.get_authorizer] = lambda: authorizer
        app.dependency_overrides[manager_api.get_store] = lambda: store
        client = TestClient(app)
        client.authorizer = authorizer
        return client

    return factory


def test_api_paginas_estaticas(make_client):
    client = make_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "frame-ancestors 'self'" in resp.headers["content-security-policy"]
    assert client.get("/gerador").text == "<html>gerador</html>"


@pytest.mark.parametrize("name", ["icon.svg", "icon-dark.svg"])
def test_api_icones_do_menu(make_client, name):
    resp = make_client(authenticated=False).get(f"/{name}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")


def test_plugin_fica_no_primeiro_nivel_do_menu(monkeypatch):
    import importlib

    monkeypatch.setenv("RO_DOU__DAG_MANAGER_DIR", "/tmp/dag_confs_ui")
    plugin = importlib.import_module("ro_dou_dag_manager_plugin")
    (view,) = plugin._external_views()
    assert view["nav_top_level"] is True and "category" not in view
    assert view["icon"].startswith(plugin.URL_PREFIX)
    monkeypatch.delenv("RO_DOU__DAG_MANAGER_DIR")
    assert plugin._external_views() == [] and plugin._fastapi_apps() == []


def test_api_exige_autenticacao(make_client):
    client = make_client(authenticated=False)
    assert client.get("/api/dags").status_code == 401


def test_api_exige_permissao_de_leitura(make_client):
    assert make_client(read=False).get("/api/dags").status_code == 403


def test_api_fluxo_completo(make_client):
    client = make_client()
    status = client.get("/api/status").json()
    assert status["can_write"] is True and status["user"] == "maria"

    resp = client.post("/api/dags", json={"content": dag_yaml("nova_dag")}, headers=HEADERS)
    assert resp.status_code == 201, resp.text
    source, path = resp.json()["source"], resp.json()["path"]

    items = client.get("/api/dags").json()["items"]
    assert {i["dag_id"] for i in items} == {"dag_do_git", "nova_dag"}

    dag = client.get(f"/api/dags/{source}/{path}").json()
    assert dag["editable"] and dag["data"]["dag"]["id"] == "nova_dag"

    novo = dag["content"].replace("DAG de teste", "Alterada")
    resp = client.put(
        f"/api/dags/{source}/{path}", json={"content": novo, "etag": dag["etag"]}, headers=HEADERS
    )
    assert resp.status_code == 200, resp.text
    # o etag antigo não serve mais
    resp = client.put(
        f"/api/dags/{source}/{path}", json={"content": novo, "etag": dag["etag"]}, headers=HEADERS
    )
    assert resp.status_code == 409

    etag = client.get(f"/api/dags/{source}/{path}").json()["etag"]
    resp = client.delete(f"/api/dags/{source}/{path}", params={"etag": etag}, headers=HEADERS)
    assert resp.status_code == 204
    assert client.get(f"/api/dags/{source}/{path}").status_code == 404


def test_api_escrita_exige_cabecalho_csrf(make_client):
    client = make_client()
    resp = client.post("/api/dags", json={"content": dag_yaml("nova_dag")})
    assert resp.status_code == 403


def test_api_escrita_exige_permissao_de_edicao(make_client):
    client = make_client(write=False)
    assert client.get("/api/status").json()["can_write"] is False
    resp = client.post("/api/dags", json={"content": dag_yaml("nova_dag")}, headers=HEADERS)
    assert resp.status_code == 403


def test_api_create_retorna_erros_de_validacao(make_client):
    client = make_client()
    resp = client.post("/api/dags", json={"content": "dag:\n  id: x\n"}, headers=HEADERS)
    assert resp.status_code == 422
    assert resp.json()["detail"]["errors"]


def test_api_exige_permissao_na_conexao_usada(make_client):
    client = make_client(connections=False)
    terms = "from_db_select:\n  sql: SELECT termo FROM termos\n  conn_id: banco_restrito"
    resp = client.post("/api/dags", json={"content": dag_yaml(terms=terms)}, headers=HEADERS)
    assert resp.status_code == 422
    assert any("banco_restrito" in e for e in resp.json()["detail"]["errors"])


def test_api_exige_permissao_na_variavel_usada(make_client):
    client = make_client(variables=False)
    resp = client.post(
        "/api/dags",
        json={"content": dag_yaml(terms="from_airflow_variable: segredo")},
        headers=HEADERS,
    )
    assert resp.status_code == 422
    assert any("segredo" in e for e in resp.json()["detail"]["errors"])


def test_api_checa_permissao_na_dag_especifica(make_client):
    client = make_client()
    client.post("/api/dags", json={"content": dag_yaml("nova_dag")}, headers=HEADERS)
    assert "nova_dag" in client.authorizer.write_checks


def test_api_nao_altera_dag_do_git(make_client):
    client = make_client()
    dag = client.get("/api/dags/0/do_git.yaml").json()
    assert dag["editable"] is False
    resp = client.put(
        "/api/dags/0/do_git.yaml", json={"content": dag["content"], "etag": dag["etag"]}, headers=HEADERS
    )
    assert resp.status_code == 403


def test_api_validate_devolve_dados(make_client):
    client = make_client()
    body = client.post("/api/validate", json={"content": dag_yaml()}).json()
    assert body["valid"] and body["data"]["dag"]["id"] == "minha_dag"


def test_api_lista_so_dags_com_permissao_de_leitura(make_client, dirs):
    git_dir, _ = dirs
    (git_dir / "outra.yaml").write_text(dag_yaml("outra_dag"), encoding="utf-8")
    (git_dir / "quebrado.yaml").write_text("dag: [", encoding="utf-8")
    client = make_client(write=False, readable_dags={"dag_do_git"})
    items = client.get("/api/dags").json()["items"]
    # arquivo inválido exige edição global; outra_dag não é legível
    assert [i["dag_id"] for i in items] == ["dag_do_git"]
    assert client.get("/api/dags/0/outra.yaml").status_code == 404
    assert client.get("/api/dags/0/quebrado.yaml").status_code == 404
    assert client.get("/api/dags/0/do_git.yaml").status_code == 200


def test_api_mascara_webhook_para_quem_nao_edita(make_client, dirs):
    git_dir, _ = dirs
    extra = f"    notification:\n      - '{TEAMS_URL}'\n"
    (git_dir / "teams.yaml").write_text(dag_yaml("dag_teams", extra_report=extra), encoding="utf-8")
    leitor = make_client(write=False)
    body = leitor.get("/api/dags/0/teams.yaml").json()
    assert "Signature" not in body["content"] and "Signature" not in str(body["data"])
    editor = make_client()
    assert "Signature" in editor.get("/api/dags/0/teams.yaml").json()["content"]


def test_api_can_edit_por_item(make_client):
    client = make_client(writable_dags={"editavel"})
    for dag_id in ("editavel", "bloqueada"):
        client.post("/api/dags", json={"content": dag_yaml(dag_id)}, headers=HEADERS)
    items = {i["dag_id"]: i["can_edit"] for i in client.get("/api/dags").json()["items"]}
    assert items == {"dag_do_git": False, "editavel": True}


def test_api_nao_edita_dag_sem_permissao_especifica(make_client):
    admin = make_client()
    created = admin.post("/api/dags", json={"content": dag_yaml("restrita")}, headers=HEADERS).json()
    client = make_client(writable_dags=set())
    dag = client.get(f"/api/dags/{created['source']}/{created['path']}").json()
    assert dag["can_edit"] is False
    resp = client.put(
        f"/api/dags/{created['source']}/{created['path']}",
        json={"content": dag["content"], "etag": dag["etag"]},
        headers=HEADERS,
    )
    assert resp.status_code == 422
