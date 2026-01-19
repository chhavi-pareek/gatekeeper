const hre = require("hardhat");

/**
 * Deploy MerkleRootRegistry contract
 * 
 * Usage:
 * npx hardhat run scripts/deploy.js --network sepolia
 */
async function main() {
    console.log("Deploying MerkleRootRegistry contract...");

    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying with account:", deployer.address);

    const balance = await hre.ethers.provider.getBalance(deployer.address);
    console.log("Account balance:", hre.ethers.formatEther(balance), "ETH");

    // Deploy contract
    const MerkleRootRegistry = await hre.ethers.getContractFactory("MerkleRootRegistry");
    const registry = await MerkleRootRegistry.deploy();

    await registry.waitForDeployment();

    const address = await registry.getAddress();
    console.log("MerkleRootRegistry deployed to:", address);
    console.log("\nSave this address to your .env file:");
    console.log(`CONTRACT_ADDRESS=${address}`);
    console.log("\nTo verify on Etherscan, run:");
    console.log(`npx hardhat verify --network sepolia ${address}`);
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
