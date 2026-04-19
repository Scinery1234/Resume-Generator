# CI/CD Pipeline - Resume Generator

## Live Deployment

| Service | URL |
|---|---|
| Frontend | https://d15qp9ffjs24sd.cloudfront.net |
| Backend API | https://tjnyvgariy.us-east-1.awsapprunner.com |
| API Docs | https://tjnyvgariy.us-east-1.awsapprunner.com/docs |

## 1. Overview

This project uses GitHub Actions to automate three distinct processes:

| Workflow file | Purpose | Trigger |
|---|---|---|
| ci.yml | Install dependencies, run all tests, validate Docker build | Every push / pull request |
| cd.yml | Build Docker image, push to ECR, deploy App Runner + S3/CloudFront | CI passes on main |
| health-check.yml | Probe live production endpoints and store health reports | Every 6 hours (cron) |

The pipeline enforces a strict gate: code cannot be deployed unless CI tests pass first. This is implemented using the workflow_run trigger in cd.yml, which creates a hard dependency between the two workflows.

## 2. Tools and Systems Chosen

### GitHub Actions

GitHub Actions is the CI/CD tool for this application. It is an automated workflow tool provided by GitHub that performs the actions defined in YAML files in cloud-based virtual machines called runners whenever specific events happen.

- Continuous Integration: With every push, GitHub Actions pulls the code and performs actions like installing the dependencies, running tests using pytest and Jest, building Docker image and checking if there are any errors in the process. Any failure in this pipeline will ensure that the pull request cannot go through until the error is fixed.
- Continuous Deployment: If the pipeline runs successfully in the master branch, GitHub Actions automatically creates a production Docker image tagged by commit SHAs, pushed to Amazon ECR, and a new App Runner deployment is kicked off. GitHub Actions also builds the React frontend and uploads it to S3.
- Scheduled monitoring: Every six hours a cron job fires off to monitor the live backend and frontend, writing structured output logs as an artifact file available for download.

### Amazon ECR

Amazon ECR is the Amazon-managed private registry for hosting Docker images. The CI/CD workflow creates a FastAPI backend Docker image and pushes it to Amazon ECR. App Runner pulls this image to deploy the web app.

### AWS App Runner

App Runner is a fully managed AWS service that runs containerised web applications without requiring server or cluster management. It pulls images from ECR, handles scaling, and exposes an HTTPS endpoint automatically.

### Amazon S3 and CloudFront

The React frontend is a static build that is synced to an S3 bucket. CloudFront distributes these files from edge locations globally, providing HTTPS and low-latency delivery.

### Amazon RDS PostgreSQL

Backend persistently stores user accounts and resumes using a managed PostgreSQL database on RDS. DATABASE_URL gets stored in AWS Secrets Manager and injected into App Runner as an environment variable, never committed to the repository.

### AWS Secrets Manager

Securely stores sensitive credentials such as the OpenAI API key and database URL. App Runner retrieves secrets directly from Secrets Manager during execution, ensuring secrets never appear in source code or Docker images.

### GitHub Encrypted Secrets

All required AWS credentials and other parameters are defined as secrets in the GitHub repository and injected into the running workflow as environment variables by the runner.

## 3. Why GitHub Actions Over Alternatives

| Criterion | GitHub Actions | Jenkins | CircleCI | GitLab CI/CD |
|---|---|---|---|---|
| Setup effort | Zero - built into GitHub | High - requires a self-hosted server | Low - cloud-hosted | Low, but requires migrating to GitLab |
| Free tier | 2000 min/month on public repos | Free software, but you pay for the server | 6000 build min/month free | 400 CI/CD min/month |
| YAML syntax | Native, well-documented | Groovy DSL - steeper learning curve | CircleCI YAML - similar to GHA | GitLab CI YAML - similar to GHA |
| Marketplace | 20000+ pre-built actions | Plugin ecosystem 1800+ plugins | Orbs fewer than GHA | Limited compared to GHA |
| GitHub integration | Native - PR status checks, branch protection | Requires webhook configuration | Requires OAuth app setup | N/A different platform |
| Secrets management | Repository/Environment Secrets built-in | Credentials plugin | Environment variables in UI | CI/CD Variables |
| Composite actions DRY | First-class composite actions | Shared libraries | Orbs | Templates |
| Scheduled triggers | Native cron | Native | Scheduled pipelines | Scheduled pipelines |
| Dependent workflows | workflow_run trigger | Pipeline triggers | Workflow triggers | needs + triggers |
| Self-hosted runners | Supported | Core feature | Supported | Supported |

