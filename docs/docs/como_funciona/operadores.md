# Operadores de Pesquisa Avançada

Os seguintes operadores de pesquisa avançada no Ro-DOU podem ser configurados nos arquivos YAML:

- **&** : Equivalente ao operador lógico **and** (conjunção "e").
- **|** : Equivalente ao operador lógico **or** (conjunção "ou").
- **!** : Equivalente ao operador lógico **not** (negação).

O exemplo abaixo demonstra, na prática, como tais operadores podem ser utilizados no Ro-DOU:

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
    - designar & ( MGI | MINISTÉRIO FAZENDA)
    - instituto & federal ! paraná
  report:
    emails:
      - destination@economia.gov.br
    attach_csv: True
    subject: "Teste do Ro-dou"
```