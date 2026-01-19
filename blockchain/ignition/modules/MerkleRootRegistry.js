const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

/**
 * Hardhat Ignition deployment module for MerkleRootRegistry
 * 
 * Deploy with:
 * npx hardhat ignition deploy ignition/modules/MerkleRootRegistry.js --network sepolia
 */
module.exports = buildModule("MerkleRootRegistryModule", (m) => {
    // Deploy the MerkleRootRegistry contract
    const merkleRootRegistry = m.contract("MerkleRootRegistry");

    return { merkleRootRegistry };
});