There were three main reasons for opting for GitHub Actions:

1. Zero infrastructure overhead. Jenkins needs a server to be set up and managed. Using App Runner for this project was specifically intended to avoid server management. Opting for Jenkins would defeat this purpose.
2. Native GitHub integration. This repository exists on GitHub and GitHub Actions has inbuilt compatibility with pull requests, branch protections, and the GitHub Environments functionality without anything extra.
3. AWS ecosystem support. The aws-actions organisation at GitHub Marketplace offers officially supported actions for ECR login and credential configuration. They have been tested thoroughly by the AWS team.

CircleCI would have been a strong secondary option since its YAML format is almost identical to GitHub Actions. But CircleCI would require setting up a separate account with GitHub OAuth integration.

## 4. Pipeline Architecture

The pipeline runs in three stages. First, CI runs on every push testing backend with pytest, frontend with Jest, and validating the Docker build. Second, when CI passes on main, CD fires automatically building and pushing a Docker image to ECR, deploying to App Runner, building the React app and syncing to S3, then invalidating CloudFront cache. Third, every 6 hours the health check workflow probes the live backend and frontend endpoints and stores a timestamped report as an artifact.

The workflow_run trigger in cd.yml creates a hard dependency: CD only fires when CI completes successfully on main. This means broken code can never be deployed automatically.

### Trigger flow
Developer --> git push origin main --> GitHub
GitHub --> CI runner: Trigger ci.yml
CI runner: setup-python-env (composite action)
CI runner: pytest tests - JUnit XML + log
CI runner: setup-node-env (composite action)
CI runner: npm test - Jest JSON + log
CI runner: docker build - health check
CI runner --> GitHub: Upload artifacts 30-day retention
CI runner --> GitHub: CI passed
GitHub --> CD runner: Trigger cd.yml workflow_run completed
CD runner: Gate - verify CI conclusion == success
CD runner: configure-aws-credentials
CD runner: amazon-ecr-login
CD runner: docker build --tag sha + latest
CD runner --> ECR: docker push sha revision tag
CD runner --> ECR: docker push latest convenience tag
CD runner --> App Runner: aws apprunner start-deployment
App Runner: Pull latest from ECR replace revision
CD runner: npm run build REACT_APP_API_URL injected
CD runner --> S3: aws s3 sync build with cache headers
CD runner --> S3: create-invalidation CloudFront
CD runner --> GitHub: Upload deployment record 365-day retention


## 5. CI Workflow - Deep Dive

File: .github/workflows/ci.yml

### Triggers

The CI workflow uses a push trigger on all branches and a pull_request trigger on main with a paths filter. The paths filter makes this a complex trigger - GitHub only fires the workflow when relevant source files change. Documentation-only commits do not waste CI minutes.

### Job: test-backend

Runs full pytest against a temporary SQLite DB. Tests calling OpenAI API are replaced by MagicMock so no real API key is needed.

| Variable | CI Value | Purpose |
|---|---|---|
| DATABASE_URL | sqlite:///./test_temp.db | Lightweight in-process DB - no Postgres needed |
| OPENAI_API_KEY | sk-test-not-real-ci-key | Placeholder - tests mock all OpenAI calls |
| CORS_ORIGINS | http://localhost:3000 | Default allowed origin |

Output files uploaded as artifacts with 30-day retention: backend-test.log and backend-junit.xml.

### Job: test-frontend

Runs Jest with CI=true which treats warnings as errors and disables watch mode. --forceExit prevents Jest from hanging after tests complete. Output files: frontend-test.log and frontend-jest.json.

### Job: validate-docker

Builds the Docker image with --platform linux/amd64 (required because App Runner runs x86-64). Boots a container and checks /health returns HTTP 200. This catches Docker-specific failures that tests alone would miss.

### Job: ci-summary

