"""Testes das funções puras do diagnóstico de VPS."""

import inspect
import os
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from tools.diagnostico_vps import (
    _decodificar_endereco,
    _fmt_bytes,
    avaliar,
)

GIB = 1024**3


def _dados_base() -> dict:
    return {
        "host": {
            "familia": "Linux",
            "sistema": "Ubuntu 24.04 LTS",
            "arquitetura": "x86_64",
            "fuso_horario": "America/Sao_Paulo",
            "ntp_sincronizado": True,
        },
        "cpu": {"threads": 4, "limite_cgroup_cpus": None},
        "memoria": {
            "total_bytes": 8 * GIB,
            "swap_total_bytes": 2 * GIB,
            "limite_cgroup_bytes": None,
        },
        "disco": {
            "livre_raiz_bytes": 50 * GIB,
            "montagens": [{"ponto": "/", "livre_bytes": 50 * GIB}],
        },
        "docker": {
            "instalado": True,
            "daemon_acessivel": True,
            "compose": "2.30.0",
            "compose_v1": None,
            "erro": None,
        },
        "ferramentas": {
            "caminhos": {
                "bash": "/bin/bash",
                "make": "/usr/bin/make",
                "curl": "/usr/bin/curl",
                "python3": "/usr/bin/python3",
                "git": "/usr/bin/git",
            }
        },
        "kernel": {"vm.max_map_count": "262144"},
        "portas": {"criticas": []},
        "rede": {"conectividade": None},
        "seguranca": {
            "ssh": {"efetivas": {}},
            "firewall": {"ativo": True},
            "fail2ban": "active",
            "reinicio_pendente": False,
        },
    }


def test_fmt_bytes():
    assert _fmt_bytes(0) == "0.0 B"
    assert _fmt_bytes(1024) == "1.0 KiB"
    assert _fmt_bytes(4 * GIB) == "4.0 GiB"


def test_decodificar_endereco_ipv4():
    assert _decodificar_endereco("0100007F") == "127.0.0.1"
    assert _decodificar_endereco("00000000") == "0.0.0.0"


def test_decodificar_endereco_ipv6():
    assert _decodificar_endereco("00000000000000000000000001000000") == "::1"


def test_avaliar_viavel():
    resultado = avaliar(_dados_base())
    assert resultado["veredito"] == "viavel"
    assert resultado["bloqueadores"] == []
    assert resultado["alertas"] == []


def test_avaliar_bloqueia_sem_docker():
    dados = _dados_base()
    dados["docker"]["instalado"] = False
    resultado = avaliar(dados)
    assert resultado["veredito"] == "inviavel"
    assert any("Docker" in item for item in resultado["bloqueadores"])


def test_avaliar_bloqueia_ram_insuficiente():
    dados = _dados_base()
    dados["memoria"]["total_bytes"] = 2 * GIB
    resultado = avaliar(dados)
    assert resultado["veredito"] == "inviavel"
    assert any("Memória" in item for item in resultado["bloqueadores"])


def test_avaliar_aceita_vps_de_4gb_decimais():
    dados = _dados_base()
    dados["memoria"]["total_bytes"] = 3_800_000_000
    resultado = avaliar(dados)
    assert not any("Memória" in item for item in resultado["bloqueadores"])
    assert resultado["veredito"] == "viavel_com_ressalvas"


def test_avaliar_nao_recomenda_swap_com_ram_suficiente():
    dados = _dados_base()
    dados["memoria"]["total_bytes"] = 16 * GIB
    dados["memoria"]["swap_total_bytes"] = 0
    resultado = avaliar(dados)
    assert not any("swap" in item.lower() for item in resultado["recomendacoes"])


def test_avaliar_fuso_utc_nao_gera_alerta():
    dados = _dados_base()
    dados["host"]["fuso_horario"] = "Etc/UTC"
    resultado = avaliar(dados)
    assert resultado["veredito"] == "viavel"
    assert not any("Fuso" in item for item in resultado["alertas"])
    assert any(
        "AIRFLOW__CORE__DEFAULT_TIMEZONE" in item for item in resultado["recomendacoes"]
    )


def test_avaliar_opensearch_exige_max_map_count():
    dados = _dados_base()
    dados["kernel"]["vm.max_map_count"] = "65530"
    resultado = avaliar(dados, com_opensearch=True)
    assert resultado["veredito"] == "inviavel"
    assert any("max_map_count" in item for item in resultado["bloqueadores"])


def test_avaliar_alerta_porta_ocupada():
    dados = _dados_base()
    dados["portas"]["criticas"] = [
        {
            "porta": 8080,
            "servico": "Airflow (interface/API)",
            "em_uso": True,
            "enderecos": ["0.0.0.0"],
            "usuarios": ["root"],
        }
    ]
    resultado = avaliar(dados)
    assert resultado["veredito"] == "viavel_com_ressalvas"
    assert any("8080" in item for item in resultado["alertas"])
