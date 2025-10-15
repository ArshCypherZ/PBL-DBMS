# Backend API
# Integrated by: Arsh Javed
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import Database
from gemini_parser import GeminiParser
import uvicorn
import jwt
import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI-Native DBMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database()
parser = GeminiParser()
security = HTTPBearer()

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str
    email: str

class QueryRequest(BaseModel):
    text: str
    confirm: bool = False

class QueryResponse(BaseModel):
    success: bool
    message: str
    data: list = []
    explanation: str = ""
    sql_query: str = ""
    needs_confirmation: bool = False

class UserInfo(BaseModel):
    user_id: int
    username: str
    role: str
    email: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return UserInfo(
            user_id=payload.get("user_id"),
            username=payload.get("sub"),
            role=payload.get("role"),
            email=payload.get("email")
        )
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_admin(user: UserInfo = Depends(verify_token)) -> UserInfo:
    if user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

@app.get("/")
def root():
    return {"message": "AI-Native DBMS API"}

@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        users = {
            'admin': {'user_id': 1, 'role': 'admin', 'email': 'admin@university.edu'},
            'student1': {'user_id': 2, 'role': 'student', 'email': 'student1@university.edu'},
            'faculty1': {'user_id': 3, 'role': 'faculty', 'email': 'faculty1@university.edu'}
        }
        
        if request.username in users and request.password in ['admin123', 'user123']:
            user = users[request.username]
            token_data = {
                "sub": request.username,
                "user_id": user['user_id'],
                "role": user['role'],
                "email": user['email']
            }
            access_token = create_access_token(token_data)
            
            return LoginResponse(
                access_token=access_token,
                token_type="bearer",
                user_id=user['user_id'],
                username=request.username,
                role=user['role'],
                email=user['email']
            )
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
        

@app.get("/auth/me", response_model=UserInfo)
def get_current_user(user: UserInfo = Depends(verify_token)):
    return user

@app.post("/query", response_model=QueryResponse)
def execute_query(request: QueryRequest, user: UserInfo = Depends(verify_token)):
    try:
        parsed = parser.parse(request.text, user.username, user.role)
        
        if not parsed:
            raise HTTPException(status_code=400, detail="Could not parse query")
        
        if not request.confirm:
            # Generate SQL preview based on operation type
            if parsed.get('procedure'):
                sql_preview = f"CALL {parsed['procedure']}({', '.join(['%s'] * len(parsed.get('params', [])))})"
            else:
                sql_preview = parsed.get('query', 'SQL query will be generated')
            
            return QueryResponse(
                success=False,
                message="Please confirm the query",
                data=[],
                explanation=parsed.get('explanation', ''),
                sql_query=sql_preview,
                needs_confirmation=True
            )
        
        if parsed['operation'] == 'select':
            query = parsed['query'].lower()
            
            if user.role != 'admin':
                # Block direct access to audit_log table
                if 'from audit_log' in query or 'join audit_log' in query:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Cannot access audit logs"
                    )
                # Block queries that select password or other sensitive system_users fields directly
                if 'system_users.password' in query.replace(' ', ''):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Cannot access sensitive fields"
                    )
            
            result = db.execute_query(parsed['query'])
            db.execute_query("SELECT log_operation(%s, %s, %s, %s)", 
                           ['SELECT', 'query', user.username, 'SUCCESS'], fetch=False)
            return QueryResponse(
                success=True,
                message="Query executed successfully",
                data=[dict(row) for row in result],
                explanation=parsed.get('explanation', ''),
                sql_query=parsed.get('query', ''),
                needs_confirmation=False
            )
        
        elif parsed['operation'] in ['insert', 'update', 'delete']:
            # Permission checks
            if parsed['operation'] == 'delete' and user.role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admin can delete records"
                )
            
            if parsed['operation'] == 'insert' and user.role == 'student':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Students cannot add records"
                )
            
            # Check if procedure is specified
            if parsed.get('procedure'):
                placeholders = ','.join(['%s'] * len(parsed['params']))
                query = f"SELECT * FROM {parsed['procedure']}({placeholders})"
                result = db.execute_query(query, parsed['params'])
                
                return QueryResponse(
                    success=result[0].get('success', False),
                    message=result[0].get('message', 'Operation completed'),
                    data=[dict(row) for row in result],
                    explanation=parsed.get('explanation', ''),
                    sql_query=f"CALL {parsed['procedure']}({', '.join(map(str, parsed['params']))})",
                    needs_confirmation=False
                )
            else:
                if not parsed.get('query'):
                    raise HTTPException(status_code=400, detail="No query or procedure specified")
                
                db.execute_query(parsed['query'], parsed.get('params', []), fetch=False)
                db.execute_query("SELECT log_operation(%s, %s, %s, %s)", 
                               [parsed['operation'].upper(), 'query', user.username, 'SUCCESS'], fetch=False)
                
                return QueryResponse(
                    success=True,
                    message="Operation completed successfully",
                    data=[],
                    explanation=parsed.get('explanation', ''),
                    sql_query=parsed.get('query', ''),
                    needs_confirmation=False
                )
        else:
            raise HTTPException(status_code=400, detail="Unsupported operation")
    
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
      

