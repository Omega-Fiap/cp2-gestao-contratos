BEGIN;

CREATE INDEX IF NOT EXISTS ix_contrato_usuario_id
    ON contrato(usuario_id);

CREATE INDEX IF NOT EXISTS ix_clausula_contrato_id
    ON clausula(contrato_id);

CREATE INDEX IF NOT EXISTS ix_aditivo_contrato_id
    ON aditivo(contrato_id);

CREATE INDEX IF NOT EXISTS ix_historico_status_contrato_id
    ON historico_status(contrato_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM contrato WHERE usuario_id IS NULL) THEN
        RAISE EXCEPTION 'Atribua todos os contratos existentes a um usuario antes de tornar contrato.usuario_id obrigatorio.';
    END IF;
END $$;

ALTER TABLE contrato
    ALTER COLUMN usuario_id SET NOT NULL;

COMMIT;BEGIN;

CREATE INDEX IF NOT EXISTS ix_contrato_usuario_id
    ON contrato(usuario_id);

CREATE INDEX IF NOT EXISTS ix_clausula_contrato_id
    ON clausula(contrato_id);

CREATE INDEX IF NOT EXISTS ix_aditivo_contrato_id
    ON aditivo(contrato_id);

CREATE INDEX IF NOT EXISTS ix_historico_status_contrato_id
    ON historico_status(contrato_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM contrato WHERE usuario_id IS NULL) THEN
        RAISE EXCEPTION 'Atribua todos os contratos existentes a um usuario antes de tornar contrato.usuario_id obrigatorio.';
    END IF;
END $$;

ALTER TABLE contrato
    ALTER COLUMN usuario_id SET NOT NULL;

COMMIT;