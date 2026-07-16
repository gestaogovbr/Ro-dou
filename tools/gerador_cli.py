"""CLI (POC) para gerar arquivos de configuração YAML do Ro-dou.

Dois modos de uso:

- interativo (padrão, sem flags de configuração): perguntas passo a passo;
- por flags: geração direta, sem perguntas — ex.:
  ``gerador_cli.py --id minha_busca --description "..." --terms "dados abertos"
  --emails pessoa@gov.br --stdout``

Este script não reimplementa nenhuma regra de negócio: toda a validação é
delegada ao `RoDouConfig` (Pydantic) definido em `src/schemas.py`, a mesma
classe usada pelo `YAMLParser` para carregar as DAGs. O que o schema não
valida, o CLI também não valida.

Como o `schemas.py` importa `airflow.models.Variable` (via `ai/provider.py`),
este script precisa rodar num ambiente com o Airflow instalado — na prática,
dentro do container `airflow-webserver` (veja `make gerador-cli`).
"""
import argparse
import os
import re
import sys

import yaml
from pydantic import ValidationError

SRC_PATH = os.environ.get("RO_DOU_SRC_PATH", "/opt/airflow/dags/ro_dou_src")
sys.path.insert(0, SRC_PATH)
from schemas import RoDouConfig  # noqa: E402

DAG_CONFS_DIR = os.environ.get(
    "RO_DOU__DAG_CONF_DIR", "/opt/airflow/dags/ro_dou/dag_confs"
)

VERDE, AZUL, VERM, CINZA, RESET = (
    "\033[32m", "\033[36m", "\033[31m", "\033[90m", "\033[0m"
)

FONTES = {"dou": "DOU", "inlabs": "INLABS", "qd": "QD"}


# ---------------------------------------------------------------- interação

def titulo(texto: str) -> None:
    """Imprime um cabeçalho de seção colorido."""
    print(f"\n{AZUL}── {texto} ──{RESET}")


def perguntar(
    mensagem: str, dica: str | None = None, obrigatorio: bool = False
) -> str | None:
    """Faz uma pergunta de texto livre; insiste se obrigatória e vazia."""
    if dica:
        print(f"{CINZA}{dica}{RESET}")
    marca = f"{VERM}*{RESET}" if obrigatorio else " "
    while True:
        valor = input(f"{marca} {mensagem}: ").strip()
        if valor:
            return valor
        if not obrigatorio:
            return None
        print(f"{VERM}  ! Este campo é obrigatório.{RESET}")


def perguntar_lista(
    mensagem: str, dica: str | None = None, obrigatorio: bool = False
) -> list[str] | None:
    """Pergunta uma lista de valores separados por vírgula."""
    valor = perguntar(f"{mensagem} (separe por vírgula)", dica, obrigatorio)
    if not valor:
        return None
    return [item.strip() for item in valor.split(",") if item.strip()]


def perguntar_sim_nao(mensagem: str, default: bool = True) -> bool:
    """Pergunta sim/não; Enter usa o default."""
    dica = "S/n" if default else "s/N"
    while True:
        valor = input(f"  {mensagem} ({dica}): ").strip().lower()
        if not valor:
            return default
        if valor in ("s", "sim"):
            return True
        if valor in ("n", "nao", "não"):
            return False
        print(f"{VERM}  ! Responda com 's' ou 'n'.{RESET}")


# ------------------------------------------------------- coleta interativa

def coletar_id() -> str:
    """Pergunta o id da DAG (obrigatório)."""
    return perguntar(
        "ID da DAG",
        dica="ex.: monitoramento_dados_abertos (único, sem espaços)",
        obrigatorio=True,
    )


def coletar_description() -> str:
    """Pergunta a descrição da DAG (obrigatória)."""
    return perguntar(
        "Descrição da DAG",
        dica="ex.: Monitora publicações sobre dados abertos no DOU",
        obrigatorio=True,
    )


