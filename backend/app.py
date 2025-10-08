# Backend API with Transaction Execution and Audit Logging
# Integrated by: Arsh Javed

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import Database
from nlp_parser import NLPParser
import uvicorn

app = FastAPI(title="AI-Native DBMS API")
db = Database()
parser = NLPParser()

class QueryRequest(BaseModel):
    text: str

class QueryResponse(BaseModel):
    success: bool
    message: str
    data: list = []

@app.post("/query", response_model=QueryResponse)
def execute_query(request: QueryRequest):
    try:
        parsed = parser.parse(request.text)
        
        if not parsed:
            raise HTTPException(status_code=400, detail="Could not parse query")
        
        if parsed['operation'] == 'select':
            result = db.execute_query(parsed['query'])
            return QueryResponse(
                success=True,
                message="Query executed successfully",
                data=[dict(row) for row in result]
            )
        
        elif parsed['operation'] in ['insert', 'update']:
            query = f"SELECT * FROM {parsed['procedure']}({','.join(['%s'] * len(parsed['params']))})"
            result = db.execute_query(query, parsed['params'])
            return QueryResponse(
                success=result[0]['success'],
                message=result[0]['message'],
                data=[dict(row) for row in result]
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit-logs")
def get_audit_logs():
    try:
        result = db.execute_query("SELECT * FROM audit_log ORDER BY executed_at DESC LIMIT 50")
        return {"logs": [dict(row) for row in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
