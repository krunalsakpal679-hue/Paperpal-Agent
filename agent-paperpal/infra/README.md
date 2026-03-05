# infra/README.md
# Infrastructure Configuration

This directory contains infrastructure-as-code for deploying Agent Paperpal.

## Structure

```
infra/
├── docker/          # Docker build configs (handled by root docker-compose.yml)
├── k8s/             # Kubernetes manifests for production deployment
└── terraform/       # Terraform modules for cloud provisioning
```

## Production Deployment

Production deployment targets:
- AWS ECS / EKS for container orchestration
- RDS PostgreSQL for managed database
- ElastiCache Redis for managed caching
- S3 for file storage
- CloudFront for CDN
