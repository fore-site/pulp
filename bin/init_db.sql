CREATE TYPE commerce.UserStatus AS ENUM (
    'Active',
    'Suspended',
    'Deleted'
);

CREATE TYPE commerce.BookFormat AS ENUM (
    'Hardcover',
    'Paperback',
    'Digital'
);

CREATE TABLE IF NOT EXISTS commerce.users (
    id SERIAL PRIMARY KEY,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_no VARCHAR(50),
    password_hash VARCHAR(255),
    user_status commerce.UserStatus DEFAULT 'Active',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.addresses (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL references commerce.users(id) ON DELETE RESTRICT,
    city VARCHAR(255) NOT NULL,
    address_state VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS commerce.genre (
    id SERIAL PRIMARY KEY,
    genre_name VARCHAR(255) NOT NULL,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS commerce.series (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    image_url TEXT,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS commerce.books (
    id SERIAL PRIMARY KEY,
    series_id INT references commerce.series(id) ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS commerce.authors (
    id SERIAL PRIMARY KEY,
    author_name VARCHAR(255) NOT NULL,
    bio VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.publishers (
    id SERIAL PRIMARY KEY,
    publisher_name VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.books_authors_pivot (
    book_id INT references commerce.books(id) NOT NULL,
    author_id INT references commerce.authors(id) ON DELETE RESTRICT NOT NULL,
    author_role VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.books_publishers_pivot (
    book_id INT references commerce.books(id) NOT NULL,
    publisher_id INT references commerce.publishers(id) ON DELETE RESTRICT NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.genre_books_pivot (
    genre_id INT references commerce.genre(id) ON DELETE SET NULL,
    book_id INT references commerce.books(id) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.sku (
    id SERIAL PRIMARY KEY,
    book_id INT references commerce.books(id) ON DELETE RESTRICT NOT NULL,
    code VARCHAR(30) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    quantity INT,
    format commerce.BookFormat NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.carts (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) ON DELETE CASCADE NOT NULL,
    session_id VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INT references commerce.carts(id) ON DELETE CASCADE NOT NULL,
    sku_id INT references commerce.sku(id) ON DELETE RESTRICT NOT NULL,
    quantity INT NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.orders (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) ON DELETE RESTRICT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    address_city VARCHAR(255) NOT NULL,
    address_state VARCHAR(255) NOT NULL,
    address_description TEXT NOT NULL,
    order_status VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS commerce.order_items (
    id SERIAL PRIMARY KEY,
    order_id INT references commerce.orders(id) ON DELETE RESTRICT NOT NULL,
    sku_id INT references commerce.sku(id) ON DELETE RESTRICT NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) ON DELETE CASCADE,
    provider VARCHAR(255) NOT NULL,
    method_type VARCHAR(255) NOT NULL,
    token VARCHAR(255),
    last_four_digits VARCHAR(4),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS commerce.payments (
    id SERIAL PRIMARY KEY,
    order_id BIGINT references commerce.orders(id) ON DELETE RESTRICT NOT NULL,
    payment_method_id INT references commerce.payment_methods(id) ON DELETE SET NULL,
    method_type VARCHAR(50) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    last_four_digits VARCHAR(4),
    amount DECIMAL(10, 2) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE,
    payment_status VARCHAR(255) NOT NULL,
    payment_date TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS commerce.transaction_logs (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(255) references commerce.payments(transaction_id) ON DELETE RESTRICT NOT NULL,
    events VARCHAR(50) NOT NULL,
    details TEXT,
    time_stamp TIMESTAMPTZ NOT NULL
);