def coletar_schedule() -> str | None:
    """Pergunta o agendamento cron (opcional)."""
    return perguntar(
        "Agendamento cron",
        dica="ex.: 0 8 * * MON-FRI — Enter usa o padrão do Ro-dou",
    )


def coletar_owner() -> list[str] | None:
    """Pergunta os owners da DAG (opcional)."""
    return perguntar_lista("Owners/responsáveis pela DAG", dica="ex.: cginf")


CAMPOS_SIMPLES = {
    "id": coletar_id,
    "description": coletar_description,
    "schedule": coletar_schedule,
    "owner": coletar_owner,
}


def coletar_search() -> dict:
    """Pergunta o bloco `search`: fontes, termos e territory_id (se QD)."""
    titulo("Busca")
    search = {}
    sources = perguntar_lista("Fontes (DOU, INLABS, QD)", dica="Enter usa DOU")
    if sources:
        search["sources"] = [fonte.upper() for fonte in sources]
    terms = perguntar_lista(
        "Termos de pesquisa", dica="ex.: dados abertos, governo aberto"
    )
    if terms:
        search["terms"] = terms
    if "QD" in search.get("sources", []):
        territory_id = perguntar(
            "ID do município no Querido Diário (territory_id)",
            dica="ex.: 4106902 (código IBGE)",
        )
        if territory_id:
            search["territory_id"] = territory_id
    return search


def coletar_report() -> dict:
    """Pergunta o bloco `report`: e-mails de destino."""
    titulo("Relatório")
    report = {}
    emails = perguntar_lista(
        "E-mails de destino do relatório", dica="ex.: pessoa@economia.gov.br"
    )
    if emails:
        report["emails"] = emails
    return report


# ------------------------------------------------------------- validação

def formatar_erros(exc: ValidationError) -> str:
    """Converte um ValidationError do Pydantic em lista legível de erros."""
    erros = exc.errors()
    # Quando um validator do schema levanta ValueError, o Pydantic também
    # reporta erros de tipo dos outros ramos da união; mostra só as regras.
    erros_de_regra = [erro for erro in erros if erro["type"] == "value_error"]
    if erros_de_regra:
        erros = erros_de_regra
    linhas = []
    for erro in erros:
        campo = ".".join(
            str(parte) for parte in erro["loc"]
            if not str(parte).startswith("function-after")
        )
        linhas.append(f"  - {campo}: {erro['msg']}" if campo else f"  - {erro['msg']}")
    return "\n".join(linhas)


def campo_do_erro(erro: dict) -> str:
    """Extrai o campo de primeiro nível ('id', 'search', ...) de um erro
    do Pydantic, para reperguntar somente o que falhou."""
    loc = [
        str(parte) for parte in erro["loc"]
        if not str(parte).startswith("function-after")
    ]
    if loc and loc[0] == "dag":
        loc = loc[1:]
    if loc and loc[0] in (*CAMPOS_SIMPLES, "report"):
        return loc[0]
    return "search"


# ----------------------------------------------------------- serialização

