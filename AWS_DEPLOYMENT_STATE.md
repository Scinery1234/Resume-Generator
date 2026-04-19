# AWS Deployment State — Resume Generator

This document captures the current AWS deployment so any engineer or AI assistant
can understand the infrastructure, make changes, or debug issues without starting
from scratch.

---

## Live URLs

| Service | URL |
|---|---|
| Frontend | https://d15qp9ffjs24sd.cloudfront.net |
| Backend API | https://tjnyvgariy.us-east-1.awsapprunner.com |
| API Docs (Swagger) | https://tjnyvgariy.us-east-1.awsapprunner.com/docs |

---

## AWS Account

| Field | Value |
|---|---|
| Account ID | 415407325416 |
| Region | us-east-1 |
| Root user | Yes (IAM user recommended for future work) |

---

## Architecture

```
User
 │
 ▼
CloudFront (CDN + HTTPS)
 │
 ▼
S3 Bucket (React static files)
 │                         │
 │                         ▼
 │               App Runner (FastAPI backend)
 │                         │
 │                ┌────────┴────────┐
 │                ▼                 ▼
 │           RDS PostgreSQL    Secrets Manager
 │           (database)        (API keys)
 ▼
ECR (Docker image registry)
```

---

## Resources

### Frontend — S3 + CloudFront

| Resource | Value |
|---|---|
| S3 Bucket | `resume-generator-frontend-415407325416` |
| S3 Website URL | http://resume-generator-frontend-415407325416.s3-website-us-east-1.amazonaws.com |
| CloudFront Distribution Domain | `d15qp9ffjs24sd.cloudfront.net` |
| Built with | `REACT_APP_API_URL=https://tjnyvgariy.us-east-1.awsapprunner.com npm run build` |

### Backend — App Runner

| Resource | Value |
|---|---|
| Service Name | `resume-generator-api` |
| Service ARN | `arn:aws:apprunner:us-east-1:415407325416:service/resume-generator-api/b8d79ba7061246499e0f1cd7961e297c` |
| Service URL | `tjnyvgariy.us-east-1.awsapprunner.com` |
| Port | 8000 |
| CPU | 0.25 vCPU |
| Memory | 0.5 GB |
| CORS_ORIGINS | `https://d15qp9ffjs24sd.cloudfront.net` |

### Container Registry — ECR

| Resource | Value |
|---|---|
| Repository Name | `resume-generator-backend` |
| Image URI | `415407325416.dkr.ecr.us-east-1.amazonaws.com/resume-generator-backend:latest` |
| Built with | `docker build --platform linux/amd64 -t resume-generator-backend .` |

### Database — RDS PostgreSQL

| Resource | Value |
|---|---|
| Instance ID | `resume-generator-db` |
| Endpoint | `resume-generator-db.cg5662c62ata.us-east-1.rds.amazonaws.com` |
| Port | 5432 |
| Engine | PostgreSQL 15 |
| Instance Class | db.t3.micro |
| Master Username | `resumeadmin` |
| Database Name | `postgres` |
| SSL | Required (`sslmode=require` appended automatically by `database.py`) |

### Secrets Manager

| Secret Name | ARN | Used For |
|---|---|---|
| `resume-generator/openai-api-key` | `arn:aws:secretsmanager:us-east-1:415407325416:secret:resume-generator/openai-api-key-600T41` | OpenAI API key |
| `resume-generator/database-url` | `arn:aws:secretsmanager:us-east-1:415407325416:secret:resume-generator/database-url-tzWZoG` | Full PostgreSQL connection string |

### IAM Roles

| Role | ARN | Purpose |
|---|---|---|
| `AppRunnerECRRole` | `arn:aws:iam::415407325416:role/AppRunnerECRRole` | Allows App Runner to pull images from ECR |
| `AppRunnerInstanceRole` | `arn:aws:iam::415407325416:role/AppRunnerInstanceRole` | Allows running containers to read Secrets Manager |

---

## Codebase

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the FastAPI backend image (must use `--platform linux/amd64` on Apple Silicon) |
| `.dockerignore` | Excludes frontend, venv, .env, uploads from the image |
| `database.py` | Handles DB URL resolution, SSL, and resilient `init_db()` startup |
| `main.py` | FastAPI app entry point — calls `init_db()` at startup |
| `AWS_DEPLOYMENT.md` | Full step-by-step deployment guide with CLI commands |

### Key environment variables (injected via Secrets Manager into App Runner)

| Variable | Source |
|---|---|
| `OPENAI_API_KEY` | Secrets Manager |
| `DATABASE_URL` | Secrets Manager |
| `CORS_ORIGINS` | App Runner environment variable (plaintext) |

---

## How to Update

### Backend code change
```bash
docker build --platform linux/amd64 -t resume-generator-backend .
docker tag resume-generator-backend:latest 415407325416.dkr.ecr.us-east-1.amazonaws.com/resume-generator-backend:latest
docker push 415407325416.dkr.ecr.us-east-1.amazonaws.com/resume-generator-backend:latest
aws apprunner start-deployment --service-arn arn:aws:apprunner:us-east-1:415407325416:service/resume-generator-api/b8d79ba7061246499e0f1cd7961e297c --region us-east-1
```

### Frontend code change
```bash
cd frontend
REACT_APP_API_URL=https://tjnyvgariy.us-east-1.awsapprunner.com npm run build
aws s3 sync build/ s3://resume-generator-frontend-415407325416 --delete
aws cloudfront create-invalidation --distribution-id <get from console> --paths "/*"
```

### Rotate OpenAI key
```bash
aws secretsmanager put-secret-value \
  --secret-id resume-generator/openai-api-key \
  --secret-string "sk-proj-new-key-here"
# Then redeploy App Runner so it picks up the new value
aws apprunner start-deployment --service-arn arn:aws:apprunner:us-east-1:415407325416:service/resume-generator-api/b8d79ba7061246499e0f1cd7961e297c --region us-east-1
```

---

## Known Issues & Decisions

- **Apple Silicon Mac**: Docker images must be built with `--platform linux/amd64` — App Runner runs on x86.
- **init_db resilience**: `database.py` wraps `init_db()` in try/except so the app starts even if the DB is briefly unreachable. Tables are created on first successful connection.
- **RDS public access**: The RDS instance is publicly accessible (port 5432 open to 0.0.0.0/0) for simplicity. In production, place App Runner in a VPC and restrict RDS access to that VPC.
- **Root user**: AWS CLI is configured with root credentials. Create an IAM user with least-privilege permissions for ongoing work.
