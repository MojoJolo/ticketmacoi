ALTER TABLE orders ADD COLUMN IF NOT EXISTS ticket_type_id UUID REFERENCES ticket_types(id);
