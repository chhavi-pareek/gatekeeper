"""
Blockchain anchoring service for Merkle roots.
Integrates with Sepolia testnet via Alchemy RPC.
"""
from web3 import Web3
from eth_account import Account
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Contract ABI (only the functions we need)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_merkleRoot", "type": "bytes32"},
            {"internalType": "uint256", "name": "_batchId", "type": "uint256"},
            {"internalType": "uint256", "name": "_requestCount", "type": "uint256"}
        ],
        "name": "anchorMerkleRoot",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_batchId", "type": "uint256"}],
        "name": "getMerkleRootByBatchId",
        "outputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
                    {"internalType": "uint256", "name": "batchId", "type": "uint256"},
                    {"internalType": "uint256", "name": "requestCount", "type": "uint256"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "address", "name": "anchoredBy", "type": "address"}
                ],
                "internalType": "struct MerkleRootRegistry.MerkleRootRecord",
                "name": "",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getTotalAnchors",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_batchId", "type": "uint256"}],
        "name": "isBatchAnchored",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"indexed": True, "internalType": "uint256", "name": "batchId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "requestCount", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "anchoredBy", "type": "address"}
        ],
        "name": "MerkleRootAnchored",
        "type": "event"
    }
]


class BlockchainAnchor:
    """
    Service for anchoring Merkle roots to Sepolia blockchain.
    """
    
    def __init__(self):
        """Initialize blockchain connection and contract."""
        self.enabled = os.getenv("ENABLE_BLOCKCHAIN_ANCHORING", "false").lower() == "true"
        
        if not self.enabled:
            logger.info("Blockchain anchoring is disabled")
            return
        
        # Initialize Web3
        alchemy_url = os.getenv("ALCHEMY_SEPOLIA_URL")
        if not alchemy_url:
            logger.error("ALCHEMY_SEPOLIA_URL not set in environment")
            self.enabled = False
            return
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(alchemy_url))
            
            if not self.w3.is_connected():
                logger.error("Failed to connect to Sepolia via Alchemy")
                self.enabled = False
                return
            
            logger.info(f"Connected to Sepolia. Chain ID: {self.w3.eth.chain_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            self.enabled = False
            return
        
        # Load account
        private_key = os.getenv("BLOCKCHAIN_PRIVATE_KEY")
        if not private_key:
            logger.error("BLOCKCHAIN_PRIVATE_KEY not set in environment")
            self.enabled = False
            return
        
        try:
            # Handle private key with or without 0x prefix
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            
            self.account = Account.from_key(private_key)
            self.address = self.account.address
            
            # Check balance
            balance = self.w3.eth.get_balance(self.address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            logger.info(f"Wallet address: {self.address}")
            logger.info(f"Wallet balance: {balance_eth} ETH")
            
            if balance == 0:
                logger.warning("Wallet has zero balance! Get testnet ETH from faucets.")
        except Exception as e:
            logger.error(f"Failed to load account: {e}")
            self.enabled = False
            return
        
        # Load contract
        contract_address = os.getenv("CONTRACT_ADDRESS")
        if not contract_address:
            logger.error("CONTRACT_ADDRESS not set in environment")
            self.enabled = False
            return
        
        try:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=CONTRACT_ABI
            )
            logger.info(f"Contract loaded at: {contract_address}")
            
            # Test contract connection
            total_anchors = self.contract.functions.getTotalAnchors().call()
            logger.info(f"Total anchors on-chain: {total_anchors}")
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
            self.enabled = False
            return
        
        logger.info("✅ Blockchain anchoring service initialized successfully")
    
    def anchor_merkle_root(
        self,
        merkle_root: str,
        batch_id: int,
        request_count: int
    ) -> Optional[Dict[str, any]]:
        """
        Anchor a Merkle root to the blockchain.
        
        Args:
            merkle_root: 64-character hex string (no 0x prefix)
            batch_id: Batch ID from database
            request_count: Number of requests in batch
        
        Returns:
            dict with tx_hash, block_number, and gas_used, or None if failed
        """
        if not self.enabled:
            logger.warning("Blockchain anchoring is disabled, skipping")
            return None
        
        try:
            # Convert merkle root to bytes32
            if merkle_root.startswith("0x"):
                merkle_root = merkle_root[2:]
            merkle_root_bytes = bytes.fromhex(merkle_root)
            
            # Check if already anchored
            is_anchored = self.contract.functions.isBatchAnchored(batch_id).call()
            if is_anchored:
                logger.warning(f"Batch {batch_id} is already anchored on-chain")
                return None
            
            # Get current nonce
            nonce = self.w3.eth.get_transaction_count(self.address)
            
            # Estimate gas
            try:
                gas_estimate = self.contract.functions.anchorMerkleRoot(
                    merkle_root_bytes,
                    batch_id,
                    request_count
                ).estimate_gas({'from': self.address})
                gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}. Using default gas limit.")
                gas_limit = 200000
            
            # Get current gas price
            base_fee = self.w3.eth.get_block('latest')['baseFeePerGas']
            max_priority_fee = self.w3.to_wei('2', 'gwei')
            max_fee = base_fee * 2 + max_priority_fee
            
            # Build transaction
            tx = self.contract.functions.anchorMerkleRoot(
                merkle_root_bytes,
                batch_id,
                request_count
            ).build_transaction({
                'from': self.address,
                'nonce': nonce,
                'gas': gas_limit,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': max_priority_fee,
                'chainId': 11155111  # Sepolia
            })
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = "0x" + tx_hash.hex() if not tx_hash.hex().startswith("0x") else tx_hash.hex()
            
            logger.info(f"⛓️  Anchoring transaction sent: {tx_hash_hex}")
            logger.info(f"   View on Etherscan: https://sepolia.etherscan.io/tx/{tx_hash_hex}")
            
            # Wait for receipt (with timeout)
            logger.info("   Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                logger.info(f"✅ Merkle root anchored successfully!")
                logger.info(f"   Block: {receipt['blockNumber']}")
                logger.info(f"   Gas used: {receipt['gasUsed']}")
                
                return {
                    "tx_hash": tx_hash_hex,
                    "block_number": receipt['blockNumber'],
                    "gas_used": receipt['gasUsed']
                }
            else:
                logger.error(f"❌ Transaction failed: {tx_hash_hex}")
                return None
        
        except Exception as e:
            logger.error(f"Failed to anchor Merkle root: {e}")
            return None
    
    def get_on_chain_record(self, batch_id: int) -> Optional[Dict[str, any]]:
        """
        Retrieve on-chain record for a batch ID.
        
        Args:
            batch_id: Batch ID to look up
        
        Returns:
            dict with merkle_root, timestamp, anchored_by, etc., or None if not found
        """
        if not self.enabled:
            return None
        
        try:
            is_anchored = self.contract.functions.isBatchAnchored(batch_id).call()
            if not is_anchored:
                return None
            
            record = self.contract.functions.getMerkleRootByBatchId(batch_id).call()
            
            return {
                "merkle_root": record[0].hex(),
                "batch_id": record[1],
                "request_count": record[2],
                "timestamp": record[3],
                "anchored_by": record[4]
            }
        except Exception as e:
            logger.error(f"Failed to get on-chain record: {e}")
            return None


# Global instance
blockchain_anchor = BlockchainAnchor()
