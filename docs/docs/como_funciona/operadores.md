# Operadores de Pesquisa Avançada

Os seguintes operadores de pesquisa avançada no Ro-DOU podem ser utilizados nas consultas configuradas nos arquivos YAML:

| Operador | Significado | Exemplo |
|-----------|-------------|----------|
| `AND` | Ambos os termos devem existir | `apple AND banana` |
| `OR` | Pelo menos um dos termos pode existir | `apple OR banana` |
| `NOT` | Exclui um termo da busca | `apple NOT banana` |
| `+` | Define um termo obrigatório | `+apple banana` |
| `-` | Exclui um termo da busca | `apple -banana` |
| `&&` | Equivalente ao operador `AND` | `apple && banana` |
| `!` | Equivalente ao operador `NOT` | `apple !banana` |

Também é possível combinar expressões utilizando parênteses:

```text
(ministério OR MGI) AND designar
```

Ou:

```text
(instituto AND federal) NOT paraná
```

Além disso, o operador de aspas duplas (`"`) pode ser utilizado para buscar expressões exatas:

```text
"instituto federal"
```

O exemplo abaixo demonstra, na prática, como esses operadores podem ser utilizados no Ro-DOU:

```yaml
dag:
  id: inlabs_advanced_search_example
  description: DAG de teste
  tags:
    - inlabs
  schedule: 0 8 * * MON-FRI
  owner:
    - cdata

  search:
    sources:
      - INLABS

    terms:
      - '(ministério OR MGI) AND designar'
      - '(instituto AND federal) NOT paraná'
      - '+servidor aposentadoria'
      - 'educação -temporário'
      - '"instituto federal"'

  report:
    emails:
      - destination@economia.gov.br

    attach_csv: true
    subject: "Teste do Ro-DOU"
```