BEGIN;

ALTER TABLE clausula DROP CONSTRAINT IF EXISTS clausula_contrato_id_fkey;
ALTER TABLE clausula ADD CONSTRAINT clausula_contrato_id_fkey
    FOREIGN KEY (contrato_id) REFERENCES contrato(id) ON DELETE CASCADE;

ALTER TABLE aditivo DROP CONSTRAINT IF EXISTS aditivo_contrato_id_fkey;
ALTER TABLE aditivo ADD CONSTRAINT aditivo_contrato_id_fkey
    FOREIGN KEY (contrato_id) REFERENCES contrato(id) ON DELETE CASCADE;

ALTER TABLE historico_status DROP CONSTRAINT IF EXISTS historico_status_contrato_id_fkey;
ALTER TABLE historico_status ADD CONSTRAINT historico_status_contrato_id_fkey
    FOREIGN KEY (contrato_id) REFERENCES contrato(id) ON DELETE CASCADE;

COMMIT;
