data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid    = "AllowGitHubActionsProductionDeployment"
    effect = "Allow"

    actions = [
      "sts:AssumeRoleWithWebIdentity",
    ]

    principals {
      type = "Federated"

      identifiers = [
        aws_iam_openid_connect_provider.github.arn,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        var.github_oidc_subject,
      ]
    }
  }
}

resource "aws_iam_role" "github_actions_deployment" {
  name = "HomePulseGitHubActionsDeploymentRole"

  assume_role_policy = (
    data.aws_iam_policy_document.github_actions_assume_role.json
  )

  max_session_duration = 3600
}

data "aws_iam_policy_document" "terraform_state" {
  statement {
    sid    = "ListTerraformStateBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${var.terraform_state_bucket_name}",
    ]
  }

  statement {
    sid    = "ManageTerraformStateObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${var.terraform_state_bucket_name}/*",
    ]
  }
}

resource "aws_iam_role_policy" "terraform_state" {
  name = "HomePulseTerraformStatePolicy"
  role = aws_iam_role.github_actions_deployment.id

  policy = data.aws_iam_policy_document.terraform_state.json
}

data "aws_iam_policy_document" "homepulse_deployment" {
  statement {
    sid    = "ManageHomePulseCloudWatchAlarms"
    effect = "Allow"

    actions = [
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:TagResource",
      "cloudwatch:UntagResource",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:HomePulse-*",
    ]
  }

  statement {
    sid    = "ManageHomePulseCloudWatchDashboard"
    effect = "Allow"

    actions = [
      "cloudwatch:DeleteDashboards",
      "cloudwatch:GetDashboard",
      "cloudwatch:PutDashboard",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:cloudwatch::${data.aws_caller_identity.current.account_id}:dashboard/*",
    ]
  }

  statement {
    sid    = "ManageHomePulseDynamoDB"
    effect = "Allow"

    # DynamoDB table lifecycle
    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DeleteTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:DescribeTable",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:ListTagsOfResource",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
      "dynamodb:UpdateContinuousBackups",
      "dynamodb:UpdateTable",
      "dynamodb:UpdateTimeToLive",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/homepulse-*",
    ]
  }

  statement {
    sid    = "ManageHomePulseIot"
    effect = "Allow"

    # IoT topic rule
    actions = [
      "iot:CreateTopicRule",
      "iot:DeleteTopicRule",
      "iot:DisableTopicRule",
      "iot:EnableTopicRule",
      "iot:GetTopicRule",
      "iot:ListTagsForResource",
      "iot:ListTopicRules",
      "iot:ReplaceTopicRule",
      "iot:TagResource",
      "iot:UntagResource",
    ]

    resources = ["*"]
  }

  statement {
    sid    = "ManageHomePulseLambda"
    effect = "Allow"

    # Lambda lifecycle
    actions = [
      "lambda:AddPermission",
      "lambda:CreateFunction",
      "lambda:DeleteFunction",
      "lambda:DeleteFunctionEventInvokeConfig",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionEventInvokeConfig",
      "lambda:GetPolicy",
      "lambda:ListTags",
      "lambda:ListVersionsByFunction",
      "lambda:PutFunctionEventInvokeConfig",
      "lambda:RemovePermission",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:homepulse-*",
    ]
  }


  statement {
    sid    = "ManageHomePulseSns"
    effect = "Allow"

    # SNS topic
    actions = [
      "sns:CreateTopic",
      "sns:DeleteTopic",
      "sns:GetTopicAttributes",
      "sns:ListTagsForResource",
      "sns:SetTopicAttributes",
      "sns:TagResource",
      "sns:UntagResource",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:homepulse-*",
    ]
  }

  statement {
    sid    = "ManageHomePulseSqs"
    effect = "Allow"

    # SQS queue
    actions = [
      "sqs:CreateQueue",
      "sqs:DeleteQueue",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListQueueTags",
      "sqs:SetQueueAttributes",
      "sqs:TagQueue",
      "sqs:UntagQueue",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:homepulse-*",
    ]
  }

  statement {
    sid    = "ManageHomePulseIamResources"
    effect = "Allow"

    actions = [
      "iam:AttachRolePolicy",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:CreateRole",
      "iam:DeletePolicy",
      "iam:DeletePolicyVersion",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:DetachRolePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListPolicyVersions",
      "iam:ListRolePolicies",
      "iam:PutRolePolicy",
      "iam:TagPolicy",
      "iam:TagRole",
      "iam:UntagPolicy",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:UpdateRole",
      "iam:UpdateRoleDescription",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role/homepulse-*",
      "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role/service-role/homepulse-*",
      "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:policy/HomePulse*",
    ]
  }

  statement {
    sid    = "PassHomePulseLambdaRole"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role/homepulse-*",
      "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role/service-role/homepulse-*",
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"

      values = [
        "lambda.amazonaws.com",
      ]
    }
  }

  statement {
    sid    = "ReadAccountMetadata"
    effect = "Allow"

    actions = [
      "iam:GetOpenIDConnectProvider",
      "iam:ListOpenIDConnectProviders",
      "sts:GetCallerIdentity",
    ]

    resources = [
      "*",
    ]
  }
}

resource "aws_iam_role_policy" "homepulse_deployment" {
  name = "HomePulseInfrastructureDeploymentPolicy"
  role = aws_iam_role.github_actions_deployment.id

  policy = data.aws_iam_policy_document.homepulse_deployment.json
}