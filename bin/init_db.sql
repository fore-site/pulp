CREATE TYPE ENUM AS UserStatus (
    'ACTIVE',
    'SUSPENDED',
    'DELETED'
)

CREATE TABLE commerce.users (
    id SERIAL PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password VARCHAR(10) NOT NULL
    address TEXT DEFAULT NULL,
    user_status UserStatus DEFAULT 'ACTIVE'
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.categories (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER references commerce.categories(id) DEFAULT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    image TEXT DEFAULT NULL
)

CREATE TABLE commerce.products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.category_product_lookup (
    category_id INTEGER references commerce.categories(id),
    product_id INTEGER references commerce.products(id)
    PRIMARY KEY (category_id, product_id)
)

CREATE TABLE commerce.sku(
    id SERIAL PRIMARY KEY,
    product_id INTEGER references commerce.products(id),
    code TEXT UNIQUE,
    price DECIMAL NOT NULL,
    stock_quantity INTEGER NOT NULL
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.attributes(
    id SERIAL PRIMARY KEY
    name VARCHAR(10) NOT NULL
    value VARCHAR(255) NOT NULL
)

CREATE TABLE commerce.atrributes_sku_pivot(
    id SERIAL PRIMARY KEY,
    attribute_id INTEGER references commerce.attributes(id),
    sku_id INTEGER references commerce.sku(id)
)

CREATE TABLE commerce.orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER references commerce.users(id)
    sku_id INTEGER references commerce.sku(id),
    quantity INTEGER NOT NULL,
    price INTEGER NOT NULL,
    address TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    delivered BOOLEAN DEFAULT FALSE
)
