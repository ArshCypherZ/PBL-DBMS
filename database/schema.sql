-- Database Schema for AI-Native DBMS
-- Created by: Nayan Kumar

CREATE DATABASE ai_dbms;
\c ai_dbms;

-- Sample table for demonstration
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    log_id SERIAL PRIMARY KEY,
    operation VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    query_text TEXT NOT NULL,
    executed_by VARCHAR(100),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    error_message TEXT
);

-- Function to log operations
CREATE OR REPLACE FUNCTION log_operation(
    p_operation VARCHAR,
    p_table VARCHAR,
    p_query TEXT,
    p_user VARCHAR,
    p_status VARCHAR,
    p_error TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_log_id INTEGER;
BEGIN
    INSERT INTO audit_log (operation, table_name, query_text, executed_by, status, error_message)
    VALUES (p_operation, p_table, p_query, p_user, p_status, p_error)
    RETURNING log_id INTO v_log_id;
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- Stored procedure for safe insert
CREATE OR REPLACE FUNCTION safe_insert_user(
    p_name VARCHAR,
    p_email VARCHAR,
    p_user VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT, user_id INTEGER) AS $$
DECLARE
    v_user_id INTEGER;
    v_log_id INTEGER;
BEGIN
    BEGIN
        INSERT INTO users (name, email) VALUES (p_name, p_email) RETURNING id INTO v_user_id;
        v_log_id := log_operation('INSERT', 'users', 
            format('INSERT INTO users (name, email) VALUES (%L, %L)', p_name, p_email),
            p_user, 'SUCCESS');
        RETURN QUERY SELECT TRUE, 'User inserted successfully'::TEXT, v_user_id;
    EXCEPTION WHEN OTHERS THEN
        v_log_id := log_operation('INSERT', 'users',
            format('INSERT INTO users (name, email) VALUES (%L, %L)', p_name, p_email),
            p_user, 'FAILED', SQLERRM);
        RETURN QUERY SELECT FALSE, SQLERRM::TEXT, NULL::INTEGER;
    END;
END;
$$ LANGUAGE plpgsql;

-- Stored procedure for safe update
CREATE OR REPLACE FUNCTION safe_update_user(
    p_id INTEGER,
    p_name VARCHAR,
    p_email VARCHAR,
    p_user VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
DECLARE
    v_log_id INTEGER;
BEGIN
    BEGIN
        UPDATE users SET name = p_name, email = p_email WHERE id = p_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'User not found';
        END IF;
        v_log_id := log_operation('UPDATE', 'users',
            format('UPDATE users SET name=%L, email=%L WHERE id=%s', p_name, p_email, p_id),
            p_user, 'SUCCESS');
        RETURN QUERY SELECT TRUE, 'User updated successfully'::TEXT;
    EXCEPTION WHEN OTHERS THEN
        v_log_id := log_operation('UPDATE', 'users',
            format('UPDATE users SET name=%L, email=%L WHERE id=%s', p_name, p_email, p_id),
            p_user, 'FAILED', SQLERRM);
        RETURN QUERY SELECT FALSE, SQLERRM::TEXT;
    END;
END;
$$ LANGUAGE plpgsql;

-- sample data
INSERT INTO users (name, email) VALUES 
    ('John Doe', 'john@example.com'),
    ('Jane Smith', 'jane@example.com');
