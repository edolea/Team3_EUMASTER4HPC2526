#!/bin/bash
# Cleanup zombie vLLM processes on GPU nodes

echo "========================================="
echo "vLLM Cleanup Script"
echo "========================================="

# Get list of GPU nodes that might have zombie processes
NODES=$(squeue -u $USER -p gpu -h -o "%N" | sort -u)

if [ -z "$NODES" ]; then
    echo "No active GPU jobs found for user $USER"
    echo ""
    echo "Checking recent GPU nodes from logs..."
    NODES=$(ls -t slurm-*.out 2>/dev/null | head -20 | xargs grep -h "Hostname.*mel" | grep -oP "mel\d+" | sort -u)
fi

if [ -z "$NODES" ]; then
    echo "No nodes to check. If you know the node name, run:"
    echo "  ssh <node> 'pkill -9 -f vllm'"
    exit 0
fi

echo "Found nodes to check:"
echo "$NODES"
echo ""

for NODE in $NODES; do
    echo "Checking node: $NODE"
    
    # Check for vLLM processes
    PROCS=$(ssh $NODE "ps aux | grep -E 'vllm|python.*8000' | grep -v grep" 2>/dev/null || true)
    
    if [ -n "$PROCS" ]; then
        echo "  Found vLLM processes:"
        echo "$PROCS" | sed 's/^/    /'
        echo ""
        echo "  Killing processes..."
        ssh $NODE "pkill -9 -f 'vllm.entrypoints.openai.api_server'" 2>/dev/null || true
        ssh $NODE "pkill -9 -f 'python.*8000'" 2>/dev/null || true
        sleep 1
        echo "  ✓ Cleanup complete"
    else
        echo "  No vLLM processes found"
    fi
    echo ""
done

echo "========================================="
echo "Cleanup complete!"
echo "========================================="
echo ""
echo "You can now deploy the server:"
echo "  ./ai-factories.sh server run --recipe vllm-server"
