CREATE TYPE ENUM AS UserStatus (
    'Active',
    'Suspended',
    'Deleted'
)

CREATE TYPE ENUM AS BookFormat (
    'Hardcover',
    'Paperback',
    'Digital'
)

CREATE TABLE commerce.users (
    id SERIAL PRIMARY KEY,
    fullname VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_no INTEGER DEFAULT NULL,
    password_hash VARCHAR(255) DEFAULT NULL,
    user_status UserStatus DEFAULT 'Active'
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.addresses (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL references commerce.users(id) ON DELETE RESTRICT,
    city VARCHAR(255) NOT NULL,
    address_state VARCHAR(255) NOT NULL,
    description VARCHAR(255) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE
)

CREATE TABLE commerce.genre (
    id SERIAL PRIMARY KEY,
    genre_name VARCHAR(255) NOT NULL,
    image_url TEXT DEFAULT NULL
)

CREATE TABLE commerce.series (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    image_url TEXT DEFAULT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
)

CREATE TABLE commerce.books (
    id SERIAL PRIMARY KEY,
    series_id INT references commerce.series(id) DEFAULT NULL ON DELETE RESTRICT,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE
)

CREATE TABLE commerce.authors (
    id SERIAL PRIMARY KEY,
    author_name VARCHAR(255) NOT NULL,
    bio VARCHAR(255) NOT NULL
)

CREATE TABLE commerce.publishers (
    id SERIAL PRIMARY KEY,
    publisher_name VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL
)

CREATE TABLE commerce.books_authors_pivot (
    book_id INT references commerce.books(id),
    author_id INT references commerce.authors(id) ON DELETE RESTRICT,
    author_role VARCHAR(255) NOT NULL
)

CREATE TABLE commerce.books_publishers_pivot (
    book_id INT references commerce.books(id),
    publisher_id INT references commerce.publishers(id) ON DELETE RESTRICT
)

CREATE TABLE commerce.genre_books_pivot (
    genre_id INT references commerce.genre(id) ON DELETE SET NULL,
    book_id INT references commerce.books(id)
)

CREATE TABLE commerce.sku(
    id SERIAL PRIMARY KEY,
    book_id INT references commerce.books(id) ON DELETE RESTRICT,
    code VARCHAR(30) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    quantity INT,
    format BookFormat NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.carts (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) DEFAULT ON DELETE CASCADE,
    session_id VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL
)

CREATE TABLE commerce.cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INT references commerce.carts(id) ON DELETE CASCADE,
    sku_id INT references commerce.sku(id),
    quantity INT NOT NULL
)

CREATE TABLE commerce.orders (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) ON DELETE RESTRICT,
    total_amount DECIMAL(10, 2) NOT NULL,
    address_city VARCHAR(255) NOT NULL,
    address_state VARCHAR(255) NOT NULL,
    address_description TEXT NOT NULL,
    order_status VARCHAR(255) DEFAULT 'Placed',
    created_at TIMESTAMPTZ NOT NULL,
    delivered_at TIMESTAMPTZ DEFAULT NULL
)

CREATE TABLE commerce.order_items (
    id SERIAL PRIMARY KEY,
    order_id INT references commerce.orders(id) ON DELETE RESTRICT,
    sku_id INT references commerce.sku(id) ON DELETE RESTRICT,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL
)

CREATE TABLE commerce.payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INT references commerce.users(id) DEFAULT NULL ON DELETE CASCADE,
    provider VARCHAR(255) NOT NULL,
    method_type VARCHAR(255) NOT NULL,
    token VARCHAR(255) DEFAULT NULL,
    last_four_digits INT DEFAULT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
)

CREATE TABLE commerce.payments (
    id SERIAL PRIMARY KEY,
    order_id BIGINT references commerce.orders(id) ON DELETE RESTRICT,
    payment_method_id INT references commerce.payment_methods(id) ON DELETE SET NULL,
    method_type VARCHAR(50) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    last_four_digits INT DEFAULT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE,
    payment_status VARCHAR(255) DEFAULT 'Pending'
    payment_date TIMESTAMPTZ,
)

CREATE TABLE commerce.transaction_logs (
    id SERIAL PRIMARY KEY
    transaction_id VARCHAR(255) references commerce.payments(transaction_id) ON DELETE RESTRICT,
    events VARCHAR(50) NOT NULL,
    details TEXT DEFAULT NULL,
    time_stamp TIMESTAMPTZ DEFAULT NOW()
)
