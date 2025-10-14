CREATE OR REPLACE FUNCTION add_student(
    p_username VARCHAR,
    p_password_hash VARCHAR,
    p_email VARCHAR,
    p_full_name VARCHAR,
    p_roll_number VARCHAR,
    p_department VARCHAR,
    p_year INTEGER,
    p_cgpa NUMERIC
) RETURNS TABLE(success BOOLEAN, message TEXT, student_id INTEGER) AS $$
DECLARE
    v_user_id INTEGER;
    v_student_id INTEGER;
BEGIN
    INSERT INTO system_users (username, password_hash, role, email, full_name)
    VALUES (p_username, p_password_hash, 'student', p_email, p_full_name)
    RETURNING user_id INTO v_user_id;
    
    INSERT INTO students (user_id, roll_number, department, year, cgpa)
    VALUES (v_user_id, p_roll_number, p_department, p_year, p_cgpa)
    RETURNING students.student_id INTO v_student_id;
    
    PERFORM log_operation('INSERT', 'students', p_username, 'SUCCESS');
    
    RETURN QUERY SELECT TRUE, 'Student added successfully'::TEXT, v_student_id;
EXCEPTION WHEN OTHERS THEN
    PERFORM log_operation('INSERT', 'students', p_username, 'FAILED');
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT, NULL::INTEGER;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_faculty(
    p_username VARCHAR,
    p_password_hash VARCHAR,
    p_email VARCHAR,
    p_full_name VARCHAR,
    p_employee_id VARCHAR,
    p_department VARCHAR,
    p_designation VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT, faculty_id INTEGER) AS $$
DECLARE
    v_user_id INTEGER;
    v_faculty_id INTEGER;
BEGIN
    INSERT INTO system_users (username, password_hash, role, email, full_name)
    VALUES (p_username, p_password_hash, 'faculty', p_email, p_full_name)
    RETURNING user_id INTO v_user_id;
    
    INSERT INTO faculty (user_id, employee_id, department, designation)
    VALUES (v_user_id, p_employee_id, p_department, p_designation)
    RETURNING faculty.faculty_id INTO v_faculty_id;
    
    PERFORM log_operation('INSERT', 'faculty', p_username, 'SUCCESS');
    
    RETURN QUERY SELECT TRUE, 'Faculty added successfully'::TEXT, v_faculty_id;
EXCEPTION WHEN OTHERS THEN
    PERFORM log_operation('INSERT', 'faculty', p_username, 'FAILED');
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT, NULL::INTEGER;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_course(
    p_course_code VARCHAR,
    p_course_name VARCHAR,
    p_credits INTEGER,
    p_faculty_id INTEGER,
    p_department VARCHAR,
    p_username VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT, course_id INTEGER) AS $$
DECLARE
    v_course_id INTEGER;
BEGIN
    INSERT INTO courses (course_code, course_name, credits, faculty_id, department)
    VALUES (p_course_code, p_course_name, p_credits, p_faculty_id, p_department)
    RETURNING courses.course_id INTO v_course_id;
    
    PERFORM log_operation('INSERT', 'courses', p_username, 'SUCCESS');
    
    RETURN QUERY SELECT TRUE, 'Course added successfully'::TEXT, v_course_id;
EXCEPTION WHEN OTHERS THEN
    PERFORM log_operation('INSERT', 'courses', p_username, 'FAILED');
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT, NULL::INTEGER;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enroll_student(
    p_student_id INTEGER,
    p_course_id INTEGER,
    p_semester VARCHAR,
    p_username VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
BEGIN
    INSERT INTO enrollments (student_id, course_id, semester)
    VALUES (p_student_id, p_course_id, p_semester);
    
    PERFORM log_operation('INSERT', 'enrollments', p_username, 'SUCCESS');
    
    RETURN QUERY SELECT TRUE, 'Student enrolled successfully'::TEXT;
EXCEPTION WHEN OTHERS THEN
    PERFORM log_operation('INSERT', 'enrollments', p_username, 'FAILED');
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_grade(
    p_enrollment_id INTEGER,
    p_grade VARCHAR,
    p_username VARCHAR
) RETURNS TABLE(success BOOLEAN, message TEXT) AS $$
BEGIN
    UPDATE enrollments SET grade = p_grade WHERE enrollment_id = p_enrollment_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Enrollment not found';
    END IF;
    
    PERFORM log_operation('UPDATE', 'enrollments', p_username, 'SUCCESS');
    
    RETURN QUERY SELECT TRUE, 'Grade updated successfully'::TEXT;
EXCEPTION WHEN OTHERS THEN
    PERFORM log_operation('UPDATE', 'enrollments', p_username, 'FAILED');
    RETURN QUERY SELECT FALSE, SQLERRM::TEXT;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_student_courses(p_student_id INTEGER)
RETURNS TABLE(
    course_code VARCHAR,
    course_name VARCHAR,
    credits INTEGER,
    grade VARCHAR,
    semester VARCHAR,
    faculty_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.course_code, c.course_name, c.credits, e.grade, e.semester, su.full_name as faculty_name
    FROM enrollments e
    JOIN courses c ON e.course_id = c.course_id
    LEFT JOIN faculty f ON c.faculty_id = f.faculty_id
    LEFT JOIN system_users su ON f.user_id = su.user_id
    WHERE e.student_id = p_student_id
    ORDER BY e.semester DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_faculty_courses(p_faculty_id INTEGER)
RETURNS TABLE(
    course_code VARCHAR,
    course_name VARCHAR,
    credits INTEGER,
    department VARCHAR,
    enrolled_students BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT c.course_code, c.course_name, c.credits, c.department, COUNT(e.enrollment_id) as enrolled_students
    FROM courses c
    LEFT JOIN enrollments e ON c.course_id = e.course_id
    WHERE c.faculty_id = p_faculty_id
    GROUP BY c.course_id, c.course_code, c.course_name, c.credits, c.department
    ORDER BY c.course_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_course_enrollments(p_course_id INTEGER)
RETURNS TABLE(
    enrollment_id INTEGER,
    student_name VARCHAR,
    roll_number VARCHAR,
    grade VARCHAR,
    semester VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT e.enrollment_id, su.full_name as student_name, s.roll_number, e.grade, e.semester
    FROM enrollments e
    JOIN students s ON e.student_id = s.student_id
    JOIN system_users su ON s.user_id = su.user_id
    WHERE e.course_id = p_course_id
    ORDER BY s.roll_number;
END;
$$ LANGUAGE plpgsql;
