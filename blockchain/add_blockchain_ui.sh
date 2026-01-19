#!/bin/bash

# Script to add blockchain proof UI to transparency page
# This adds the blockchain anchoring display after the verification result section

FILE="/home/fate/prj/gatekeeper/frontend/app/transparency/page.tsx"

# Find the line number after verification result and before the closing fragment
LINE_NUM=$(grep -n "Verification Result" "$FILE" | tail -1 | cut -d: -f1)
INSERT_LINE=$((LINE_NUM + 12))

# Create the blockchain proof section
cat > /tmp/blockchain_section.tsx << 'EOF'

                                {/* Blockchain Proof - NEW */}
                                <BlockchainProof batchId={latestRoot.batch_id} />
EOF

# Note: This would require creating a BlockchainProof component
# For simplicity, let's document the manual steps instead
