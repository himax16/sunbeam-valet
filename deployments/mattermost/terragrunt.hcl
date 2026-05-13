terraform {
  source = "."
}

inputs = {
  k8s_cloud_name  = "canonical"
  site_url        = "https://chat.example.com"
  tls_secret_name = "mattermost-tls"
  s3_enabled      = true
  s3_bucket       = "mattermost-files"
  s3_endpoint     = "https://s3.example.com"
  s3_region       = "us-east-1"
}
