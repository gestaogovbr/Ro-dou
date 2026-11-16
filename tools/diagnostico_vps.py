#!/usr/bin/env python3
"""Coleta dados de uma VPS para avaliar a viabilidade de executar o Ro-DOU.

O script é somente leitura: não instala pacotes, não altera arquivos de
configuração e não envia dados para fora. As únicas conexões de rede são
testes TCP (handshake) para os hosts usados pelo Ro-DOU, que podem ser
desativados com ``--sem-rede``.

Uso típico na VPS::

    python3 diagnostico_vps.py
    python3 diagnostico_vps.py --json --saida diagnostico.json
    python3 diagnostico_vps.py --com-opensearch
    python3 diagnostico_vps.py --sem-rede --amostra 0.5

O relatório em texto traz um veredito (viável, viável com ressalvas ou
inviável), bloqueadores, alertas e recomendações. O JSON contém todos os
dados brutos coletados.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import ipaddress
import json
import os
import platform
import pwd
import resource
import shutil
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

VERSAO_SCHEMA = 1

# Requisitos documentados em docs/docs/como_utilizar/instalacao.md e no FAQ.
# A RAM usa GB decimais porque é assim que as VPS são anunciadas: uma VPS
# "de 4 GB" normalmente reporta ~3,8 GiB em /proc/meminfo. A tolerância de 5%
# evita classificar como inviável uma VPS de 4 GB por causa da reserva do
# kernel.
MIN_RAM_BYTES = 3_800_000_000
REC_RAM_BYTES = 8_000_000_000
MIN_DISCO_LIVRE_BYTES = 5 * 1024**3
REC_DISCO_LIVRE_BYTES = 20 * 1024**3
MIN_CPUS = 2
MAX_MAP_COUNT_OPENSEARCH = 262144

HOSTS_REDE = (
    ("INLABS", "inlabs.in.gov.br", 443),
    ("DOU", "www.in.gov.br", 443),
    ("Querido Diário", "api.queridodiario.org.br", 443),
    ("DOE-SP", "doe.sp.gov.br", 443),
    ("Docker Hub", "registry-1.docker.io", 443),
    ("PyPI", "pypi.org", 443),
    ("GitHub", "github.com", 443),
)

HOSTS_INSTALACAO = {"Docker Hub", "PyPI", "GitHub"}
HOSTS_FONTES = {"INLABS", "DOU", "Querido Diário", "DOE-SP"}

PORTAS_RODOU = {
    8080: "Airflow (interface/API)",
    5001: "smtp4dev (interface)",
    25: "smtp4dev (SMTP)",
    143: "smtp4dev (IMAP)",
    5432: "PostgreSQL",
    9200: "OpenSearch",
}

USAR_COR = True
COR_VERDE = "\033[32m"
COR_AMARELA = "\033[33m"
COR_VERMELHA = "\033[31m"
COR_AZUL = "\033[36m"
COR_CINZA = "\033[90m"
COR_RESET = "\033[0m"


# --------------------------------------------------------------- utilitários


def _ler(caminho: str) -> str | None:
    """Lê um arquivo de texto, devolvendo None se não for possível."""
    try:
        return Path(caminho).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _executar(
    comando: list[str], timeout: float = 5.0
) -> tuple[str | None, str | None]:
    """Executa um comando sem shell e devolve (stdout, erro).

    Em caso de código de saída diferente de zero, o stdout é descartado e o
    stderr (ou o próprio stdout) é devolvido como erro.
    """
    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return None, "comando não encontrado"
    except subprocess.TimeoutExpired:
        return None, f"timeout após {timeout:g}s"
    except OSError as exc:
        return None, str(exc)

    saida = (processo.stdout or "").strip()
    if processo.returncode != 0:
        erro = (processo.stderr or "").strip() or saida
        return None, erro or f"código de saída {processo.returncode}"
    return saida, None


def _executar_status(comando: list[str], timeout: float = 5.0) -> str | None:
    """Executa um comando e devolve o stdout mesmo com código diferente de 0."""
    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return (processo.stdout or "").strip() or None


def _int(valor: Any) -> int | None:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _fmt_bytes(valor: float | None) -> str:
    if valor is None:
        return "n/d"
    numero = float(valor)
    for unidade in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(numero) < 1024 or unidade == "TiB":
            return f"{numero:.1f} {unidade}"
        numero /= 1024
    return f"{numero:.1f} TiB"


def _fmt_bool(valor: bool | None) -> str:
    if valor is None:
        return "n/d"
    return "sim" if valor else "não"


def _fmt_duracao(segundos: float | None) -> str:
    if segundos is None:
        return "n/d"
    segundos = int(segundos)
    dias, resto = divmod(segundos, 86400)
    horas, resto = divmod(resto, 3600)
    minutos = resto // 60
    partes = []
    if dias:
        partes.append(f"{dias}d")
    if horas:
        partes.append(f"{horas}h")
    if minutos or not partes:
        partes.append(f"{minutos}min")
    return " ".join(partes)


def _pintar(texto: str, cor: str) -> str:
    if not USAR_COR:
        return texto
    return f"{cor}{texto}{COR_RESET}"


def _titulo(texto: str) -> str:
    return _pintar(f"\n── {texto} ──", COR_AZUL)


def _status(ok: bool | None) -> str:
    if ok is True:
        return _pintar("[ok]", COR_VERDE)
    if ok is False:
        return _pintar("[falha]", COR_VERMELHA)
    return _pintar("[n/d]", COR_CINZA)


def _decodificar_endereco(hexa: str) -> str:
    """Converte o endereço hexadecimal de /proc/net/tcp para texto."""
    try:
        bruto = bytes.fromhex(hexa)
    except ValueError:
        return hexa
    if len(bruto) == 4:
        return ".".join(str(byte) for byte in bruto[::-1])
    if len(bruto) == 16:
        # /proc/net/tcp6 representa cada palavra de 32 bits em little-endian.
        invertido = b"".join(bruto[i : i + 4][::-1] for i in range(0, 16, 4))
        return str(ipaddress.IPv6Address(invertido))
    return hexa


# ------------------------------------------------------------------ coletores


def coletar_host() -> dict[str, Any]:
    dados: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "sistema": None,
        "familia": platform.system(),
        "versao_sistema": None,
        "kernel": platform.release(),
        "arquitetura": platform.machine(),
        "hardware": None,
        "virtualizacao": None,
        "container": None,
        "uptime_segundos": None,
        "uptime_humano": None,
        "inicializado_em": None,
        "fuso_horario": None,
        "ntp_sincronizado": None,
        "hora_local": dt.datetime.now().astimezone().isoformat(),
    }

    try:
        os_release = platform.freedesktop_os_release()
    except (OSError, AttributeError):
        os_release = {}
    dados["sistema"] = os_release.get("PRETTY_NAME") or platform.platform()
    dados["versao_sistema"] = os_release.get("VERSION_ID")

    uptime = _ler("/proc/uptime")
    if uptime:
        try:
            segundos = float(uptime.split()[0])
        except (IndexError, ValueError):
            segundos = None
        if segundos is not None:
            dados["uptime_segundos"] = round(segundos)
            dados["uptime_humano"] = _fmt_duracao(segundos)
            inicio = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=segundos)
            dados["inicializado_em"] = inicio.isoformat()

    fabricante = (_ler("/sys/devices/virtual/dmi/id/sys_vendor") or "").strip()
    modelo = (_ler("/sys/devices/virtual/dmi/id/product_name") or "").strip()
    if fabricante or modelo:
        dados["hardware"] = " ".join(parte for parte in (fabricante, modelo) if parte)
    virt = _executar_status(["systemd-detect-virt"], timeout=3)
    if virt and virt != "none":
        dados["virtualizacao"] = virt
    elif virt == "none":
        dados["virtualizacao"] = "bare-metal"

    cgroup = (_ler("/proc/1/cgroup") or "") + (_ler("/proc/self/cgroup") or "")
    if os.path.exists("/.dockerenv"):
        dados["container"] = "docker"
    elif os.path.exists("/run/.containerenv"):
        dados["container"] = "podman"
    elif "kubepods" in cgroup:
        dados["container"] = "kubernetes"
    elif "docker" in cgroup or "containerd" in cgroup:
        dados["container"] = "container"

    fuso, _ = _executar(["timedatectl", "show", "-p", "Timezone", "--value"])
    dados["fuso_horario"] = fuso or (_ler("/etc/timezone") or "").strip() or None
    ntp, _ = _executar(["timedatectl", "show", "-p", "NTPSynchronized", "--value"])
    if ntp is not None:
        dados["ntp_sincronizado"] = ntp.lower() == "yes"
    return dados


def _ler_cpu_stat() -> tuple[int, int] | None:
    linha = _ler("/proc/stat")
    if not linha:
        return None
    primeira = linha.splitlines()[0].split()
    if not primeira or primeira[0] != "cpu":
        return None
    try:
        campos = [int(valor) for valor in primeira[1:]]
    except ValueError:
        return None
    if len(campos) < 4:
        return None
    ocioso = campos[3] + (campos[4] if len(campos) > 4 else 0)
    return sum(campos), ocioso


def _limite_cpu_cgroup() -> float | None:
    texto = _ler("/sys/fs/cgroup/cpu.max")
    if texto:
        partes = texto.split()
        if len(partes) >= 2 and partes[0] != "max":
            try:
                return round(int(partes[0]) / int(partes[1]), 2)
            except (ValueError, ZeroDivisionError):
                pass
    quota = _int(_ler("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"))
    periodo = _int(_ler("/sys/fs/cgroup/cpu/cpu.cfs_period_us"))
    if quota and periodo and quota > 0:
        return round(quota / periodo, 2)
    return None


def coletar_cpu(amostra: float) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "modelo": None,
        "threads": os.cpu_count(),
        "nucleos_fisicos": None,
        "carga_1_5_15": None,
        "uso_percentual": None,
        "limite_cgroup_cpus": _limite_cpu_cgroup(),
    }

    cpuinfo = _ler("/proc/cpuinfo")
    if cpuinfo:
        modelos: list[str] = []
        for linha in cpuinfo.splitlines():
            if linha.startswith("model name"):
                modelos.append(linha.split(":", 1)[1].strip())
        if modelos:
            dados["modelo"] = modelos[0]
        # Contagem física só é confiável quando physical id e core id existem.
        pares: set[tuple[str, str]] = set()
        fisico_atual = None
        for linha in cpuinfo.splitlines():
            if linha.startswith("physical id"):
                fisico_atual = linha.split(":", 1)[1].strip()
            elif linha.startswith("core id") and fisico_atual is not None:
                pares.add((fisico_atual, linha.split(":", 1)[1].strip()))
        if pares:
            dados["nucleos_fisicos"] = len(pares)

    try:
        dados["carga_1_5_15"] = [round(valor, 2) for valor in os.getloadavg()]
    except OSError:
        pass

    if amostra > 0:
        antes = _ler_cpu_stat()
        time.sleep(amostra)
        depois = _ler_cpu_stat()
        if antes and depois:
            total = depois[0] - antes[0]
            ocioso = depois[1] - antes[1]
            if total > 0:
                dados["uso_percentual"] = round(100 * (1 - ocioso / total), 1)
    return dados


def _limite_memoria_cgroup() -> tuple[int | None, int | None]:
    limite = _int(_ler("/sys/fs/cgroup/memory.max"))
    atual = _int(_ler("/sys/fs/cgroup/memory.current"))
    if limite is None:
        limite = _int(_ler("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
        atual = _int(_ler("/sys/fs/cgroup/memory/memory.usage_in_bytes"))
    # Valores próximos de 2^63 significam "sem limite".
    if limite is not None and limite >= 2**60:
        limite = None
    return limite, atual


def coletar_memoria() -> dict[str, Any]:
    dados: dict[str, Any] = {
        "total_bytes": None,
        "livre_bytes": None,
        "disponivel_bytes": None,
        "usada_percentual": None,
        "swap_total_bytes": None,
        "swap_livre_bytes": None,
        "limite_cgroup_bytes": None,
        "cgroup_atual_bytes": None,
    }

    texto = _ler("/proc/meminfo") or ""
    valores: dict[str, int] = {}
    for linha in texto.splitlines():
        if ":" not in linha:
            continue
        chave, resto = linha.split(":", 1)
        partes = resto.split()
        if partes:
            numero = _int(partes[0])
            if numero is not None:
                valores[chave.strip()] = numero * 1024

    dados["total_bytes"] = valores.get("MemTotal")
    dados["livre_bytes"] = valores.get("MemFree")
    disponivel = valores.get("MemAvailable")
    if disponivel is None:
        # Núcleos antigos não expõem MemAvailable.
        disponivel = (
            (valores.get("MemFree") or 0)
            + (valores.get("Buffers") or 0)
            + (valores.get("Cached") or 0)
        )
    dados["disponivel_bytes"] = disponivel
    if dados["total_bytes"]:
        dados["usada_percentual"] = round(
            100 * (1 - disponivel / dados["total_bytes"]), 1
        )
    dados["swap_total_bytes"] = valores.get("SwapTotal")
    dados["swap_livre_bytes"] = valores.get("SwapFree")

    limite, atual = _limite_memoria_cgroup()
    dados["limite_cgroup_bytes"] = limite
    dados["cgroup_atual_bytes"] = atual
    return dados


def _medir_disco(ponto: str) -> dict[str, Any] | None:
    try:
        uso = shutil.disk_usage(ponto)
        stat = os.statvfs(ponto)
        dispositivo = os.stat(ponto).st_dev
    except OSError:
        return None
    inodes_total = stat.f_files
    inodes_livres = stat.f_ffree
    return {
        "ponto": ponto,
        "dispositivo": dispositivo,
        "total_bytes": uso.total,
        "usado_bytes": uso.used,
        "livre_bytes": uso.free,
        "usado_percentual": round(100 * uso.used / uso.total, 1) if uso.total else None,
        "inodes_total": inodes_total,
        "inodes_livres": inodes_livres,
        "inodes_usado_percentual": (
            round(100 * (1 - inodes_livres / inodes_total), 1) if inodes_total else None
        ),
    }


def coletar_disco() -> dict[str, Any]:
    montagens: list[dict[str, Any]] = []
    vistos: set[int] = set()
    for ponto in ("/", "/var/lib/docker", "/var/lib/postgresql", "/opt", "/home"):
        if not os.path.isdir(ponto):
            continue
        medicao = _medir_disco(ponto)
        if not medicao or medicao["dispositivo"] in vistos:
            continue
        vistos.add(medicao["dispositivo"])
        montagens.append(medicao)

    raiz = next((item for item in montagens if item["ponto"] == "/"), None)
    return {
        "montagens": montagens,
        "livre_raiz_bytes": raiz["livre_bytes"] if raiz else None,
        "total_raiz_bytes": raiz["total_bytes"] if raiz else None,
        "usado_raiz_percentual": raiz["usado_percentual"] if raiz else None,
    }


def _versao(comando: list[str]) -> str | None:
    saida, _ = _executar(comando, timeout=5)
    if not saida:
        return None
    return saida.splitlines()[0].strip()


def _systemctl_ativo(servico: str) -> str | None:
    saida = _executar_status(["systemctl", "is-active", servico], timeout=3)
    return saida.lower() if saida else None


def coletar_docker() -> dict[str, Any]:
    dados: dict[str, Any] = {
        "instalado": False,
        "versao_cliente": None,
        "compose": None,
        "compose_v1": None,
        "daemon_acessivel": False,
        "info": {},
        "erro": None,
        "containers": [],
        "uso_disco": [],
        "usuario_no_grupo_docker": None,
        "grupos_do_usuario": None,
    }

    if not shutil.which("docker"):
        return dados
    dados["instalado"] = True
    dados["versao_cliente"] = _versao(["docker", "--version"])

    compose, _ = _executar(["docker", "compose", "version", "--short"], timeout=5)
    if not compose:
        compose, _ = _executar(["docker", "compose", "version"], timeout=5)
    dados["compose"] = compose.splitlines()[0] if compose else None

    compose_v1, _ = _executar(["docker-compose", "version", "--short"], timeout=5)
    if not compose_v1:
        compose_v1, _ = _executar(["docker-compose", "version"], timeout=5)
    dados["compose_v1"] = compose_v1.splitlines()[0] if compose_v1 else None

    grupos = _executar_status(["id", "-nG"])
    if grupos:
        dados["grupos_do_usuario"] = grupos.split()
        dados["usuario_no_grupo_docker"] = "docker" in grupos.split()

    saida, erro = _executar(["docker", "info", "--format", "{{json .}}"], timeout=15)
    if saida:
        try:
            bruto = json.loads(saida)
        except json.JSONDecodeError:
            bruto = None
        if isinstance(bruto, dict):
            chaves = (
                "ServerVersion",
                "Driver",
                "StorageDriver",
                "DockerRootDir",
                "CgroupVersion",
                "CgroupDriver",
                "NCPU",
                "MemTotal",
                "Containers",
                "ContainersRunning",
                "ContainersPaused",
                "ContainersStopped",
                "Images",
                "KernelVersion",
                "OperatingSystem",
                "Architecture",
                "Warnings",
            )
            dados["info"] = {chave: bruto.get(chave) for chave in chaves}
            dados["daemon_acessivel"] = True
        else:
            dados["erro"] = "saída de 'docker info' não é JSON"
    else:
        dados["erro"] = erro or "não foi possível consultar o daemon"

    if dados["daemon_acessivel"]:
        saida, _ = _executar(
            ["docker", "ps", "-a", "--format", "{{json .}}"], timeout=10
        )
        if saida:
            for linha in saida.splitlines():
                try:
                    item = json.loads(linha)
                except json.JSONDecodeError:
                    continue
                dados["containers"].append(
                    {
                        "nome": item.get("Names"),
                        "imagem": item.get("Image"),
                        "estado": item.get("State"),
                        "status": item.get("Status"),
                        "portas": item.get("Ports"),
                    }
                )

        saida, _ = _executar(
            ["docker", "system", "df", "--format", "{{json .}}"], timeout=20
        )
        if saida:
            for linha in saida.splitlines():
                try:
                    dados["uso_disco"].append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    return dados


def coletar_ferramentas() -> dict[str, Any]:
    nomes = (
        "bash",
        "make",
        "curl",
        "python3",
        "git",
        "openssl",
        "ss",
        "ip",
        "systemctl",
        "timedatectl",
        "nft",
        "iptables",
        "ufw",
        "firewall-cmd",
        "fail2ban-client",
    )
    dados: dict[str, Any] = {
        "caminhos": {nome: shutil.which(nome) for nome in nomes},
        "versoes": {},
    }
    for nome, comando in (
        ("python3", ["python3", "--version"]),
        ("make", ["make", "--version"]),
        ("curl", ["curl", "--version"]),
        ("git", ["git", "--version"]),
    ):
        if dados["caminhos"].get(nome):
            dados["versoes"][nome] = _versao(comando)
    return dados


def coletar_kernel() -> dict[str, Any]:
    arquivos = {
        "vm.max_map_count": "/proc/sys/vm/max_map_count",
        "vm.swappiness": "/proc/sys/vm/swappiness",
        "vm.overcommit_memory": "/proc/sys/vm/overcommit_memory",
        "fs.file-max": "/proc/sys/fs/file-max",
        "fs.inotify.max_user_watches": "/proc/sys/fs/inotify/max_user_watches",
        "net.core.somaxconn": "/proc/sys/net/core/somaxconn",
        "kernel.pid_max": "/proc/sys/kernel/pid_max",
    }
    dados: dict[str, Any] = {}
    for chave, caminho in arquivos.items():
        valor = _ler(caminho)
        if valor is not None:
            dados[chave] = valor.strip()

    thp = _ler("/sys/kernel/mm/transparent_hugepage/enabled")
    if thp:
        if "[" in thp and "]" in thp:
            dados["transparent_hugepage"] = thp.split("[", 1)[1].split("]", 1)[0]
        else:
            dados["transparent_hugepage"] = thp.strip()
    else:
        dados["transparent_hugepage"] = None

    try:
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        dados["nofile"] = {
            "soft": None if soft == resource.RLIM_INFINITY else soft,
            "hard": None if hard == resource.RLIM_INFINITY else hard,
        }
    except (OSError, ValueError):
        dados["nofile"] = None
    return dados


def _ler_portas_tcp() -> list[dict[str, Any]]:
    portas: list[dict[str, Any]] = []
    vistos: set[tuple[int, str, int]] = set()
    for caminho in ("/proc/net/tcp", "/proc/net/tcp6"):
        texto = _ler(caminho)
        if not texto:
            continue
        for linha in texto.splitlines()[1:]:
            campos = linha.split()
            if len(campos) < 8 or campos[3] != "0A":  # 0A = LISTEN
                continue
            endereco_hex, porta_hex = campos[1].split(":")
            porta = _int(porta_hex)
            uid = _int(campos[7])
            if porta is None or uid is None:
                continue
            endereco = _decodificar_endereco(endereco_hex)
            chave = (porta, endereco, uid)
            if chave in vistos:
                continue
            vistos.add(chave)
            try:
                usuario = pwd.getpwuid(uid).pw_name
            except KeyError:
                usuario = str(uid)
            portas.append(
                {
                    "porta": porta,
                    "endereco": endereco,
                    "uid": uid,
                    "usuario": usuario,
                }
            )
    portas.sort(key=lambda item: (item["porta"], item["endereco"]))
    return portas


def coletar_portas() -> dict[str, Any]:
    em_uso = _ler_portas_tcp()
    criticas = []
    for porta, servico in PORTAS_RODOU.items():
        donos = [item for item in em_uso if item["porta"] == porta]
        criticas.append(
            {
                "porta": porta,
                "servico": servico,
                "em_uso": bool(donos),
                "enderecos": sorted({item["endereco"] for item in donos}),
                "usuarios": sorted({item["usuario"] for item in donos}),
            }
        )
    return {"em_uso": em_uso, "criticas": criticas}


def _testar_conexao(nome: str, host: str, porta: int, timeout: float) -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "nome": nome,
        "host": host,
        "porta": porta,
        "dns_ok": False,
        "conectado": False,
        "latencia_ms": None,
        "erro": None,
        "enderecos": [],
    }
    inicio = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, porta, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        resultado["erro"] = f"DNS: {exc}"
        return resultado
    resultado["dns_ok"] = True
    resultado["enderecos"] = sorted({info[4][0] for info in infos})

    erro = None
    for familia, tipo, proto, _, endereco in infos:
        try:
            with socket.socket(familia, tipo, proto) as conector:
                conector.settimeout(timeout)
                conector.connect(endereco)
            resultado["conectado"] = True
            resultado["latencia_ms"] = round((time.perf_counter() - inicio) * 1000, 1)
            break
        except OSError as exc:
            erro = str(exc)
    if not resultado["conectado"]:
        resultado["erro"] = erro or "nenhum endereço respondeu"
    return resultado


def _interfaces_rede() -> list[dict[str, Any]] | None:
    if not shutil.which("ip"):
        return None
    saida, _ = _executar(["ip", "-j", "addr", "show"], timeout=5)
    if not saida:
        return None
    try:
        bruto = json.loads(saida)
    except json.JSONDecodeError:
        return None
    interfaces = []
    for item in bruto:
        enderecos = []
        for info in item.get("addr_info", []):
            enderecos.append(
                {
                    "familia": info.get("family"),
                    "endereco": info.get("local"),
                    "prefixo": info.get("prefixlen"),
                }
            )
        interfaces.append(
            {
                "nome": item.get("ifname"),
                "estado": item.get("operstate"),
                "mtu": item.get("mtu"),
                "mac": item.get("address"),
                "enderecos": enderecos,
            }
        )
    return interfaces


def _rota_padrao() -> dict[str, Any] | None:
    if not shutil.which("ip"):
        return None
    saida, _ = _executar(["ip", "-j", "route", "show", "default"], timeout=5)
    if not saida:
        return None
    try:
        rotas = json.loads(saida)
    except json.JSONDecodeError:
        return None
    if not rotas:
        return None
    rota = rotas[0]
    return {
        "gateway": rota.get("gateway"),
        "interface": rota.get("dev"),
        "metrica": rota.get("metric"),
    }


def _dns_configurado() -> list[str]:
    texto = _ler("/etc/resolv.conf") or ""
    servidores = []
    for linha in texto.splitlines():
        partes = linha.split()
        if len(partes) >= 2 and partes[0].lower() == "nameserver":
            servidores.append(partes[1])
    return servidores


def coletar_rede(timeout: float, testar: bool) -> dict[str, Any]:
    dados: dict[str, Any] = {
        "interfaces": _interfaces_rede(),
        "rota_padrao": _rota_padrao(),
        "dns": _dns_configurado(),
        "conectividade": None,
    }
    if not testar:
        return dados
    with ThreadPoolExecutor(max_workers=len(HOSTS_REDE)) as executor:
        futuros = [
            executor.submit(_testar_conexao, nome, host, porta, timeout)
            for nome, host, porta in HOSTS_REDE
        ]
        dados["conectividade"] = [futuro.result() for futuro in futuros]
    return dados


def _diretivas_ssh() -> dict[str, Any]:
    interessantes = {
        "permitrootlogin",
        "passwordauthentication",
        "pubkeyauthentication",
        "port",
    }
    dados: dict[str, Any] = {
        "arquivos_lidos": [],
        "diretivas": {},
        "efetivas": {},
        "observacao": (
            "Verificação básica: diretivas dentro de blocos Match não são "
            "avaliadas e a primeira ocorrência efetiva é usada."
        ),
    }
    visitados: set[str] = set()

    def processar(caminho: Path, profundidade: int = 0) -> None:
        if profundidade > 5:
            return
        try:
            chave_caminho = str(caminho.resolve())
        except OSError:
            chave_caminho = str(caminho)
        if chave_caminho in visitados:
            return
        visitados.add(chave_caminho)
        texto = _ler(str(caminho))
        if texto is None:
            return
        dados["arquivos_lidos"].append(str(caminho))
        for linha in texto.splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            partes = linha.split(None, 1)
            if len(partes) != 2:
                continue
            chave = partes[0].lower()
            valor = partes[1].strip()
            if chave == "include":
                for padrao in valor.split():
                    if not os.path.isabs(padrao):
                        padrao = str(caminho.parent / padrao)
                    for incluido in sorted(glob.glob(padrao)):
                        processar(Path(incluido), profundidade + 1)
                continue
            if chave not in interessantes:
                continue
            item = {"valor": valor, "arquivo": str(caminho)}
            dados["diretivas"].setdefault(chave, []).append(item)
            dados["efetivas"].setdefault(chave, item)

    processar(Path("/etc/ssh/sshd_config"))
    return dados


def _firewall() -> dict[str, Any]:
    dados: dict[str, Any] = {
        "ufw": None,
        "ufw_erro": None,
        "firewalld": _systemctl_ativo("firewalld"),
        "nftables": _systemctl_ativo("nftables"),
        "nft_regras": None,
        "iptables_regras": None,
        "ativo": None,
    }
    saida, erro = _executar(["ufw", "status"], timeout=5)
    if saida:
        dados["ufw"] = saida.splitlines()[0].replace("Status:", "").strip()
    else:
        dados["ufw_erro"] = erro

    ufw = (dados["ufw"] or "").lower()
    firewalld = (dados["firewalld"] or "").lower()
    nftables = (dados["nftables"] or "").lower()
    if ufw == "active" or firewalld == "active" or nftables == "active":
        dados["ativo"] = True
    elif ufw == "inactive" or firewalld == "inactive" and not shutil.which("ufw"):
        dados["ativo"] = False

    if shutil.which("nft"):
        saida, _ = _executar(["nft", "list", "ruleset"], timeout=5)
        if saida:
            dados["nft_regras"] = len(
                [linha for linha in saida.splitlines() if linha.strip()]
            )
    if shutil.which("iptables"):
        saida, _ = _executar(["iptables", "-S"], timeout=5)
        if saida:
            dados["iptables_regras"] = len(
                [linha for linha in saida.splitlines() if linha.strip()]
            )
    return dados


def coletar_seguranca() -> dict[str, Any]:
    return {
        "ssh": _diretivas_ssh(),
        "firewall": _firewall(),
        "fail2ban": _systemctl_ativo("fail2ban"),
        "reinicio_pendente": os.path.exists("/var/run/reboot-required")
        or os.path.exists("/run/reboot-required"),
    }


# ---------------------------------------------------------------- avaliação


def avaliar(dados: dict[str, Any], com_opensearch: bool = False) -> dict[str, Any]:
    bloqueadores: list[str] = []
    alertas: list[str] = []
    recomendacoes: list[str] = []

    host = dados.get("host") or {}
    cpu = dados.get("cpu") or {}
    memoria = dados.get("memoria") or {}
    disco = dados.get("disco") or {}
    docker = dados.get("docker") or {}
    ferramentas = dados.get("ferramentas") or {}
    kernel = dados.get("kernel") or {}
    portas = dados.get("portas") or {}
    rede = dados.get("rede") or {}
    seguranca = dados.get("seguranca") or {}

    # Recursos efetivos: considera limite de cgroup quando existir.
    ram_total = memoria.get("total_bytes") or 0
    limite_memoria = memoria.get("limite_cgroup_bytes")
    ram_efetiva = ram_total
    if limite_memoria and 0 < limite_memoria < ram_efetiva:
        ram_efetiva = limite_memoria

    threads = cpu.get("threads") or 0
    limite_cpu = cpu.get("limite_cgroup_cpus")
    cpus_efetivas = min(threads, limite_cpu) if limite_cpu else threads

    livre = disco.get("livre_raiz_bytes") or 0

    if ram_efetiva < MIN_RAM_BYTES:
        bloqueadores.append(
            f"Memória RAM efetiva de {_fmt_bytes(ram_efetiva)}; o mínimo "
            "documentado é 4 GB."
        )
    elif ram_efetiva < REC_RAM_BYTES:
        alertas.append(
            f"RAM de {_fmt_bytes(ram_efetiva)} atende ao mínimo, mas 8 GB "
            "são recomendados para produção."
        )

    if livre < MIN_DISCO_LIVRE_BYTES:
        bloqueadores.append(
            f"Apenas {_fmt_bytes(livre)} livres em /; o ambiente precisa de "
            f"espaço para imagens, banco e logs (mínimo prático "
            f"{_fmt_bytes(MIN_DISCO_LIVRE_BYTES)})."
        )
    elif livre < REC_DISCO_LIVRE_BYTES:
        alertas.append(
            f"Disco livre de {_fmt_bytes(livre)}; recomenda-se pelo menos "
            f"{_fmt_bytes(REC_DISCO_LIVRE_BYTES)} para imagens e volumes."
        )
    for montagem in disco.get("montagens") or []:
        if montagem.get("ponto") == "/":
            continue
        livre_montagem = montagem.get("livre_bytes") or 0
        if livre_montagem < MIN_DISCO_LIVRE_BYTES:
            alertas.append(
                f"Ponto {montagem.get('ponto')} com apenas "
                f"{_fmt_bytes(livre_montagem)} livres."
            )

    if cpus_efetivas and cpus_efetivas < MIN_CPUS:
        alertas.append(
            f"Apenas {cpus_efetivas:g} vCPU efetiva(s); 2 vCPU são "
            "recomendadas para Airflow, PostgreSQL e OpenSearch."
        )

    swap = memoria.get("swap_total_bytes") or 0
    if swap == 0 and ram_efetiva < REC_RAM_BYTES:
        alertas.append(
            "Sem swap configurado. Em VPS com menos de 8 GiB de RAM, "
            "2 GiB de swap reduzem o risco de oom-kill."
        )

    if not docker.get("instalado"):
        bloqueadores.append(
            "Docker não encontrado. O Ro-DOU é executado via containers."
        )
    else:
        if not docker.get("daemon_acessivel"):
            bloqueadores.append(
                "Daemon do Docker inacessível"
                + (f": {docker.get('erro')}" if docker.get("erro") else ".")
            )
        if not docker.get("compose") and not docker.get("compose_v1"):
            bloqueadores.append(
                "Docker Compose não encontrado (plugin 'docker compose' ou "
                "'docker-compose')."
            )
        elif not docker.get("compose"):
            alertas.append(
                "Apenas o Docker Compose v1 foi encontrado; ele está em fim "
                "de vida. Instale o plugin v2 ('docker compose')."
            )

    caminhos = ferramentas.get("caminhos") or {}
    for nome in ("bash", "make", "curl", "python3"):
        if not caminhos.get(nome):
            bloqueadores.append(
                f"'{nome}' não encontrado; o fluxo oficial 'make run' depende "
                "dessa ferramenta no host."
            )
    if not caminhos.get("git"):
        alertas.append("Git não encontrado; necessário para clonar o repositório.")

    familia = (host.get("familia") or "").lower()
    if familia and familia != "linux":
        alertas.append(
            f"Sistema '{host.get('sistema')}' não é Linux; o guia de VPS "
            "considera Linux."
        )
    arquitetura = host.get("arquitetura")
    if arquitetura and arquitetura not in ("x86_64", "amd64", "aarch64", "arm64"):
        alertas.append(
            f"Arquitetura '{arquitetura}' incomum; confirme a disponibilidade "
            "das imagens Docker."
        )

    fuso = host.get("fuso_horario")
    if fuso and fuso != "America/Sao_Paulo":
        recomendacoes.append(
            f"Host em {fuso}. O Airflow usa a variável "
            "AIRFLOW__CORE__DEFAULT_TIMEZONE; o docker-compose do projeto já "
            "define America/Sao_Paulo. Confirme a variável se usar outro deploy."
        )
    if host.get("ntp_sincronizado") is False:
        alertas.append(
            "Relógio não sincronizado (NTP). Agendamentos do Airflow podem "
            "disparar em horários inesperados."
        )
    if host.get("container"):
        alertas.append(
            f"Script executado dentro de container ({host['container']}); "
            "os dados refletem o container, não necessariamente a VPS. "
            "Execute-o diretamente no host."
        )

    max_map_count = _int(kernel.get("vm.max_map_count"))
    if com_opensearch:
        if max_map_count is not None and max_map_count < MAX_MAP_COUNT_OPENSEARCH:
            bloqueadores.append(
                f"vm.max_map_count={max_map_count}; o OpenSearch exige pelo "
                f"menos {MAX_MAP_COUNT_OPENSEARCH}."
            )
        if ram_efetiva < REC_RAM_BYTES:
            alertas.append(
                "OpenSearch habilitado: reserve mais 1-2 GiB de RAM além do "
                "Airflow e do PostgreSQL."
            )

    for item in portas.get("criticas") or []:
        if item.get("em_uso"):
            enderecos = ", ".join(item.get("enderecos") or [])
            alertas.append(
                f"Porta {item['porta']} ({item['servico']}) já está em uso "
                f"em {enderecos or 'endereço não identificado'}; o compose "
                "tentará publicá-la e pode falhar."
            )

    conectividade = rede.get("conectividade")
    if conectividade:
        por_nome = {item["nome"]: item for item in conectividade}
        for nome in sorted(HOSTS_INSTALACAO):
            item = por_nome.get(nome)
            if item and not item.get("conectado"):
                bloqueadores.append(
                    f"Sem acesso TCP a {nome} ({item['host']}:{item['porta']}"
                    f"): {item.get('erro')}. A instalação/build pode falhar."
                )
        fontes_ok = [
            por_nome[nome]
            for nome in HOSTS_FONTES
            if por_nome.get(nome, {}).get("conectado")
        ]
        for nome in sorted(HOSTS_FONTES):
            item = por_nome.get(nome)
            if item and not item.get("conectado"):
                alertas.append(
                    f"Fonte {nome} inacessível ({item.get('erro')}); as "
                    "buscas que a utilizam falharão."
                )
        if not fontes_ok:
            alertas.append(
                "Nenhuma fonte de diário oficial respondeu; verifique DNS, "
                "saída 443 e proxy."
            )

    ssh = (seguranca.get("ssh") or {}).get("efetivas") or {}
    for chave, rotulo in (
        ("permitrootlogin", "PermitRootLogin"),
        ("passwordauthentication", "PasswordAuthentication"),
    ):
        item = ssh.get(chave) or {}
        if str(item.get("valor", "")).lower() in ("yes", "true"):
            alertas.append(
                f"SSH com {rotulo}=yes. Em produção, prefira chave e acesso "
                "restrito."
            )

    firewall = seguranca.get("firewall") or {}
    if firewall.get("ativo") is False:
        alertas.append(
            "Nenhum firewall ativo detectado (ufw/firewalld). Restrinja "
            "8080, 5432, 9200 e as portas do smtp4dev."
        )
    elif firewall.get("ativo") is None:
        recomendacoes.append(
            "Não foi possível confirmar o firewall (o status do ufw exige "
            "root). Verifique com 'sudo ufw status verbose' ou "
            "'sudo nft list ruleset'."
        )
    if seguranca.get("fail2ban") not in ("active",):
        recomendacoes.append("Avalie fail2ban ou proteção equivalente para o SSH.")
    if seguranca.get("reinicio_pendente"):
        alertas.append("Há atualização de kernel/serviço pendente de reinício.")

    if (
        not com_opensearch
        and max_map_count is not None
        and max_map_count < MAX_MAP_COUNT_OPENSEARCH
    ):
        recomendacoes.append(
            "Se for habilitar o OpenSearch do INLABS, configure "
            f"vm.max_map_count={MAX_MAP_COUNT_OPENSEARCH} no host."
        )
    nofile = (kernel.get("nofile") or {}).get("soft")
    if com_opensearch and nofile is not None and nofile < 65536:
        recomendacoes.append(
            f"nofile soft={nofile}; o OpenSearch recomenda 65536 ou mais. "
            "Confirme o limite efetivo do daemon/containers."
        )
    if swap == 0 and ram_efetiva < REC_RAM_BYTES:
        recomendacoes.append(
            f"Sem swap em uma VPS com {_fmt_bytes(ram_efetiva)} de RAM. "
            "Considere 2 GiB de swap para absorver picos de build."
        )
    recomendacoes.append(
        "Dimensione a VPS com 2 vCPU, 4 GiB de RAM (ideal 8 GiB) e 20-40 "
        "GiB de SSD; o mínimo documentado (4 GiB/2 GiB) serve para testes."
    )
    recomendacoes.append(
        "Em produção, troque as credenciais padrão e não exponha as portas "
        "5432, 9200, 25 e 143 à internet."
    )

    if bloqueadores:
        veredito = "inviavel"
    elif alertas:
        veredito = "viavel_com_ressalvas"
    else:
        veredito = "viavel"

    return {
        "veredito": veredito,
        "bloqueadores": bloqueadores,
        "alertas": alertas,
        "recomendacoes": recomendacoes,
        "metricas": {
            "ram_efetiva_bytes": ram_efetiva,
            "ram_efetiva_gib": round(ram_efetiva / 1024**3, 2),
            "cpus_efetivas": cpus_efetivas,
            "disco_livre_bytes": livre,
            "disco_livre_gib": round(livre / 1024**3, 2),
            "total_bloqueadores": len(bloqueadores),
            "total_alertas": len(alertas),
        },
    }


# ------------------------------------------------------------------ relatório


def _renderizar_texto(dados: dict[str, Any]) -> str:
    host = dados.get("host") or {}
    cpu = dados.get("cpu") or {}
    memoria = dados.get("memoria") or {}
    disco = dados.get("disco") or {}
    docker = dados.get("docker") or {}
    ferramentas = dados.get("ferramentas") or {}
    kernel = dados.get("kernel") or {}
    portas = dados.get("portas") or {}
    rede = dados.get("rede") or {}
    seguranca = dados.get("seguranca") or {}
    avaliacao = dados.get("avaliacao") or {}

    linhas: list[str] = []
    linhas.append("=" * 62)
    linhas.append(" Relatório de viabilidade — Ro-DOU em VPS")
    linhas.append("=" * 62)
    linhas.append(
        f"Host: {host.get('hostname')} ({host.get('fqdn')})" f" | {host.get('sistema')}"
    )
    linhas.append(
        f"Coletado em: {dados.get('coletado_em')}"
        f" | duração: {dados.get('duracao_segundos')}s"
    )

    veredito = avaliacao.get("veredito")
    rotulos = {
        "viavel": ("VIÁVEL", COR_VERDE),
        "viavel_com_ressalvas": ("VIÁVEL COM RESSALVAS", COR_AMARELA),
        "inviavel": ("INVIÁVEL", COR_VERMELHA),
    }
    rotulo, cor = rotulos.get(veredito, (str(veredito), COR_CINZA))
    linhas.append(f"\nVeredito: {_pintar(rotulo, cor)}")
    metricas = avaliacao.get("metricas") or {}
    linhas.append(
        f"  Bloqueadores: {metricas.get('total_bloqueadores', 0)}"
        f" | Alertas: {metricas.get('total_alertas', 0)}"
    )

    for titulo, chave, marcador, cor_item in (
        ("BLOQUEADORES", "bloqueadores", "x", COR_VERMELHA),
        ("ALERTAS", "alertas", "!", COR_AMARELA),
    ):
        itens = avaliacao.get(chave) or []
        if itens:
            linhas.append(_titulo(titulo))
            for item in itens:
                linhas.append(f"  {_pintar(marcador, cor_item)} {item}")

    linhas.append(_titulo("RECURSOS"))
    threads = cpu.get("threads")
    fisicos = cpu.get("nucleos_fisicos")
    linhas.append(
        f"  CPU: {threads} thread(s)"
        + (f", {fisicos} núcleo(s) físico(s)" if fisicos else "")
        + (
            f" | uso {cpu['uso_percentual']}%"
            if cpu.get("uso_percentual") is not None
            else ""
        )
    )
    if cpu.get("modelo"):
        linhas.append(f"       {cpu['modelo']}")
    if cpu.get("limite_cgroup_cpus"):
        linhas.append(f"       limite de cgroup: {cpu['limite_cgroup_cpus']:g} CPU(s)")
    if cpu.get("carga_1_5_15"):
        carga = ", ".join(str(valor) for valor in cpu["carga_1_5_15"])
        linhas.append(f"       load average (1, 5, 15): {carga}")

    linhas.append(
        f"  RAM: {_fmt_bytes(memoria.get('total_bytes'))} total, "
        f"{_fmt_bytes(memoria.get('disponivel_bytes'))} disponível"
        + (
            f" | uso {memoria['usada_percentual']}%"
            if memoria.get("usada_percentual") is not None
            else ""
        )
    )
    if memoria.get("limite_cgroup_bytes"):
        linhas.append(
            f"       limite de cgroup: " f"{_fmt_bytes(memoria['limite_cgroup_bytes'])}"
        )
    linhas.append(
        f"  Swap: {_fmt_bytes(memoria.get('swap_total_bytes'))} total, "
        f"{_fmt_bytes(memoria.get('swap_livre_bytes'))} livre"
    )

    for montagem in disco.get("montagens") or []:
        linhas.append(
            f"  Disco {montagem['ponto']}: "
            f"{_fmt_bytes(montagem['livre_bytes'])} livres de "
            f"{_fmt_bytes(montagem['total_bytes'])}"
            f" ({montagem['usado_percentual']}% usado)"
        )
        if montagem.get("inodes_usado_percentual") is not None:
            linhas.append(
                f"       inodes: {montagem['inodes_usado_percentual']}% usados"
            )

    linhas.append(_titulo("SISTEMA"))
    linhas.append(f"  Kernel: {host.get('kernel')} | {host.get('arquitetura')}")
    linhas.append(
        f"  Virtualização: {host.get('virtualizacao') or 'n/d'}"
        f" | hardware: {host.get('hardware') or 'n/d'}"
        f" | container: {host.get('container') or 'não detectado'}"
    )
    linhas.append(
        f"  Uptime: {host.get('uptime_humano')}"
        f" | fuso: {host.get('fuso_horario')}"
        f" | NTP: {_fmt_bool(host.get('ntp_sincronizado'))}"
    )

    linhas.append(_titulo("DOCKER E FERRAMENTAS"))
    linhas.append(f"  Docker: {docker.get('versao_cliente') or 'não instalado'}")
    linhas.append(
        f"  Compose: {docker.get('compose') or docker.get('compose_v1') or 'n/d'}"
    )
    linhas.append(
        f"  Daemon acessível: {_status(docker.get('daemon_acessivel'))}"
        + (f" ({docker['erro']})" if docker.get("erro") else "")
    )
    if docker.get("info"):
        info = docker["info"]
        linhas.append(
            f"  Docker info: {info.get('ServerVersion')}"
            f" | storage: {info.get('Driver') or info.get('StorageDriver')}"
            f" | cgroup: {info.get('CgroupVersion')}"
        )
        linhas.append(
            f"  Containers: {info.get('Containers')} "
            f"({info.get('ContainersRunning')} em execução)"
            f" | imagens: {info.get('Images')}"
        )
        linhas.append(
            f"  Docker root: {info.get('DockerRootDir')}"
            f" | memória vista: {_fmt_bytes(info.get('MemTotal'))}"
        )
    if docker.get("containers"):
        linhas.append("  Containers existentes:")
        for container in docker["containers"]:
            linhas.append(
                f"    - {container.get('nome')}: {container.get('imagem')}"
                f" ({container.get('estado')})"
            )
    caminhos = ferramentas.get("caminhos") or {}
    ausentes = [nome for nome, caminho in caminhos.items() if not caminho]
    presentes = [nome for nome, caminho in caminhos.items() if caminho]
    linhas.append(f"  Presentes: {', '.join(presentes) or 'n/d'}")
    if ausentes:
        linhas.append(f"  Ausentes: {', '.join(ausentes)}")

    linhas.append(_titulo("REDE E PORTAS"))
    rota = rede.get("rota_padrao") or {}
    linhas.append(
        f"  Rota padrão: {rota.get('gateway') or 'n/d'}"
        f" via {rota.get('interface') or 'n/d'}"
    )
    linhas.append(f"  DNS: {', '.join(rede.get('dns') or []) or 'n/d'}")
    for interface in rede.get("interfaces") or []:
        enderecos = ", ".join(
            f"{item.get('endereco')}/{item.get('prefixo')}"
            for item in interface.get("enderecos") or []
        )
        linhas.append(
            f"  Interface {interface.get('nome')}: {interface.get('estado')}"
            f" | {enderecos or 'sem endereço'}"
        )
    for item in portas.get("criticas") or []:
        estado = "em uso" if item.get("em_uso") else "livre"
        donos = ""
        if item.get("em_uso"):
            donos = (
                f" ({', '.join(item.get('usuarios') or [])}; "
                f"{', '.join(item.get('enderecos') or [])})"
            )
        linhas.append(f"  Porta {item['porta']} [{item['servico']}]: {estado}{donos}")

    conectividade = rede.get("conectividade")
    if conectividade is not None:
        linhas.append("  Conectividade (TCP):")
        for item in conectividade:
            detalhe = (
                f"{item['latencia_ms']} ms"
                if item.get("conectado")
                else item.get("erro") or "falhou"
            )
            linhas.append(
                f"    {_status(item.get('conectado'))} {item['nome']} "
                f"({item['host']}:{item['porta']}): {detalhe}"
            )

    linhas.append(_titulo("KERNEL E LIMITES"))
    for chave in (
        "vm.max_map_count",
        "vm.swappiness",
        "vm.overcommit_memory",
        "fs.file-max",
        "fs.inotify.max_user_watches",
        "net.core.somaxconn",
        "kernel.pid_max",
        "transparent_hugepage",
    ):
        if chave in kernel:
            linhas.append(f"  {chave}: {kernel[chave]}")
    if kernel.get("nofile"):
        linhas.append(
            f"  nofile: soft={kernel['nofile'].get('soft')}"
            f" hard={kernel['nofile'].get('hard')}"
        )

    linhas.append(_titulo("SEGURANÇA (VERIFICAÇÃO BÁSICA)"))
    firewall = seguranca.get("firewall") or {}
    linhas.append(
        f"  Firewall: ufw={firewall.get('ufw') or 'n/d'}"
        f" | firewalld={firewall.get('firewalld') or 'n/d'}"
        f" | nftables={firewall.get('nftables') or 'n/d'}"
        f" | ativo={_fmt_bool(firewall.get('ativo'))}"
    )
    if firewall.get("ufw_erro"):
        linhas.append(f"       ufw: {firewall['ufw_erro']}")
    linhas.append(f"  fail2ban: {seguranca.get('fail2ban') or 'n/d'}")
    ssh = (seguranca.get("ssh") or {}).get("efetivas") or {}
    for chave in ("permitrootlogin", "passwordauthentication"):
        item = ssh.get(chave) or {}
        if item:
            linhas.append(
                f"  SSH {chave}: {item['valor']}" f" ({Path(item['arquivo']).name})"
            )
    linhas.append(
        f"  Reinício pendente: {_fmt_bool(seguranca.get('reinicio_pendente'))}"
    )

    recomendacoes = avaliacao.get("recomendacoes") or []
    if recomendacoes:
        linhas.append(_titulo("RECOMENDAÇÕES"))
        for item in recomendacoes:
            linhas.append(f"  - {item}")

    linhas.append("")
    return "\n".join(linhas)


# ----------------------------------------------------------------------- CLI


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Coleta dados da VPS e avalia a viabilidade de executar o Ro-DOU. "
            "O script é somente leitura."
        ),
        epilog=(
            "Algumas verificações (firewall, SSH e limites) podem exigir root; "
            "sem privilégio elas aparecem como n/d."
        ),
    )
    parser.add_argument(
        "--formato",
        choices=("texto", "json"),
        default="texto",
        help="formato da saída (padrão: texto)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="atalho para --formato json",
    )
    parser.add_argument(
        "--saida",
        metavar="ARQUIVO",
        help="grava o relatório no arquivo informado (permissão 600)",
    )
    parser.add_argument(
        "--sem-rede",
        action="store_true",
        help="não executa os testes TCP de conectividade",
    )
    parser.add_argument(
        "--com-opensearch",
        action="store_true",
        help="considera o OpenSearch como parte da instalação",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="timeout em segundos de cada teste TCP (padrão: 4)",
    )
    parser.add_argument(
        "--amostra",
        type=float,
        default=1.0,
        help="janela em segundos para medir uso de CPU (padrão: 1)",
    )
    parser.add_argument(
        "--sem-cor",
        action="store_true",
        help="desativa cores na saída em texto",
    )
    parser.add_argument(
        "--falhar-em-bloqueador",
        action="store_true",
        help="retorna código 2 se houver bloqueadores",
    )
    return parser.parse_args()


def main() -> int:
    global USAR_COR
    args = _argumentos()
    if args.sem_cor or not sys.stdout.isatty() or args.saida:
        USAR_COR = False
    if args.json:
        args.formato = "json"
    args.amostra = max(args.amostra, 0)
    args.timeout = max(args.timeout, 0.1)

    inicio = time.perf_counter()
    dados: dict[str, Any] = {
        "schema": VERSAO_SCHEMA,
        "coletado_em": dt.datetime.now().astimezone().isoformat(),
    }
    dados["host"] = coletar_host()
    dados["cpu"] = coletar_cpu(args.amostra)
    dados["memoria"] = coletar_memoria()
    dados["disco"] = coletar_disco()
    dados["docker"] = coletar_docker()
    dados["ferramentas"] = coletar_ferramentas()
    dados["kernel"] = coletar_kernel()
    dados["portas"] = coletar_portas()
    dados["rede"] = coletar_rede(args.timeout, not args.sem_rede)
    dados["seguranca"] = coletar_seguranca()
    dados["avaliacao"] = avaliar(dados, com_opensearch=args.com_opensearch)
    dados["duracao_segundos"] = round(time.perf_counter() - inicio, 2)

    if args.formato == "json":
        conteudo = json.dumps(dados, indent=2, ensure_ascii=False, default=str)
    else:
        conteudo = _renderizar_texto(dados)

    if args.saida:
        destino = Path(args.saida)
        try:
            destino.write_text(conteudo + "\n", encoding="utf-8")
            os.chmod(destino, 0o600)
        except OSError as exc:
            print(f"Erro ao gravar {destino}: {exc}", file=sys.stderr)
            return 1
        print(f"Relatório gravado em {destino} (permissão 600).", file=sys.stderr)
    else:
        print(conteudo)

    bloqueadores = dados["avaliacao"]["bloqueadores"]
    if args.falhar_em_bloqueador and bloqueadores:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
