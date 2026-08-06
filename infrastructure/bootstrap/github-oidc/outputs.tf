output "github_actions_role_arn" {
  description = "IAM role assumed by GitHub Actions for HomePulse deployments."
  value       = aws_iam_role.github_actions_deployment.arn
}

output "github_oidc_provider_arn" {
  description = "GitHub Actions OIDC provider ARN."
  value       = aws_iam_openid_connect_provider.github.arn
}