@app.get("/profile")
def get_profile(user: UserInfo = Depends(verify_token)):
    try:
        result = db.execute_query(
            "SELECT * FROM get_my_profile(%s, %s)",
            [user.user_id, user.role]
        )
        return {"profile": dict(result[0]) if result else {}}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-logs")
def get_audit_logs(user: UserInfo = Depends(verify_token)):
    try:
        result = db.execute_query("SELECT * FROM get_audit_logs(%s)", [user.role])
        return {"logs": [dict(row) for row in result]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=403 if "Only admin" in str(e) else 500, detail=str(e))

@app.get("/users")
def get_users(user: UserInfo = Depends(require_admin)):
    try:
        result = db.execute_query("SELECT * FROM get_all_users(%s)", [user.role])
        return {"users": [dict(row) for row in result]}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema")
def get_schema(user: UserInfo = Depends(verify_token)):
    try:
        if user.role == 'admin':
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            columns_query = "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' ORDER BY table_name, ordinal_position"
            procedures_query = """
                SELECT 
                    r.routine_name,
                    COALESCE(
                        string_agg(
                            COALESCE(p.parameter_name, '') || ' ' || COALESCE(p.data_type, ''), 
                            ', ' ORDER BY p.ordinal_position
                        ),
                        'no parameters'
                    ) as parameters
                FROM information_schema.routines r
                LEFT JOIN information_schema.parameters p 
                    ON r.specific_name = p.specific_name 
                    AND p.parameter_mode = 'IN'
                WHERE r.routine_schema = 'public' 
                    AND r.routine_type = 'FUNCTION'
                GROUP BY r.routine_name
                ORDER BY r.routine_name
            """
        else:
            tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT IN ('audit_log', 'system_users') ORDER BY table_name"
            columns_query = "SELECT table_name, column_name, data_type FROM information_schema.columns WHERE table_schema = 'public' AND table_name NOT IN ('audit_log', 'system_users') ORDER BY table_name, ordinal_position"
            
            # Filter procedures based on role
            if user.role == 'faculty':
                # Faculty can see enrollment and grade management procedures
                allowed_procs = ['enroll_student', 'update_grade', 'get_student_courses', 'get_faculty_courses', 'get_course_enrollments', 'get_my_profile']
            else:  # student
                # Students can only view their own data
                allowed_procs = ['get_student_courses', 'get_my_profile']
            
            procedures_query = f"""
                SELECT 
                    r.routine_name,
                    COALESCE(
                        string_agg(
                            COALESCE(p.parameter_name, '') || ' ' || COALESCE(p.data_type, ''), 
                            ', ' ORDER BY p.ordinal_position
                        ),
                        'no parameters'
                    ) as parameters
                FROM information_schema.routines r
                LEFT JOIN information_schema.parameters p 
                    ON r.specific_name = p.specific_name 
                    AND p.parameter_mode = 'IN'
                WHERE r.routine_schema = 'public' 
                    AND r.routine_type = 'FUNCTION'
                    AND r.routine_name IN ({','.join([f"'{p}'" for p in allowed_procs])})
                GROUP BY r.routine_name
                ORDER BY r.routine_name
            """
        
        tables = db.execute_query(tables_query)
        columns = db.execute_query(columns_query)
        procedures = db.execute_query(procedures_query)
        
        return {
            "tables": [dict(row) for row in tables],
            "columns": [dict(row) for row in columns],
            "procedures": [dict(row) for row in procedures] if procedures else []
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/procedures/load")
def load_procedures(user: UserInfo = Depends(require_admin)):
    try:
        procedures_file = "database/procedures.sql"
        if not os.path.exists(procedures_file):
            raise HTTPException(status_code=404, detail="Procedures file not found")
        
        with open(procedures_file, 'r') as f:
            sql_content = f.read()
        
        db.execute_query(sql_content, fetch=False)
        
        return {"success": True, "message": "Procedures loaded successfully"}
    except Exception as e:
        print("Exception: ", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