Downloads all test artifacts, combines them into a single markdown report, and posts it to GitHub step summary. Also exports the ci.yml workflow file itself as a downloadable artifact.

## 6. CD Workflow - Deep Dive

File: .github/workflows/cd.yml

### Complex Trigger 1 - Dependent workflow

The workflow_run trigger fires when the CI workflow completes on main. The gate job checks the CI conclusion equals success before allowing deployment. This creates a hard dependency chain where broken code cannot be deployed automatically.

### Complex Trigger 2 - Manual dispatch with conditions

workflow_dispatch with a skip_frontend boolean input allows deploying only the backend when set to true. This is a complex trigger because its behaviour changes based on input conditions.

### Job: deploy-backend

1. configure-aws-credentials - injects AWS credentials from GitHub Secrets as environment variables.
2. amazon-ecr-login - authenticates Docker to ECR using a short-lived token valid 12 hours.
3. docker build - builds the image with two tags: the commit SHA as an immutable revision tag and latest as a mutable convenience tag.
4. docker push - pushes both tags. The SHA tag permanently records this deployment revision in ECR.
5. aws apprunner start-deployment - triggers App Runner to pull the new latest image.
6. Polling loop - checks describe-service every 30 seconds until status is RUNNING.

### Job: deploy-frontend

Waits for deploy-backend to complete. Builds React with REACT_APP_API_URL injected from GitHub Secrets. Syncs to S3 with two passes: hashed assets get 1-year cache, index.html gets no-cache. Invalidates CloudFront after sync.

### Job: record-deployment

Creates a deployment.json artifact containing commit SHA, run ID, actor, timestamp, and component statuses. Retained for 365 days.

## 7. Health Check Workflow - Deep Dive

File: .github/workflows/health-check.yml

Runs on a cron schedule every 6 hours and also supports manual dispatch with a verbose flag for extended diagnostics. The cron trigger is complex because it fires independently of any user action or code change.

| Check | URL | Success condition |
|---|---|---|
| Backend API | REACT_APP_API_URL/health | HTTP 200 |
| Frontend CDN | https://d15qp9ffjs24sd.cloudfront.net | HTTP 200 |
| Extended endpoints | /, /health, /api/templates | HTTP 200 |

Results are saved as timestamped markdown reports uploaded as artifacts with 30-day retention.

## 8. DRY - Composite Actions

Composite actions in .github/actions/ prevent duplication of setup steps across workflow files.

### setup-python-env

Used by ci.yml test-backend and cd.yml deploy-backend. Handles checkout, Python 3.11 setup with pip caching, and pip install. Without this, the same four steps would be duplicated in every job needing Python.

### setup-node-env

Used by ci.yml test-frontend and cd.yml deploy-frontend. Handles checkout, Node 18 setup with npm caching, and npm ci. Uses npm ci instead of npm install because it reads package-lock.json exactly for reproducible installs and fails if the lockfile is out of sync.

## 9. Secrets and Environment Configuration

| Secret name | Value | Used by |
|---|---|---|
| AWS_ACCESS_KEY_ID | IAM access key ID | cd.yml, health-check.yml |
| AWS_SECRET_ACCESS_KEY | IAM secret access key | cd.yml, health-check.yml |
| AWS_REGION | us-east-1 | cd.yml |
| ECR_REPOSITORY | resume-generator-backend | cd.yml |
| APP_RUNNER_SERVICE_ARN | arn:aws:apprunner:us-east-1:415407325416:service/... | cd.yml |
| S3_BUCKET | resume-generator-frontend-415407325416 | cd.yml |
| CLOUDFRONT_DISTRIBUTION_ID | Your distribution ID | cd.yml |
| REACT_APP_API_URL | https://tjnyvgariy.us-east-1.awsapprunner.com | cd.yml, health-check.yml |

Services are configured differently in CI vs production:

| Variable | CI value | Production value |
|---|---|---|
| DATABASE_URL | sqlite:///./test_temp.db | PostgreSQL via Secrets Manager |
| OPENAI_API_KEY | sk-test-not-real-ci-key | Real key via Secrets Manager |
| CORS_ORIGINS | http://localhost:3000 | https://d15qp9ffjs24sd.cloudfront.net |

