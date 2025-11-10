#!/bin/bash

# Quick Start Script for vLLM Benchmarking on MeluXina
# This script automates the setup and execution of vLLM benchmarks

set -e

echo "================================================"
echo "vLLM Benchmarking Quick Start"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "__main__.py" ]; then
    echo "Error: Please run this script from the 'our' directory"
    exit 1
fi

# Step 1: Load modules
echo "Step 1: Loading MeluXina modules..."
module load env/release/2024.1
module load Apptainer/1.3.6-GCCcore-13.3.0
echo "✓ Modules loaded"
echo ""

# Step 2: Check environment
echo "Step 2: Checking environment..."
if [ ! -f ".env" ]; then
    echo "⚠ Warning: .env file not found!"
    echo "Creating .env from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ""
        echo "Please edit .env file with your SLURM account details:"
        echo "  nano .env"
        echo ""
        echo "Then run this script again."
        exit 1
    else
        echo "Error: .env.example not found!"
        exit 1
    fi
fi
echo "✓ Environment configured"
echo ""

# Step 3: Create necessary directories
echo "Step 3: Creating directories..."
mkdir -p logs
mkdir -p results
mkdir -p scripts
echo "✓ Directories created"
echo ""

# Step 4: Verify modules are working
echo "Step 4: Verifying installation..."
if ! command -v python &> /dev/null; then
    echo "Error: Python not found"
    exit 1
fi

python -m server list > /dev/null 2>&1 || {
    echo "Error: Server module not working. Check installation."
    exit 1
}

python -m client list > /dev/null 2>&1 || {
    echo "Error: Client module not working. Check installation."
    exit 1
}
echo "✓ Modules verified"
echo ""

# Step 5: Start vLLM server
echo "Step 5: Starting vLLM server..."
echo "Submitting server job..."
SERVER_OUTPUT=$(python -m server run --recipe vllm-server 2>&1)
echo "$SERVER_OUTPUT"

# Extract job ID from SLURM output
# The server manager prints the SLURM job ID
JOB_ID=$(echo "$SERVER_OUTPUT" | grep -oP 'Submitted batch job \K\d+' || echo "")

if [ -z "$JOB_ID" ]; then
    # Try to find it from squeue
    sleep 2
    JOB_ID=$(squeue -u $USER -n vllm-server -h -o "%i" | head -1)
fi

if [ -z "$JOB_ID" ]; then
    echo "⚠ Could not determine job ID. Check manually with: squeue -u \$USER"
    JOB_ID="UNKNOWN"
else
    echo "✓ Server job submitted: Job ID $JOB_ID"
fi
echo ""

# Step 6: Wait for server to start
echo "Step 6: Waiting for server to start..."
echo "This may take a few minutes (especially first time for container pull)..."

if [ "$JOB_ID" != "UNKNOWN" ]; then
    for i in {1..60}; do
        STATUS=$(squeue -j $JOB_ID -h -o "%T" 2>/dev/null || echo "UNKNOWN")
        
        if [ "$STATUS" == "RUNNING" ]; then
            echo "✓ Server is running!"
            break
        elif [ "$STATUS" == "PENDING" ]; then
            echo "  Job is pending... (attempt $i/60, waiting 10s)"
            sleep 10
        elif [ "$STATUS" == "UNKNOWN" ] || [ -z "$STATUS" ]; then
            echo "⚠ Job may have completed or failed"
            echo "Check logs: cat logs/slurm-$JOB_ID.out"
            break
        else
            echo "⚠ Job status: $STATUS"
            echo "Check logs: cat logs/slurm-$JOB_ID.out"
            break
        fi
    done
else
    echo "⚠ Skipping automatic status check. Please monitor manually:"
    echo "  squeue -u \$USER"
fi
echo ""

# Step 7: Get server endpoint
echo "Step 7: Getting server endpoint..."
sleep 10  # Wait for log file to be written

# Try to get node from squeue
NODE=$(squeue -u $USER -j $JOB_ID -h -o "%R" 2>/dev/null || echo "")

if [ -n "$NODE" ]; then
    ENDPOINT="http://${NODE}:8000"
    echo "✓ Server endpoint: $ENDPOINT"
    echo ""
    echo "========================================="
    echo "IMPORTANT: Update your client recipe!"
    echo "========================================="
    echo ""
    echo "Run this command to update the simple test recipe:"
    echo "  sed -i 's|service: vllm-server|# service: vllm-server|' recipes/clients/vllm-simple-test.yaml"
    echo "  sed -i 's|# endpoint:.*|endpoint: \"$ENDPOINT\"|' recipes/clients/vllm-simple-test.yaml"
    echo ""
    echo "Or edit manually:"
    echo "  nano recipes/clients/vllm-simple-test.yaml"
    echo ""
else
    echo "⚠ Could not determine server node automatically."
    echo ""
    echo "To get the endpoint:"
    echo "1. Check SLURM queue:"
    echo "   squeue -u \$USER -o \"%.18i %.9P %.50j %.8u %.8T %.10M %.9l %.6D %R\""
    echo ""
    echo "2. Or check server logs (wait a minute for them to appear):"
    if [ "$JOB_ID" != "UNKNOWN" ]; then
        echo "   cat slurm-${JOB_ID}.out | grep 'Server Endpoint'"
    else
        echo "   ls -lt slurm-*.out | head -1"
        echo "   cat <latest-log-file> | grep 'Server Endpoint'"
    fi
    echo ""
    echo "3. Then update recipes/clients/vllm-simple-test.yaml with the endpoint"
    echo ""
fi

# Step 8: Instructions for next steps
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo ""
echo "1. Verify server is running:"
echo "   python -m server status"
echo ""
echo "2. Update client recipe with server endpoint (if not done above)"
echo "   nano recipes/clients/vllm-simple-test.yaml"
echo ""
echo "3. Run simple benchmark test:"
echo "   python -m client run --recipe vllm-simple-test"
echo ""
echo "4. Monitor jobs:"
echo "   watch -n 5 'squeue -u \$USER'"
echo ""
echo "5. Collect results after completion:"
echo "   python -m client metrics --output ./results/vllm-metrics.json"
echo ""
echo "6. View results:"
echo "   cat ./results/vllm-metrics.json | python -m json.tool"
echo ""
echo "7. Stop server when done:"
if [ "$JOB_ID" != "UNKNOWN" ]; then
    echo "   scancel $JOB_ID"
else
    echo "   python -m server stop-all"
fi
echo ""
echo "================================================"
echo "For more details, see:"
echo "  - QUICK_REFERENCE.md (quick commands)"
echo "  - MELUXINA_GUIDE.md (complete guide)"
echo "================================================"
