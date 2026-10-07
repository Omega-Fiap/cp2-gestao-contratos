BEGIN;

CREATE TABLE IF NOT EXISTS analise_contrato (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER NOT NULL UNIQUE
        REFERENCES contrato(id) ON DELETE CASCADE,
    texto_hash VARCHAR(64) NOT NULL,
    modelo VARCHAR NOT NULL,
    versao_prompt VARCHAR NOT NULL,
    analisado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resultado_analise_clausula (
    id SERIAL PRIMARY KEY,
    analise_id INTEGER NOT NULL
        REFERENCES analise_contrato(id) ON DELETE CASCADE,
    tipo VARCHAR NOT NULL,
    valor_ou_percentual VARCHAR NOT NULL DEFAULT '',
    impacto VARCHAR NOT NULL CHECK (impacto IN ('baixo', 'médio', 'alto')),
    trecho_original TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_resultado_analise_clausula_analise_id
    ON resultado_analise_clausula(analise_id);

COMMIT;