## 10. Services and Technologies - Full Reference

### GitHub Actions runner

Each job runs on a fresh Ubuntu 22.04 VM from GitHub with Docker, Python, Node.js, AWS CLI, and curl pre-installed. The VM is discarded after the job completes so there is no persistent state between runs.

### Amazon ECR

ECR stores Docker images as immutable layers identified by SHA-256 digest. Images can be tagged with labels like latest or a commit SHA. Every pushed image is retained indefinitely.

| Registry | Cost | Integration | Private |
|---|---|---|---|
| Amazon ECR | $0.10/GB/month | Native with App Runner, ECS, EKS | Yes |
| Docker Hub | Free public, $5/month private | Universal | Yes paid |
| GitHub Container Registry | Free for public | Native with GitHub Actions | Yes |

ECR was chosen because App Runner native deployment only works with ECR.

### AWS App Runner

App Runner abstracts EC2 instances, load balancers, auto-scaling, and SSL certificates. You provide a Docker image and App Runner handles the rest.

| Platform | Management overhead | Cold start | Cost |
|---|---|---|---|
| App Runner | Minimal - fully managed | 10-15s first request | $0.064/vCPU-hour |
| EC2 | High - OS, patches, scaling | None | From $0.008/hour |
| ECS Fargate | Medium - cluster config | 30s | $0.04/vCPU-hour |
| Render | Minimal | 30s free tier | Free to $7/month |

### Amazon S3 and CloudFront

React produces static files served without a server. S3 stores them at $0.023/GB/month and CloudFront distributes from 400+ edge locations.

| Platform | Global CDN | Custom domain | Cost |
|---|---|---|---|
| S3 + CloudFront | Yes | Yes | $0.01-0.05/GB |
| Vercel | Yes | Yes | Free to $20/month |
| Netlify | Yes | Yes | Free to $19/month |
| GitHub Pages | Partial | Yes | Free |

### Amazon RDS PostgreSQL

Managed PostgreSQL with automated backups and Multi-AZ failover. CI uses SQLite to avoid requiring network access to a real database.

### AWS Secrets Manager

Stores the OpenAI API key and DATABASE_URL. App Runner reads from Secrets Manager at startup so secrets are never in the Docker image or repository.

| Option | Rotation support | Audit log | Cost |
|---|---|---|---|
| Secrets Manager | Automatic | CloudTrail | $0.40/secret/month |
| SSM Parameter Store | Manual | CloudTrail | Free standard |
| GitHub Secrets | No | Limited | Free |
| .env file | No | No | Free but dangerous |

## 11. Deployment Revisions and Rollback

Every deployment pushes two tags to ECR: latest for App Runner to pull, and the commit SHA as an immutable revision record. To roll back:

```bash
git log --oneline

aws ecr batch-get-image \
  --repository-name resume-generator-backend \
  --image-ids imageTag=<previous-sha> \
  --query 'images[].imageManifest' \
  --output text \
  | aws ecr put-image \
    --repository-name resume-generator-backend \
    --image-tag latest \
    --image-manifest file:///dev/stdin

aws apprunner start-deployment \
  --service-arn arn:aws:apprunner:us-east-1:415407325416:service/resume-generator-api/b8d79ba7061246499e0f1cd7961e297c
```

Deployment records retained for 365 days provide the SHA, actor, timestamp, and component status for every past deployment.

## 12. Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Click Settings then Secrets and variables then Actions
3. Click New repository secret for each entry below:
AWS_ACCESS_KEY_ID Your IAM access key AWS_SECRET_ACCESS_KEY Your IAM secret key AWS_REGION us-east-1 ECR_REPOSITORY resume-generator-backend APP_RUNNER_SERVICE_ARN arn:aws:apprunner:us-east-1:415407325416:service/resume-generator-api/b8d79ba7061246499e0f1cd7961e297c S3_BUCKET resume-generator-frontend-415407325416 CLOUDFRONT_DISTRIBUTION_ID get from aws cloudfront list-distributions REACT_APP_API_URL https://tjnyvgariy.us-east-1.awsapprunner.com


Then create a GitHub Environment named production under Settings then Environments then New environment.

The first automated deployment will trigger as soon as you push to main and CI passes.
