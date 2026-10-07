BEGIN;

ALTER TABLE cliente
    ADD COLUMN IF NOT EXISTS usuario_id INTEGER
    REFERENCES usuario(id);

CREATE INDEX IF NOT EXISTS ix_cliente_usuario_id
    ON cliente(usuario_id);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'cliente'::regclass
          AND contype = 'u'
          AND conname = 'cliente_documento_key'
    ) THEN
        ALTER TABLE cliente DROP CONSTRAINT cliente_documento_key;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_cliente_usuario_documento
    ON cliente(usuario_id, documento)
    WHERE documento IS NOT NULL;

WITH proprietario_unico AS (
    SELECT cliente_id, MIN(usuario_id) AS usuario_id
    FROM contrato
    WHERE usuario_id IS NOT NULL
    GROUP BY cliente_id
    HAVING COUNT(DISTINCT usuario_id) = 1
)
UPDATE cliente
SET usuario_id = proprietario_unico.usuario_id
FROM proprietario_unico
WHERE cliente.id = proprietario_unico.cliente_id
  AND cliente.usuario_id IS NULL;

COMMIT;