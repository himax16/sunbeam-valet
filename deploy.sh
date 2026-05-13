#!/bin/bash

# Deployment script for Mattermost on Canonical K8s
ACTION=${1:-apply}
echo "=== Mattermost Deployment ==="

# Step 1: Register K8s cluster with Juju
echo "Step 1: Registering K8s cluster with Juju..."
cd deployments/k8s-cluster
terragrunt init
terragrunt $ACTION -auto-approve

# Check if registration was successful
if [ $? -ne 0 ]; then
    echo "ERROR: K8s cluster registration failed"
    exit 1
fi

echo "K8s cluster registered successfully"

# Step 2: Verify cluster registration
echo "Step 2: Verifying cluster registration..."
juju clouds | grep canonical
if [ $? -ne 0 ]; then
    echo "ERROR: Cluster not registered in Juju"
    exit 1
fi

sudo k8s kubectl get nodes
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot get Kubernetes nodes"
    exit 1
fi

echo "Cluster verified successfully"

# Step 3: Create TLS secret (if using HTTPS)
echo "Step 3: Creating TLS secret..."
sudo k8s kubectl create secret tls mattermost-tls \
  --cert=path/to/tls.crt --key=path/to/tls.key \
  -n mattermost 2>/dev/null || echo "Namespace not ready, will create secret later"

echo "TLS secret creation attempted"

# Step 4: Deploy Mattermost
echo "Step 4: Deploying Mattermost..."
cd ../mattermost
terragrunt init
terragrunt plan
terragrunt $ACTION -auto-approve

# Check if deployment was successful
if [ $? -ne 0 ]; then
    echo "ERROR: Mattermost deployment failed"
    exit 1
fi

echo "Mattermost deployed successfully"

# Step 5: Post-deploy - grant initial admin user
echo "Step 5: Granting initial admin user..."
juju run mattermost/0 grant-admin-role user=admin

echo "Initial admin user granted"

echo "=== Deployment Complete ==="
echo "To verify deployment, run: juju status --model mattermost --watch 5s"
