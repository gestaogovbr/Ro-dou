import re
import unidecode


def singularize(original_text: str) -> str:
    list_str = []
    # Remove acentos e deixa tudo minuscula
    for word in original_text.split():
        word_to_takeoff_plural = unidecode.unidecode(word.strip()).lower()

        # Palavras que não variam e são terminadas em 's'
        INVARIABLE = [
            "parabens",
            "lapis",
            "virus",
            "atlas",
            "pires",
            "bonus",
            "cais",
            "oculos",
            "onibus",
            "varios",
            "varias",
        ]

        # Percorre a lista de palavras que não variam
        # verificando se a palavra buscada está contida nela, se sim retorna a palavra .
        if word_to_takeoff_plural in INVARIABLE:
            list_str.append(word_to_takeoff_plural)
            continue

        # Palavras terminadas em 'ns'
        if re.match(r"^([a-zA-z]*)ns$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)ns$", r"\1m", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'zes'
        elif re.match(r"^([a-zA-z]*)zes$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)zes$", r"\1z", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'ses'
        elif re.match(r"^([a-zA-z]*)ses$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)ses$", r"\1s", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'oes'
        elif re.match(r"^([a-zA-z]*)oes$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)oes$", r"\1ao", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'aos'
        elif re.match(r"^([a-zA-z]*)aos$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)aos$", r"\1ao", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'aes'
        elif re.match(r"^([a-zA-z]*)aes$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)aes$", r"\1ao", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'les'
        elif re.match(r"^([a-zA-z]*)les$", word_to_takeoff_plural) is not None:
            word_without_plural = re.sub(
                r"^([a-zA-z]*)les$", r"\1l", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'is' e anterior ao final 'is' uma vogal
        elif re.match(r"^([a-zA-z]*)(a|e|o|u)is$", word_to_takeoff_plural) is not None:

            word_without_plural = re.sub(
                r"^([a-zA-z]*)(a|e|o|u)is$", r"\1\2l", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Outros casos terminados em 'is' e anterior ao final 'is' uma consoante.
        elif re.match(r"^([a-zA-z]*)is$", word_to_takeoff_plural):
            word_without_plural = re.sub(
                r"^([a-zA-z]*)is$", r"\1il", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'mos'
        elif re.match(r"^([a-zA-z]*)mos$", word_to_takeoff_plural):
            word_without_plural = re.sub(
                r"^([a-zA-z]*)mos$", r"\1", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 's' e precedidas de uma vogal
        elif re.match(r"^([a-zA-z]*)(a|i|o|u)s$", word_to_takeoff_plural):
            word_without_plural = re.sub(
                r"^([a-zA-z]*)(a|i|o|u)s$", r"\1\2", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'res' e com inflexão de volta ao 'r'
        # Ex: flores - flor, investidores - investidor
        elif re.match(r"^([a-zA-z]*)(to|lo|do)res$", word_to_takeoff_plural):
            # print(word_to_takeoff_plural)
            word_without_plural = re.sub(
                r"^([a-zA-z]*)(to|lo|do)res$", r"\1\2r", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'res' e com inflexão de volta ao 're'
        # Ex: arvores - arvore
        elif re.match(r"^([a-zA-z]*)(vo)res$", word_to_takeoff_plural):
            # print(word_to_takeoff_plural)
            word_without_plural = re.sub(
                r"^([a-zA-z]*)(vo)res$", r"\1\2re", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        # Palavras terminadas em 'tes' e com inflexão de volta ao final 'te'
        elif re.match(r"^([a-zA-z]*)tes$", word_to_takeoff_plural):
            word_without_plural = re.sub(
                r"^([a-zA-z]*)tes$", r"\1te", word_to_takeoff_plural
            )
            list_str.append(word_without_plural)

        else:
            list_str.append(word_to_takeoff_plural)
    return " ".join(list_str)
