\c mydb;

DROP TABLE IF EXISTS enrollments CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS faculty CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS system_users CASCADE;

CREATE TABLE system_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'faculty', 'admin')),
    email VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE students (
    student_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES system_users(user_id),
    roll_number VARCHAR(20) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    cgpa NUMERIC(3,2)
);

CREATE TABLE faculty (
    faculty_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES system_users(user_id),
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100) NOT NULL
);

CREATE TABLE courses (
    course_id SERIAL PRIMARY KEY,
    course_code VARCHAR(20) UNIQUE NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    credits INTEGER NOT NULL,
    faculty_id INTEGER REFERENCES faculty(faculty_id),
    department VARCHAR(100) NOT NULL
);

CREATE TABLE enrollments (
    enrollment_id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id),
    course_id INTEGER REFERENCES courses(course_id),
    grade VARCHAR(2),
    semester VARCHAR(20) NOT NULL,
    UNIQUE(student_id, course_id, semester)
);

CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    operation VARCHAR(50) NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    executed_by VARCHAR(100) NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL
);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_admin_only ON audit_log
    FOR SELECT
    USING (current_setting('app.role', true) = 'admin');

CREATE OR REPLACE VIEW active_users AS
SELECT user_id, username, email, full_name, role, is_active, created_at
FROM system_users
WHERE is_active = TRUE;

INSERT INTO system_users (username, password_hash, role, email, full_name) VALUES 
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oe2K7xpkJu9u', 'admin', 'admin@university.edu', 'Admin User'),
    ('student1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'student', 'student1@university.edu', 'John Doe'),
    ('faculty1', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'faculty', 'faculty1@university.edu', 'Dr. Jane Smith');

INSERT INTO students (user_id, roll_number, department, year, cgpa) VALUES 
    (2, 'CS2021001', 'Computer Science', 3, 8.5);

INSERT INTO faculty (user_id, employee_id, department, designation) VALUES 
    (3, 'FAC001', 'Computer Science', 'Professor');

INSERT INTO courses (course_code, course_name, credits, faculty_id, department) VALUES 
    ('CS101', 'Introduction to Programming', 4, 1, 'Computer Science'),
    ('CS201', 'Data Structures', 4, 1, 'Computer Science'),
    ('CS301', 'Database Systems', 3, 1, 'Computer Science');

INSERT INTO enrollments (student_id, course_id, grade, semester) VALUES 
    (1, 1, 'A', 'Fall 2023'),
    (1, 2, 'B+', 'Spring 2024');

CREATE OR REPLACE FUNCTION log_operation(
    p_operation VARCHAR,
    p_table VARCHAR,
    p_user VARCHAR,
    p_status VARCHAR
) RETURNS VOID AS $$
BEGIN
    INSERT INTO audit_log (operation, table_name, executed_by, status)
    VALUES (p_operation, p_table, p_user, p_status);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_my_profile(p_user_id INTEGER, p_role VARCHAR)
RETURNS TABLE(
    user_id INTEGER,
    username VARCHAR,
    email VARCHAR,
    full_name VARCHAR,
    role VARCHAR,
    additional_info TEXT
) AS $$
BEGIN
    IF p_role = 'student' THEN
        RETURN QUERY
        SELECT su.user_id, su.username, su.email, su.full_name, su.role,
               format('Roll: %s, Dept: %s, Year: %s, CGPA: %s', 
                      s.roll_number, s.department, s.year, s.cgpa) as additional_info
        FROM system_users su
        JOIN students s ON su.user_id = s.user_id
        WHERE su.user_id = p_user_id;
    ELSIF p_role = 'faculty' THEN
        RETURN QUERY
        SELECT su.user_id, su.username, su.email, su.full_name, su.role,
               format('Emp ID: %s, Dept: %s, Designation: %s', 
                      f.employee_id, f.department, f.designation) as additional_info
        FROM system_users su
        JOIN faculty f ON su.user_id = f.user_id
        WHERE su.user_id = p_user_id;
    ELSE
        RETURN QUERY
        SELECT su.user_id, su.username, su.email, su.full_name, su.role,
               'Administrator' as additional_info
        FROM system_users su
        WHERE su.user_id = p_user_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_audit_logs(p_role VARCHAR)
RETURNS TABLE(
    log_id INTEGER,
    operation VARCHAR,
    table_name VARCHAR,
    executed_by VARCHAR,
    executed_at TIMESTAMP,
    status VARCHAR
) AS $$
BEGIN
    IF p_role != 'admin' THEN
        RAISE EXCEPTION 'Only admin can view audit logs';
    END IF;
    
    -- Set session variable to bypass RLS
    PERFORM set_config('app.role', 'admin', true);
    
    RETURN QUERY
    SELECT a.log_id, a.operation, a.table_name, a.executed_by, a.executed_at, a.status
    FROM audit_log a
    ORDER BY a.executed_at DESC
    LIMIT 100;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION get_all_users(p_role VARCHAR)
RETURNS TABLE(
    user_id INTEGER,
    username VARCHAR,
    email VARCHAR,
    full_name VARCHAR,
    role VARCHAR,
    is_active BOOLEAN
) AS $$
BEGIN
    IF p_role != 'admin' THEN
        RAISE EXCEPTION 'Only admin can view all users';
    END IF;
    
    RETURN QUERY
    SELECT su.user_id, su.username, su.email, su.full_name, su.role, su.is_active
    FROM system_users su
    ORDER BY su.role, su.full_name;
END;
$$ LANGUAGE plpgsql;
