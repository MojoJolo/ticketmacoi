CREATE TABLE IF NOT EXISTS tickets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id),
  event_id UUID NOT NULL REFERENCES events(id),
  ticket_number INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
