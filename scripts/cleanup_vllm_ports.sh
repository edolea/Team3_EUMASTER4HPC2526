#!/bin/bash
# Cleanup script for zombie vLLM processes on GPU nodes
# Run this if you still have port binding issues from previous failed deployments

echo "========================================="
echo "vLLM Port Cleanup Utility"
echo "========================================="
echo ""

# List of GPU nodes where vLLM might be running
GPU_NODES=("mel2105" "mel2170" "mel2106" "mel2039")

echo "Checking for vLLM processes on GPU nodes..."
echo ""

for NODE in "${GPU_NODES[@]}"; do
    echo "Checking $NODE..."
    
    # Check if we can ssh to the node
    if ssh -o ConnectTimeout=5 "$NODE" "exit" 2>/dev/null; then
        # Find vLLM processes
        PROCESSES=$(ssh "$NODE" "ps aux | grep -E 'vllm|python.*api_server' | grep -v grep" 2>/dev/null)
        
        if [ -n "$PROCESSES" ]; then
            echo "  Found vLLM processes on $NODE:"
            echo "$PROCESSES" | sed 's/^/    /'
            echo ""
            
            # Ask for confirmation
            read -p "  Kill these processes on $NODE? [y/N] " -n 1 -r
            echo ""
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                ssh "$NODE" "pkill -9 -f 'vllm.entrypoints.openai.api_server'" 2>/dev/null
                ssh "$NODE" "pkill -9 -f 'python.*vllm'" 2>/dev/null
                echo "  ✓ Processes killed on $NODE"
            else
                echo "  Skipped $NODE"
            fi
        else
            echo "  ✓ No vLLM processes found on $NODE"
        fi
    else
        echo "  ⚠ Cannot connect to $NODE (might not be allocated)"
    fi
    echo ""
done

echo "========================================="
echo "Cleanup Complete"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Cancel any stuck SLURM jobs: scancel <job_id>"
echo "2. Check SLURM queue: squeue -u \$USER"
echo "3. Try deploying vLLM again: ./ai-factories.sh server run --recipe vllm-server"
echo ""
