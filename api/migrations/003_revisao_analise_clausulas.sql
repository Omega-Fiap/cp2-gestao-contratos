BEGIN;

ALTER TABLE resultado_analise_clausula
    ADD COLUMN IF NOT EXISTS status_revisao VARCHAR NOT NULL DEFAULT 'pendente';

ALTER TABLE resultado_analise_clausula
    ADD COLUMN IF NOT EXISTS tipo_corrigido VARCHAR;

ALTER TABLE resultado_analise_clausula
    ADD COLUMN IF NOT EXISTS valor_corrigido VARCHAR;

ALTER TABLE resultado_analise_clausula
    ADD COLUMN IF NOT EXISTS impacto_corrigido VARCHAR;

ALTER TABLE resultado_analise_clausula
    ADD COLUMN IF NOT EXISTS revisado_em TIMESTAMP WITHOUT TIME ZONE;

COMMIT;