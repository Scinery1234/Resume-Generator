# AWS Deployment Guide

Deploy the Resume Generator to AWS using:
- **App Runner** — backend (FastAPI)
- **RDS PostgreSQL** — database
- **S3 + CloudFront** — frontend (React)
- **Secrets Manager** — API keys

---

## Prerequisites

Install these tools locally before starting:

```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Docker (must be running)
docker --version

# Verify AWS CLI
aws --version
```

Configure your AWS credentials:

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region (e.g. us-east-1), output format (json)
```

Set a shell variable for your region — used throughout this guide:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

---

## Step 1 — Build & Push Docker Image to ECR

ECR is AWS's private container registry. App Runner pulls from it.

### Create the ECR repository

```bash
aws ecr create-repository \
  --repository-name resume-generator-backend \
  --region $AWS_REGION
```

### Authenticate Docker to ECR

```bash
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS \
    --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

### Build and push

```bash
# Build the image (from the project root where Dockerfile lives)
docker build -t resume-generator-backend .

# Tag it for ECR
docker tag resume-generator-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/resume-generator-backend:latest

# Push
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/resume-generator-backend:latest
```

You should see the image appear in the AWS Console under **ECR → Repositories**.

---

## Step 2 — Create RDS PostgreSQL Database

### Create the database (free-tier eligible)

```bash
aws rds create-db-instance \
  --db-instance-identifier resume-generator-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --master-username resumeadmin \
  --master-user-password "ChangeMe123!" \
  --allocated-storage 20 \
  --publicly-accessible \
  --backup-retention-period 7 \
  --region $AWS_REGION
```

This takes ~5 minutes. Check status:

```bash
aws rds describe-db-instances \
  --db-instance-identifier resume-generator-db \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text
```

Wait until it returns `available`.

### Get the connection endpoint

```bash
aws rds describe-db-instances \
  --db-instance-identifier resume-generator-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

Your `DATABASE_URL` will be:
```
postgresql://resumeadmin:ChangeMe123!@<endpoint>:5432/postgres
```

### Allow inbound connections

By default RDS blocks all traffic. Find the security group and open port 5432:

```bash
# Get the security group ID
SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier resume-generator-db \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

# Allow inbound PostgreSQL from anywhere (lock this down in production)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0
```

---

## Step 3 — Store Secrets in Secrets Manager

Never put secrets in environment variables as plain text when you can avoid it.
App Runner can read directly from Secrets Manager.

```bash
# Store OpenAI key
aws secretsmanager create-secret \
  --name resume-generator/openai-api-key \
  --secret-string "sk-your-actual-openai-key-here" \
  --region $AWS_REGION

# Store database URL
aws secretsmanager create-secret \
  --name resume-generator/database-url \
  --secret-string "postgresql://resumeadmin:ChangeMe123!@<your-rds-endpoint>:5432/postgres" \
  --region $AWS_REGION
```

Note the ARNs — you'll need them in the next step:

```bash
aws secretsmanager describe-secret \
  --secret-id resume-generator/openai-api-key \
  --query 'ARN' --output text

aws secretsmanager describe-secret \
  --secret-id resume-generator/database-url \
  --query 'ARN' --output text
```

---

## Step 4 — Deploy Backend with App Runner

### Create an IAM role for App Runner to access ECR and Secrets Manager

Save this as `apprunner-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "build.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

```bash
aws iam create-role \
  --role-name AppRunnerECRRole \
  --assume-role-policy-document file://apprunner-trust-policy.json

aws iam attach-role-policy \
  --role-name AppRunnerECRRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

aws iam attach-role-policy \
  --role-name AppRunnerECRRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite
```

### Deploy the App Runner service

Replace the ARN placeholders below with your actual values:

```bash
aws apprunner create-service \
  --service-name resume-generator-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/resume-generator-backend:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "CORS_ORIGINS": "https://your-cloudfront-domain.cloudfront.net"
        },
        "RuntimeEnvironmentSecrets": {
          "OPENAI_API_KEY": "arn:aws:secretsmanager:'$AWS_REGION':'$AWS_ACCOUNT_ID':secret:resume-generator/openai-api-key-XXXXXX",
          "DATABASE_URL": "arn:aws:secretsmanager:'$AWS_REGION':'$AWS_ACCOUNT_ID':secret:resume-generator/database-url-XXXXXX"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT_ID':role/AppRunnerECRRole"
    }
  }' \
  --instance-configuration '{"Cpu": "0.25 vCPU", "Memory": "0.5 GB"}' \
  --region $AWS_REGION
```

Check deployment status:

