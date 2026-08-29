-- 001: ограничения целостности и идемпотентность событий.
--
-- Схема создаётся через Base.metadata.create_all(), который добавляет новые
-- ТАБЛИЦЫ, но не меняет существующие. Этот скрипт доводит уже развёрнутую БД
-- до состояния, описанного в app/models.py.
--
-- Идемпотентен: повторный запуск безопасен.

BEGIN;

-- Одна сущность — одно назначение. Без этого параллельные запросы
-- assignment создают дубли, из-за которых SRM считает сущность дважды.
ALTER TABLE assignments
    DROP CONSTRAINT IF EXISTS uq_assignment_entity;
ALTER TABLE assignments
    ADD CONSTRAINT uq_assignment_entity UNIQUE (experiment_id, entity_id);

-- Уникальность имён вариантов внутри эксперимента.
ALTER TABLE variants
    DROP CONSTRAINT IF EXISTS uq_variant_experiment_name;
ALTER TABLE variants
    ADD CONSTRAINT uq_variant_experiment_name UNIQUE (experiment_id, name);

-- Ключ идемпотентности события: защита от повторной отправки при сетевом retry.
ALTER TABLE events
    ADD COLUMN IF NOT EXISTS event_key VARCHAR;
ALTER TABLE events
    DROP CONSTRAINT IF EXISTS uq_event_key;
ALTER TABLE events
    ADD CONSTRAINT uq_event_key UNIQUE (experiment_id, event_key);

CREATE INDEX IF NOT EXISTS ix_events_lookup
    ON events (experiment_id, metric_name, entity_id);

-- Момент остановки эксперимента.
ALTER TABLE experiments
    ADD COLUMN IF NOT EXISTS stopped_at TIMESTAMP;

-- Сохранённые расчёты: раньше таблица существовала, но не заполнялась
-- и не хранила ни метрику, ни размеры групп.
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS metric_name VARCHAR;
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS n_control INTEGER;
ALTER TABLE results
    ADD COLUMN IF NOT EXISTS n_treatment INTEGER;

COMMIT;
