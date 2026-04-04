CREATE TABLE IF NOT EXISTS events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  event_date TIMESTAMPTZ NOT NULL,
  venue_name TEXT,
  venue_address TEXT,
  poster_url TEXT,
  ticket_price NUMERIC(10,2),
  total_slots INTEGER,
  status TEXT DEFAULT 'draft',
  producer_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
