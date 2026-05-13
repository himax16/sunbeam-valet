#!/bin/bash

# install-deps.sh - Install dependencies for Mattermost deployment

set -e  # Exit on any error

echo "=== Installing dependencies ==="

# Check if snap is available
if ! command -v snap &> /dev/null; then
    echo "Snap is not available. Installing snapd..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y snapd
    else
        echo "ERROR: Unsupported package manager. Please install snapd manually."
        exit 1
    fi
fi

# Install k8s via snap (Canonical K8s)
echo "Installing k8s..."
sudo snap install k8s --classic

# Install terraform via snap if available, otherwise use other methods
echo "Installing terraform..."
if sudo snap info terraform &> /dev/null; then
    sudo snap install terraform --classic
else
    echo "Terraform snap not available. Installing via other methods..."
    
    # Try to install terraform using tfenv (Terraform version manager)
    if command -v git &> /dev/null && command -v bash &> /dev/null; then
        if [ ! -d "$HOME/.tfenv" ]; then
            echo "Installing tfenv..."
            git clone https://github.com/tfutils/tfenv.git ~/.tfenv
            echo 'export PATH="$HOME/.tfenv/bin:$PATH"' >> ~/.bashrc
            export PATH="$HOME/.tfenv/bin:$PATH"
        fi
        
        # Install latest Terraform version
        ~/.tfenv/bin/tfenv install latest
        ~/.tfenv/bin/tfenv use latest
    else
        echo "WARNING: Could not install terraform automatically."
        echo "Please install Terraform v1.6+ manually from https://www.terraform.io/downloads.html"
    fi
fi

# Install terragrunt
echo "Installing terragrunt..."
# Try snap first
if sudo snap info terragrunt &> /dev/null; then
    sudo snap install terragrunt --classic
else
    echo "Terragrunt snap not available. Installing via other methods..."
    
    # Install via package manager if available
    if command -v apt-get &> /dev/null; then
        # Try to install via apt (Ubuntu/Debian)
        if sudo apt-get update && sudo apt-get install -y terragrunt; then
            echo "Terragrunt installed via apt"
        else
            echo "WARNING: Could not install terragrunt via apt"
            echo "Please install Terragrunt manually from https://terragrunt.gruntwork.io/docs/getting-started/install/"
        fi
    elif command -v yum &> /dev/null; then
        # Try to install via yum (RHEL/CentOS)
        if sudo yum install -y terragrunt; then
            echo "Terragrunt installed via yum"
        else
            echo "WARNING: Could not install terragrunt via yum"
            echo "Please install Terragrunt manually from https://terragrunt.gruntwork.io/docs/getting-started/install/"
        fi
    else
        echo "WARNING: Could not install terragrunt automatically"
        echo "Please install Terragrunt manually from https://terragrunt.gruntwork.io/docs/getting-started/install/"
    fi
fi

# Install Juju if not already installed
echo "Installing Juju..."
if ! command -v juju &> /dev/null; then
    sudo snap install juju --classic
else
    echo "Juju already installed"
fi

echo ""
echo "=== Installation Summary ==="
echo "k8s: $(k8s --version 2>/dev/null || echo 'not installed properly')"
echo "Terraform: $(terraform version 2>/dev/null | head -n1 || echo 'not installed properly')"
echo "Terragrunt: $(terragrunt --version 2>/dev/null | head -n1 || echo 'not installed properly')"
echo "Juju: $(juju version 2>/dev/null | head -n1 || echo 'not installed properly')"
echo "kubectl: $(k8s kubectl version --client 2>/dev/null | head -n1 || echo 'not installed properly')"

echo ""
echo "After completing these steps, you can run the deployment with:"
echo "./deploy.sh"
