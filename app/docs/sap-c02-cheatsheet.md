# SAP-C02 Quick Reference

## IAM vs SCP
- IAM policies control what an identity (user/role) can do within an account.
- SCPs (Service Control Policies) are applied at the AWS Organizations level and set the maximum permissions available to accounts in an OU. They do not grant permissions — they only restrict them.
- Use SCPs to enforce guardrails across all accounts (e.g., deny leaving the organization, deny disabling CloudTrail).
- Use IAM policies to grant specific permissions to users and roles within an account.

## VPC
- A VPC spans all AZs in a region. Subnets are tied to a single AZ.
- Internet Gateway (IGW): enables internet access for public subnets.
- NAT Gateway: lets private subnet instances initiate outbound internet connections without being directly reachable.
- VPC Peering: connects two VPCs; non-transitive (A-B and B-C does not mean A-C).
- Transit Gateway: hub-and-spoke model; supports transitive routing between VPCs and on-prem.

## Storage
- S3: object storage, 11 nines durability. Use lifecycle policies to move data to cheaper tiers.
- EBS: block storage, attached to a single EC2 instance (except Multi-Attach io1/io2).
- EFS: managed NFS, can be mounted by many EC2 instances across AZs.
- FSx for Windows: SMB file shares for Windows workloads.
- FSx for Lustre: high-performance parallel filesystem, integrates with S3.

## Compute
- EC2 Reserved Instances: 1 or 3 year commitment, significant discount over On-Demand.
- Spot Instances: up to 90% cheaper, can be interrupted with 2-minute notice.
- Savings Plans: flexible commitment ($/hr), applies across EC2, Fargate, Lambda.
- Auto Scaling: scale EC2 or ECS tasks based on metrics; supports target tracking, step scaling, scheduled scaling.

## Databases
- RDS Multi-AZ: synchronous standby for high availability; automatic failover.
- RDS Read Replicas: asynchronous replication for read scaling; can be promoted.
- Aurora: MySQL/PostgreSQL compatible, storage auto-scales, up to 15 read replicas.
- DynamoDB: serverless NoSQL; single-digit millisecond latency; use DAX for caching.
- ElastiCache: Redis or Memcached for in-memory caching to reduce DB load.

## Security
- KMS: managed encryption keys; used by S3, EBS, RDS, etc.
- Secrets Manager: stores and rotates secrets (DB passwords, API keys).
- Parameter Store: lightweight key-value store; free tier available; no auto-rotation.
- GuardDuty: threat detection; analyzes CloudTrail, VPC Flow Logs, DNS logs.
- Security Hub: aggregates findings from GuardDuty, Inspector, Macie, etc.
- Macie: discovers and protects sensitive data (PII) in S3.

## Migration
- AWS DMS: migrates databases to AWS; supports homogeneous and heterogeneous migrations.
- AWS SCT: Schema Conversion Tool; used with DMS for heterogeneous migrations.
- Snowball Edge: petabyte-scale data transfer device; compute capabilities on the device.
- DataSync: online data transfer from on-prem NFS/SMB/HDFS to S3/EFS/FSx.

## Networking
- Direct Connect: dedicated private connection from on-prem to AWS; more consistent than VPN.
- Site-to-Site VPN: encrypted tunnel over the internet; quick to set up.
- Route 53: DNS service; supports failover, weighted, latency-based, geolocation routing.
- CloudFront: CDN; caches content at edge locations; integrates with WAF and Shield.
- Global Accelerator: routes traffic through AWS backbone; improves availability and performance.
