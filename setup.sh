#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Task Management API - Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print step
print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ Error: $1${NC}"
    exit 1
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."

if ! command -v python3.12 &> /dev/null; then
    print_error "Python 3.12 is not installed. Please install Python 3.12+"
fi
print_success "Python 3.12 found"

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js 18+"
fi
print_success "Node.js found ($(node --version))"

# Setup Python virtual environment
print_step "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_step "Activating virtual environment..."
source venv/bin/activate
print_success "Virtual environment activated"

# Install Python dependencies
print_step "Installing Python dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
pip install -r requirements-dev.txt > /dev/null 2>&1
print_success "Python dependencies installed"

# Setup CDK
print_step "Setting up AWS CDK..."
cd cdk
if [ ! -d "node_modules" ]; then
    npm install > /dev/null 2>&1
    print_success "CDK dependencies installed"
else
    print_warning "CDK dependencies already installed"
fi

# Build TypeScript
print_step "Building CDK TypeScript..."
npm run build > /dev/null 2>&1
print_success "CDK TypeScript compiled"

cd ..

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Setup Complete! ✓${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "To activate the virtual environment, run:"
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo ""
echo -e "Available commands:"
echo -e "  ${GREEN}./validate.sh${NC}     - Run tests and validate CDK"
echo -e "  ${GREEN}pytest -v${NC}         - Run unit tests"
echo -e "  ${GREEN}cd cdk && npm run cdk synth${NC} - Validate CDK stack"
echo ""
