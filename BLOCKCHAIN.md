# Blockchain Anchoring

Cryptographic transparency system that anchors Merkle roots to Sepolia testnet for immutable proof of API usage.

## Overview

Every 10 API requests:
1. Compute SHA-256 hashes of request metadata
2. Build Merkle tree and compute root
3. Anchor root to Sepolia blockchain via smart contract
4. Store transaction hash and block number

**Benefits**: Immutable audit trail, public verification, tamper-proof records

## Architecture

```
API Requests → Hash Storage → Merkle Root Computation → Blockchain Anchoring → Sepolia Testnet
```

**Smart Contract**: `MerkleRootRegistry.sol` (Sepolia: `0x8fF577A0Af7872D36584F11398358733Ec6B6778`)

## Setup

### 1. Environment Configuration

Create `/home/fate/prj/gatekeeper/.env`:
```bash
ALCHEMY_SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY
BLOCKCHAIN_PRIVATE_KEY=your_private_key_here
CONTRACT_ADDRESS=0x8fF577A0Af7872D36584F11398358733Ec6B6778
ENABLE_BLOCKCHAIN_ANCHORING=true
```

### 2. Get Requirements

- **Alchemy API Key**: https://www.alchemy.com/ (free, select Sepolia)
- **Wallet**: MetaMask with exported private key
- **Testnet ETH**: Get ~0.5 ETH from https://sepoliafaucet.com/

### 3. Install Dependencies

```bash
pip install web3 python-dotenv eth-account
```

### 4. Start Backend

```bash
uvicorn main:app --reload
```

**Logs should show**:
```
INFO:app.blockchain:Connected to Sepolia. Chain ID: 11155111
INFO:app.blockchain:Wallet address: 0x...
INFO:app.blockchain:✅ Blockchain anchoring service initialized successfully
```

## Testing

### Make Test Requests

```bash
# Make 10 requests to trigger Merkle root computation
for i in {1..10}; do
  curl http://127.0.0.1:8000/proxy/SERVICE_ID -H "X-API-Key: YOUR_KEY"
done
```

### Expected Logs

```
INFO:main:Computed Merkle root: batch_id=1, root=abc123...
INFO:app.blockchain:⛓️  Anchoring transaction sent: 0x...
INFO:app.blockchain:   View on Etherscan: https://sepolia.etherscan.io/tx/0x...
INFO:app.blockchain:✅ Merkle root anchored successfully!
INFO:app.blockchain:   Block: 10078530
INFO:app.blockchain:   Gas used: 162358
```

### Verify on Blockchain

**API Endpoint**:
```bash
curl http://127.0.0.1:8000/transparency/blockchain/1
```

**Response**:
```json
{
  "batch_id": 1,
  "is_anchored": true,
  "tx_hash": "0xb973a5925eebf95395bb2a3f217a6d0c4b2d7e05b3ac68f6b84eeca980535680",
  "block_number": 10078530,
  "anchored_at": "2026-01-19T14:54:11",
  "etherscan_url": "https://sepolia.etherscan.io/tx/0x..."
}
```

**Etherscan**: Visit the `etherscan_url` to see on-chain proof

## API Endpoints

### Get Latest Merkle Root
```bash
GET /transparency/merkle-latest
```

### Get Merkle History
```bash
GET /transparency/merkle-history?limit=50&offset=0
```

### Verify Merkle Batch
```bash
GET /transparency/verify/{batch_id}
```

### Get Blockchain Proof
```bash
GET /transparency/blockchain/{batch_id}
```

## Frontend

Navigate to `http://localhost:3000/transparency` to view:
- Latest Merkle root with metadata
- Client-side integrity verification
- Historical Merkle roots table
- Blockchain anchoring status

## Smart Contract

**Contract**: `MerkleRootRegistry.sol`  
**Network**: Sepolia Testnet  
**Address**: `0x8fF577A0Af7872D36584F11398358733Ec6B6778`

### Key Functions

- `anchorMerkleRoot(bytes32, uint256, uint256)` - Store Merkle root
- `getMerkleRootByBatchId(uint256)` - Retrieve by batch ID
- `getTotalAnchors()` - Get total count
- `isBatchAnchored(uint256)` - Check if anchored

### Deploy New Contract

```bash
cd blockchain
npx hardhat run scripts/deploy.js --network sepolia
npx hardhat verify --network sepolia CONTRACT_ADDRESS
```

## Configuration

**Batch Size** (default: 10):
```bash
export MERKLE_BATCH_SIZE=10
```

**Disable Blockchain Anchoring**:
```bash
export ENABLE_BLOCKCHAIN_ANCHORING=false
```

## Cost Estimates

**Sepolia (Testnet)**: Free (testnet ETH)  
**Mainnet**: ~$2-5 USD per anchor (varies with gas prices)

**Gas Usage**:
- Contract deployment: ~885,000 gas
- Per anchor: ~165,000 gas

## Security

- ✅ Private keys stored in `.env` (gitignored)
- ✅ Environment variables loaded via `python-dotenv`
- ✅ Transaction signing done locally
- ✅ No private keys in logs or responses

## Troubleshooting

### "Blockchain anchoring is disabled"
- Check `.env` file exists with correct values
- Verify `ENABLE_BLOCKCHAIN_ANCHORING=true`
- Restart backend after `.env` changes

### "Insufficient funds"
- Get testnet ETH from faucets
- Check balance: `https://sepolia.etherscan.io/address/YOUR_WALLET`

### "Transaction failed"
- Check wallet has enough ETH for gas
- Verify contract address is correct
- Check batch ID not already anchored

### "Invalid transaction hash"
- Ensure hash has `0x` prefix for Etherscan
- Wait 10-30 seconds for transaction to propagate

## Production Deployment

### Mainnet Considerations

1. **Deploy to Ethereum Mainnet**:
   ```bash
   # Update hardhat.config.js with mainnet RPC
   npx hardhat run scripts/deploy.js --network mainnet
   ```

2. **Update Environment**:
   ```bash
   ALCHEMY_MAINNET_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
   CONTRACT_ADDRESS=0x... # New mainnet address
   ```

3. **Fund Wallet**: Add real ETH for gas fees

4. **Monitor Costs**: Set up alerts for gas price spikes

### Best Practices

- Use hardware wallet for mainnet private keys
- Implement gas price limits
- Set up monitoring/alerting
- Regular backup of transaction logs
- Consider batching multiple roots per transaction

## Files

**Backend**:
- `app/blockchain.py` - Web3 integration
- `app/models.py` - Database models (blockchain fields)
- `main.py` - Anchoring integration

**Smart Contract**:
- `blockchain/contracts/MerkleRootRegistry.sol`
- `blockchain/hardhat.config.js`
- `blockchain/scripts/deploy.js`
- `blockchain/test/MerkleRootRegistry.test.js`

**Frontend**:
- `frontend/lib/api.ts` - API client methods
- `frontend/lib/merkle.ts` - Client-side verification
- `frontend/app/transparency/page.tsx` - UI

## Support

For issues or questions:
1. Check logs: `uvicorn main:app --reload` output
2. Verify on Etherscan: Transaction status and events
3. Test locally: `npx hardhat test` in blockchain directory
