resource "aws_cloudwatch_dashboard" "network" {
  dashboard_name = "HomePulse-Network-Dashboard"

  dashboard_body = file(
    "${path.module}/../../dashboard/homepulse-dashboard.json"
  )
}

resource "aws_cloudwatch_metric_alarm" "agent_missing" {
  alarm_name        = "HomePulse-Agent-Telemetry-Missing"
  alarm_description = <<-EOT
    Triggers when HomePulse telemetry is absent for a complete
    five-minute period. Possible causes include the monitoring agent
    stopping, the Mac sleeping, a network outage, or an ingestion failure.
  EOT

  namespace   = "HomePulse"
  metric_name = "InternetReachable"

  dimensions = {
    DeviceId = var.device_id
  }

  comparison_operator = "LessThanThreshold"
  threshold           = 0

  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1

  treat_missing_data = "breaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "internet_unavailable" {
  alarm_name        = "HomePulse-Internet-Unavailable"
  alarm_description = <<-EOT
    Triggers when the HomePulse agent explicitly reports that
    the internet is unavailable during a five-minute period.
  EOT

  namespace   = "HomePulse"
  metric_name = "InternetReachable"

  dimensions = {
    DeviceId = var.device_id
  }

  comparison_operator = "LessThanThreshold"
  threshold           = 1

  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1

  treat_missing_data = "missing"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "miwifi_unavailable" {
  alarm_name        = "HomePulse-MiWifi-Unavailable"
  alarm_description = <<-EOT
    Triggers when the Xiaomi access point is reported unavailable
    during a five-minute period.
  EOT

  namespace   = "HomePulse"
  metric_name = "MiWifiReachable"

  dimensions = {
    DeviceId = var.device_id
  }

  comparison_operator = "LessThanThreshold"
  threshold           = 1

  statistic           = "Minimum"
  period              = 300
  evaluation_periods  = 1
  datapoints_to_alarm = 1

  treat_missing_data = "missing"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}