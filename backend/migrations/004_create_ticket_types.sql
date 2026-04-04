CREATE TABLE IF NOT EXISTS ticket_types (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES events(id),
  name TEXT NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  total_slots INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