```bash
aws apprunner describe-service \
  --service-arn <service-arn-from-output-above> \
  --query 'Service.Status' --output text
```

Wait for `RUNNING`. Then get your backend URL:

```bash
aws apprunner describe-service \
  --service-arn <service-arn> \
  --query 'Service.ServiceUrl' --output text
```

Your API will be live at `https://<service-url>/docs`.

---

## Step 5 — Deploy Frontend to S3 + CloudFront

### Build the React app pointing at your App Runner URL

```bash
cd frontend
REACT_APP_API_URL=https://<your-app-runner-url> npm run build
```

### Create an S3 bucket

Bucket names must be globally unique:

```bash
BUCKET_NAME=resume-generator-frontend-$AWS_ACCOUNT_ID

aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION \
  --create-bucket-configuration LocationConstraint=$AWS_REGION

# Enable static website hosting
aws s3 website s3://$BUCKET_NAME \
  --index-document index.html \
  --error-document index.html
```

### Upload the build

```bash
aws s3 sync frontend/build/ s3://$BUCKET_NAME --delete
```

### Create a CloudFront distribution

```bash
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "resume-generator-'$(date +%s)'",
    "Origins": {
      "Quantity": 1,
      "Items": [{
        "Id": "S3Origin",
        "DomainName": "'$BUCKET_NAME'.s3-website-'$AWS_REGION'.amazonaws.com",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only"
        }
      }]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "S3Origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
      "Compress": true,
      "ForwardedValues": {
        "QueryString": false,
        "Cookies": {"Forward": "none"}
      },
      "TrustedSigners": {"Enabled": false, "Quantity": 0},
      "MinTTL": 0
    },
    "CustomErrorResponses": {
      "Quantity": 1,
      "Items": [{
        "ErrorCode": 404,
        "ResponsePagePath": "/index.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 0
      }]
    },
    "Comment": "Resume Generator Frontend",
    "Enabled": true
  }'
```

CloudFront takes ~10 minutes to deploy globally. Get your domain:

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[0].DomainName' \
  --output text
```

Your site is live at `https://<distribution>.cloudfront.net`.

---

## Step 6 — Wire Everything Together

### Update CORS on the backend

Go to **App Runner → your service → Configuration → Environment variables** and update:

```
CORS_ORIGINS=https://<your-cloudfront-domain>.cloudfront.net
```

Then redeploy (App Runner → Deploy).

### Verify the full stack

```bash
# Backend health check
curl https://<app-runner-url>/docs

# Check the database connected (look for 200, not 500)
curl https://<app-runner-url>/api/health
```

Open `https://<cloudfront-domain>.cloudfront.net` in a browser — you should see the landing page and be able to register/login.

---

## Updating After Code Changes

Each time you change the backend:

```bash
docker build -t resume-generator-backend .
docker tag resume-generator-backend:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/resume-generator-backend:latest
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/resume-generator-backend:latest

# Trigger a new App Runner deployment
aws apprunner start-deployment \
  --service-arn <your-service-arn> \
  --region $AWS_REGION
```

Each time you change the frontend:

```bash
cd frontend
REACT_APP_API_URL=https://<app-runner-url> npm run build
aws s3 sync frontend/build/ s3://$BUCKET_NAME --delete

# Invalidate CloudFront cache so users get the new version
aws cloudfront create-invalidation \
  --distribution-id <your-distribution-id> \
  --paths "/*"
```

---

## Cost Estimate (light usage)

| Service | Free Tier | After Free Tier |
|---|---|---|
| App Runner | 2M requests/mo free | ~$0.064/vCPU·hr |
| RDS t3.micro | 750 hrs/mo (12 months) | ~$15/mo |
| S3 | 5 GB free | ~$0.023/GB |
| CloudFront | 1 TB transfer free | ~$0.0085/GB |

**Total for learning/dev: effectively $0 in the first year.**

---

## Teardown (when done learning)

```bash
# Delete App Runner service
aws apprunner delete-service --service-arn <service-arn>

# Delete RDS (skip final snapshot for dev)
aws rds delete-db-instance \
  --db-instance-identifier resume-generator-db \
  --skip-final-snapshot

# Empty and delete S3 bucket
aws s3 rm s3://$BUCKET_NAME --recursive
aws s3api delete-bucket --bucket $BUCKET_NAME

# Disable CloudFront distribution first, then delete it
aws cloudfront get-distribution-config --id <dist-id>  # get ETag
aws cloudfront update-distribution --id <dist-id> ...  # set Enabled: false
aws cloudfront delete-distribution --id <dist-id> --if-match <ETag>

# Delete ECR repo
aws ecr delete-repository \
  --repository-name resume-generator-backend \
  --force
```
