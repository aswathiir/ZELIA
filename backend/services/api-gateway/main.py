from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, schemes, templates, submission, status

app = FastAPI(
    title="ZELIA API Gateway", 
    version="0.2.0",
    description="Government Welfare Scheme Application System"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service Health Check
@app.get("/health")
def health_check():
    return {"status": "up", "service": "api-gateway", "version": "0.2.0"}

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(schemes.router, prefix="/schemes", tags=["Schemes"])
app.include_router(templates.router, prefix="/templates", tags=["Templates"])
app.include_router(submission.router, prefix="/submission", tags=["Submission"])
app.include_router(status.router, prefix="/status", tags=["Status"])

