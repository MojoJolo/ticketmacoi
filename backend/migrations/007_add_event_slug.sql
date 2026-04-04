ALTER TABLE events
ADD COLUMN IF NOT EXISTS slug TEXT;

UPDATE events
SET slug = CASE title
  WHEN 'Manila Soundscape Live' THEN 'manila-soundscape-live'
  WHEN 'Tanghalang Pilipino Gala Night' THEN 'tanghalang-pilipino-gala-night'
  WHEN 'Philippine Philharmonic Evening' THEN 'philippine-philharmonic-evening'
  ELSE slug
END
WHERE slug IS NULL;

ALTER TABLE events
ALTER COLUMN slug SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'events_slug_key'
  ) THEN
    ALTER TABLE events
    ADD CONSTRAINT events_slug_key UNIQUE (slug);
  END IF;
END $$;
