# Gemini AI Parser

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import os
from dotenv import load_dotenv

load_dotenv()


class SQLQuery(BaseModel):
    operation: Literal['select', 'insert', 'update', 'delete'] = Field(description="SQL operation type")
    table: str = Field(description="Target table")
    query: Optional[str] = Field(default=None, description="Full SQL query for SELECT")
    procedure: Optional[str] = Field(default=None, description="Stored procedure name")
    params: List = Field(default_factory=list, description="Procedure parameters")
    explanation: str = Field(description="Query explanation")


class GeminiParser:
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = 'gemini-2.0-flash'
        
        self.system_instruction = """You are a SQL query generator for PostgreSQL university database.

TABLES:
1. system_users (user_id, username, email, full_name, role, is_active, created_at)
2. students (student_id, user_id, roll_number, department, year, cgpa)
3. faculty (faculty_id, user_id, employee_id, department, designation)
4. courses (course_id, course_code, course_name, credits, faculty_id, department)
5. enrollments (enrollment_id, student_id, course_id, grade, semester)

VIEWS:
- active_users (user_id, username, email, full_name, role, is_active, created_at)

STORED PROCEDURES:
1. add_student(p_username, p_password_hash, p_email, p_full_name, p_roll_number, p_department, p_year, p_cgpa) - Admin only
2. add_faculty(p_username, p_password_hash, p_email, p_full_name, p_employee_id, p_department, p_designation) - Admin only
3. add_course(p_course_code, p_course_name, p_credits, p_faculty_id, p_department, p_username) - Admin only
4. enroll_student(p_student_id, p_course_id, p_semester, p_username) - Admin/Faculty
5. update_grade(p_enrollment_id, p_grade, p_username) - Faculty only, requires enrollment_id NOT student_id
6. get_student_courses(p_student_id) - Returns student's enrolled courses with grades
7. get_faculty_courses(p_faculty_id) - Returns courses taught by faculty
8. get_course_enrollments(p_course_id) - Returns students enrolled in a course

IMPORTANT RULES:
1. For SELECT queries: Generate full SQL query using proper JOIN syntax
2. For INSERT/UPDATE operations with available procedures: Set procedure name and params
3. For UPDATE operations without procedures: Generate full UPDATE SQL query
4. Use system_users.user_id, not id
5. Use students.student_id, not id
6. Use faculty.faculty_id, not id
7. Use courses.course_id, not id
8. When querying students, JOIN with system_users on user_id
9. When querying faculty, JOIN with system_users on user_id
10. When querying enrollments for a student, use student_id (not user_id)
11. Only admin can access audit_log and system_users table directly
12. Students and faculty can only view their own data
13. Use stored procedures for insert/update operations when available
14. For profile updates (name, email): Generate UPDATE system_users SET ... WHERE username = 'username'
15. IMPORTANT: Grades are LETTER GRADES (A+, A, B+, B, etc.) NOT numeric values. Do not convert numbers to letters.
16. IMPORTANT: CGPA is stored in students table (numeric), grade is in enrollments table (letter)
17. If user provides numeric value for grade, return error explaining grades must be letter grades

EXAMPLES:
- "show all students" -> SELECT s.student_id, su.full_name, s.roll_number, s.department, s.year, s.cgpa FROM students s JOIN system_users su ON s.user_id = su.user_id WHERE su.is_active = TRUE
- "show my students" (for faculty) -> SELECT DISTINCT s.student_id, su.full_name, s.roll_number, s.department, s.year, s.cgpa FROM students s JOIN system_users su ON s.user_id = su.user_id JOIN enrollments e ON s.student_id = e.student_id JOIN courses c ON e.course_id = c.course_id WHERE c.faculty_id = (SELECT faculty_id FROM faculty WHERE user_id = (SELECT user_id FROM system_users WHERE username = 'username'))
- "show my courses" (for student) -> SELECT * FROM get_student_courses((SELECT student_id FROM students WHERE user_id = (SELECT user_id FROM system_users WHERE username = 'username')))
- "show all faculty" -> SELECT f.faculty_id, su.full_name, f.employee_id, f.department, f.designation FROM faculty f JOIN system_users su ON f.user_id = su.user_id WHERE su.is_active = TRUE
- "show enrollments for course 1" -> SELECT DISTINCT e.enrollment_id, e.student_id, su.full_name, e.grade, e.semester FROM enrollments e JOIN students s ON e.student_id = s.student_id JOIN system_users su ON s.user_id = su.user_id WHERE e.course_id = 1
- "enroll student 1 in course 2" -> procedure: enroll_student, params: [1, 2, 'Fall 2024', 'faculty1']
- "update grade of enrollment 5 to A+" -> procedure: update_grade, params: [5, 'A+', 'faculty1']
- "update cgpa of student 1 to 8.5" -> UPDATE students SET cgpa = 8.5 WHERE student_id = 1
- "update grade to 9.2" -> ERROR: Grades must be letter grades (A+, A, B+, etc.), not numeric values. Use "update cgpa" for numeric grades.
- "update my name to Arsh" -> UPDATE system_users SET full_name = 'Arsh' WHERE username = 'username'
"""

    def parse(self, text: str, username: str = 'system', role: str = 'user') -> dict:
        try:
            enhanced_prompt = f"""User: {username} (Role: {role})
Query: {text}

Convert to SQL operation with username and role in parameters."""
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    response_mime_type='application/json',
                    response_schema=SQLQuery,
                    temperature=0.1,
                    max_output_tokens=500,
                )
            )
            
            if response.text:
                import json
                result = json.loads(response.text)
                return result
        except Exception as e:
            print("Exception: ", e)
            return "Error while parsing the response."
    
    def close(self):
        """Close the Gemini client connection"""
        if hasattr(self.client, 'close'):
            self.client.close()
