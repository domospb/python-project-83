-- Create the urls table if it doesn't exist
CREATE TABLE IF NOT EXISTS urls (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create a unique index on the name column
CREATE UNIQUE INDEX IF NOT EXISTS urls_name_idx ON urls (name);