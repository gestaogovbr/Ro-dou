CREATE DATABASE inlabs;

\c inlabs

CREATE SCHEMA IF NOT EXISTS dou_inlabs;

CREATE TABLE IF NOT EXISTS dou_inlabs.article_raw (
    id BIGINT PRIMARY KEY,
    name TEXT,
    idoficio BIGINT,
    pubname TEXT,
    arttype TEXT,
    pubdate TIMESTAMP WITHOUT TIME ZONE,
    artclass TEXT,
    artcategory TEXT,
    artsize BIGINT,
    artnotes TEXT,
    numberpage BIGINT,
    pdfpage TEXT,
    editionnumber TEXT,
    highlighttype TEXT,
    highlightpriority FLOAT,
    highlight TEXT,
    highlightimage TEXT,
    highlightimagename TEXT,
    idmateria BIGINT,
    midias TEXT,
    identifica TEXT,
    data TEXT,
    ementa TEXT,
    titulo TEXT,
    subtitulo TEXT,
    texto TEXT,
    assina TEXT
  )