def sem_sets(valor):
    """Converte sets em listas ordenadas para permitir a serialização YAML."""
    if isinstance(valor, set):
        return sorted(sem_sets(item) for item in valor)
    if isinstance(valor, dict):
        return {chave: sem_sets(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [sem_sets(item) for item in valor]
    return valor


class DumperIndentado(yaml.SafeDumper):
    """Indenta itens de lista sob a chave, como nos exemplos de dag_confs/."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def gerar_yaml(config: RoDouConfig) -> str:
    """Serializa a configuração validada em YAML enxuto."""
    # Só o que o usuário informou entra no YAML; os defaults ficam a cargo
    # do Ro-dou na hora de carregar a DAG.
    dag_enxuto = config.dag.model_dump(exclude_defaults=True, exclude_none=True)
    # O schema normaliza `search` para lista, mas com uma busca só os
    # exemplos de dag_confs/ usam mapeamento direto.
    search = dag_enxuto.get("search")
    if isinstance(search, list) and len(search) == 1:
        dag_enxuto["search"] = search[0]
    return yaml.dump(
        {"dag": sem_sets(dag_enxuto)},
        Dumper=DumperIndentado,
        allow_unicode=True,
        sort_keys=False,
    )


RE_CHAVE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):( .*|)$")
RE_ITEM = re.compile(r"^\s*- ")


def colorir_yaml(texto: str) -> str:
    """Aplica cores ANSI ao YAML para exibição no terminal."""
    linhas = []
    for linha in texto.splitlines():
        chave = RE_CHAVE.match(linha)
        if chave:
            indent, nome, valor = chave.groups()
            linhas.append(f"{indent}{AZUL}{nome}{RESET}:{VERDE}{valor}{RESET}")
        elif RE_ITEM.match(linha):
            linhas.append(f"{VERDE}{linha}{RESET}")
        else:
            linhas.append(linha)
    return "\n".join(linhas)


# ------------------------------------------------------------------ saída

def salvar_arquivo(
    id_dag: str, yaml_texto: str, args: argparse.Namespace, interativo: bool
) -> int:
    """Grava o YAML em disco, protegendo contra sobrescrita acidental."""
    caminho = args.output or os.path.join(DAG_CONFS_DIR, f"{id_dag}.yaml")
    if os.path.exists(caminho) and not args.force:
        if not interativo:
            print(
                f"{VERM}Arquivo {caminho} já existe — use --force para "
                f"sobrescrever.{RESET}",
                file=sys.stderr,
            )
            return 1
        if not perguntar_sim_nao(
            f"Arquivo {caminho} já existe. Sobrescrever?", default=False
        ):
            print("Operação cancelada, arquivo não foi salvo.")
            return 0
    try:
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(yaml_texto)
    except OSError as exc:
        print(
            f"{VERM}Não foi possível salvar em {caminho} ({exc.strerror}). "
            f"Verifique as permissões do diretório ou use --stdout.{RESET}",
            file=sys.stderr,
        )
        return 1
    print(f"{VERDE}Arquivo salvo em {caminho}{RESET}")
    return 0


# ------------------------------------------------------------------ modos

def modo_interativo(args: argparse.Namespace) -> int:
    """Coleta os campos por perguntas, valida e repergunta só o que falhou."""
    print(f"{AZUL}Gerador de YAML do Ro-dou{RESET}")
    print(
        f"{CINZA}Responda às perguntas abaixo; campos marcados com "
        f"{VERM}*{CINZA} são obrigatórios,\nos demais podem ser pulados "
        f"com Enter.{RESET}"
    )

    titulo("DAG")
    dag_dict = {}
    for campo, coletor in CAMPOS_SIMPLES.items():
        valor = coletor()
        if valor is not None:
            dag_dict[campo] = valor
    dag_dict["search"] = coletar_search()
    dag_dict["report"] = coletar_report()

    while True:
        try:
            config = RoDouConfig(dag=dag_dict)
            break
        except ValidationError as exc:
            print(f"\n{VERM}A configuração informada é inválida:{RESET}")
            print(f"{VERM}{formatar_erros(exc)}{RESET}")
            print(f"{CINZA}Vamos corrigir apenas os campos com problema.{RESET}")
            campos = dict.fromkeys(campo_do_erro(erro) for erro in exc.errors())
            for campo in campos:
                if campo in CAMPOS_SIMPLES:
                    valor = CAMPOS_SIMPLES[campo]()
                    if valor is None:
                        # Enter em campo opcional descarta o valor que falhou.
                        dag_dict.pop(campo, None)
                    else:
                        dag_dict[campo] = valor
                elif campo == "report":
                    dag_dict["report"] = coletar_report()
                else:
                    dag_dict["search"] = coletar_search()

    yaml_texto = gerar_yaml(config)
    titulo("YAML gerado")
    print(colorir_yaml(yaml_texto))
    if args.stdout:
        return 0
    if not perguntar_sim_nao("Salvar este arquivo?"):
        print("Arquivo não foi salvo.")
        return 0
    return salvar_arquivo(config.dag.id, yaml_texto, args, interativo=True)


def montar_dag_dict(args: argparse.Namespace) -> dict:
    """Traduz as flags do argparse para o dict esperado pelo schema."""
    search = {}
    if args.sources:
        search["sources"] = [FONTES[fonte] for fonte in args.sources]
    if args.terms:
        search["terms"] = args.terms
    if args.territory_id is not None:
        search["territory_id"] = args.territory_id
    report = {}
    if args.emails:
        report["emails"] = args.emails
    dag_dict = {"search": search, "report": report}
    for campo in ("id", "description", "schedule"):
        valor = getattr(args, campo)
        if valor is not None:
            dag_dict[campo] = valor
    if args.owner:
        dag_dict["owner"] = args.owner
    return dag_dict


def modo_direto(args: argparse.Namespace) -> int:
    """Gera o YAML a partir das flags, sem perguntas; erro vira exit 1."""
    try:
        config = RoDouConfig(dag=montar_dag_dict(args))
    except ValidationError as exc:
        print(f"{VERM}Configuração inválida:{RESET}", file=sys.stderr)
        print(f"{VERM}{formatar_erros(exc)}{RESET}", file=sys.stderr)
        return 1
    yaml_texto = gerar_yaml(config)
    if args.stdout:
        print(yaml_texto, end="")
        return 0
    return salvar_arquivo(config.dag.id, yaml_texto, args, interativo=False)


# ------------------------------------------------------------------- main

# Flags de conteúdo: a presença de qualquer uma delas ativa o modo direto.
# --output/--stdout/--force ficam de fora porque valem nos dois modos.
FLAGS_CONFIG = (
    "id", "description", "schedule", "owner",
    "terms", "sources", "territory_id", "emails",
)


def montar_parser() -> argparse.ArgumentParser:
    """Define as flags aceitas pela linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gera arquivos YAML de configuração de DAGs do Ro-dou. "
        "Sem flags de configuração, roda em modo interativo.",
        epilog="exemplo: %(prog)s --id minha_busca --description 'Minha busca' "
        "--terms 'dados abertos' --emails pessoa@gov.br --stdout",
    )
    parser.add_argument("--id", help="nome único da DAG")
    parser.add_argument("--description", help="descrição da DAG")
    parser.add_argument("--schedule", help="expressão cron do agendamento")
    parser.add_argument(
        "--owner", action="append", metavar="NOME",
        help="responsável pela DAG (repetível)",
    )
    parser.add_argument(
        "--terms", action="append", metavar="TERMO",
        help="termo de pesquisa (repetível)",
    )
    parser.add_argument(
        "--sources", action="append", choices=sorted(FONTES),
        help="fonte de dados (repetível; padrão: dou)",
    )
    parser.add_argument(
        "--territory-id", type=int, metavar="ID",
        help="ID do município no Querido Diário",
    )
    parser.add_argument(
        "--emails", action="append", metavar="EMAIL",
        help="e-mail de destino do relatório (repetível)",
    )
    parser.add_argument(
        "--output", metavar="ARQUIVO",
        help=f"arquivo de saída (padrão: {DAG_CONFS_DIR}/<id>.yaml)",
    )
    parser.add_argument(
        "--stdout", action="store_true",
        help="imprime o YAML em vez de salvar em arquivo",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="sobrescreve o arquivo de saída sem perguntar",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Escolhe o modo: flags de conteúdo presentes → direto; senão interativo."""
    args = montar_parser().parse_args(argv)
    modo_flags = any(
        getattr(args, campo) is not None for campo in FLAGS_CONFIG
    )
    if modo_flags:
        return modo_direto(args)
    return modo_interativo(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.")
        sys.exit(130)
