"""Testes dos filtros de sanitização usados nos templates de e-mail."""

import pytest

from dags.ro_dou_src.notification.templateManager import safe_url, sanitize_html


class TestSanitizeHtml:
    @pytest.mark.parametrize("value", [None, ""])
    def test_empty_value(self, value):
        assert sanitize_html(value) == ""

    def test_removes_link_but_keeps_text(self):
        result = sanitize_html('<a href="https://evil.example">clique aqui</a>')

        assert "<a" not in result
        assert "evil.example" not in result
        assert "clique aqui" in result

    def test_removes_remote_image(self):
        result = sanitize_html('texto <img src="https://tracker.example/x.png">')

        assert "<img" not in result
        assert "tracker.example" not in result
        assert "texto" in result

    def test_removes_script_and_style_content(self):
        result = sanitize_html("<script>alert(1)</script><style>p{}</style>ok")

        assert result == "ok"

    def test_keeps_highlight_span(self):
        result = sanitize_html("<span class='highlight'>termo</span>")

        assert result == '<span class="highlight">termo</span>'

    def test_removes_other_span_attributes(self):
        result = sanitize_html(
            '<span class="phishing" style="display:none" onclick="x()">termo</span>'
        )

        assert result == "<span>termo</span>"

    def test_keeps_basic_formatting(self):
        value = "<p>linha 1<br>linha <strong>2</strong> <em>3</em></p>"

        assert sanitize_html(value) == value


class TestSafeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.in.gov.br/web/dou/-/extrato-342504508",
            "http://pesquisa.in.gov.br/imprensa/jsp/visualiza/index.jsp",
            "https://querido-diario.nyc3.cdn.digitaloceanspaces.com/4106902/x",
        ],
    )
    def test_accepts_http_urls(self, url):
        assert safe_url(url) == url

    @pytest.mark.parametrize(
        "url",
        [
            None,
            "",
            "javascript:alert(1)",
            " JavaScript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "mailto:alguem@example.com",
            "//evil.example/path",
            "/web/dou/-/relativo",
            "https://",
            "http://[invalid",
        ],
    )
    def test_rejects_non_http_urls(self, url):
        assert safe_url(url) == ""
