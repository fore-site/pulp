CREATE TYPE ENUM UserStatus (
    
)

CREATE TABLE commerce.users (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)

CREATE TABLE commerce.products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price FLOAT NOT NULL
)

CREATE TABLE commerce.orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER references commerce.products(id),
    user_id INTEGER references commerce.users(id)
    paid BOOLEAN,
    delivered BOOLEAN
)