output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "nat_gateway_ip" {
  value       = aws_eip.nat.public_ip
  description = "NAT Gateway public IP — whitelist this in external services if needed"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "docs_bucket_name" {
  value = aws_s3_bucket.docs.bucket
}

output "alb_dns_name" {
  value       = aws_lb.app.dns_name
  description = "Hit this URL to reach the app: http://<alb_dns_name>/ask"
}
