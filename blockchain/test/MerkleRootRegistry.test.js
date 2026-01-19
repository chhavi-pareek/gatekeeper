const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("MerkleRootRegistry", function () {
    let registry;
    let owner;
    let addr1;
    let addr2;

    beforeEach(async function () {
        [owner, addr1, addr2] = await ethers.getSigners();
        const MerkleRootRegistry = await ethers.getContractFactory("MerkleRootRegistry");
        registry = await MerkleRootRegistry.deploy();
        await registry.waitForDeployment();
    });

    describe("Deployment", function () {
        it("Should set the deployer as owner", async function () {
            expect(await registry.owner()).to.equal(owner.address);
        });

        it("Should authorize the owner by default", async function () {
            expect(await registry.authorizedAnchors(owner.address)).to.be.true;
        });

        it("Should start with zero anchors", async function () {
            expect(await registry.getTotalAnchors()).to.equal(0);
        });
    });

    describe("Anchoring Merkle Roots", function () {
        it("Should anchor a Merkle root successfully", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test_merkle_root"));
            const batchId = 1;
            const requestCount = 10;

            await expect(registry.anchorMerkleRoot(merkleRoot, batchId, requestCount))
                .to.emit(registry, "MerkleRootAnchored")
                .withArgs(merkleRoot, batchId, requestCount, await ethers.provider.getBlock('latest').then(b => b.timestamp + 1), owner.address);

            expect(await registry.getTotalAnchors()).to.equal(1);
        });

        it("Should retrieve anchored Merkle root by batch ID", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            const batchId = 5;
            const requestCount = 15;

            await registry.anchorMerkleRoot(merkleRoot, batchId, requestCount);

            const record = await registry.getMerkleRootByBatchId(batchId);
            expect(record.merkleRoot).to.equal(merkleRoot);
            expect(record.batchId).to.equal(batchId);
            expect(record.requestCount).to.equal(requestCount);
            expect(record.anchoredBy).to.equal(owner.address);
        });

        it("Should retrieve anchored Merkle root by index", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            await registry.anchorMerkleRoot(merkleRoot, 1, 10);

            const record = await registry.getMerkleRoot(0);
            expect(record.merkleRoot).to.equal(merkleRoot);
        });

        it("Should get latest Merkle root", async function () {
            const merkleRoot1 = ethers.keccak256(ethers.toUtf8Bytes("test1"));
            const merkleRoot2 = ethers.keccak256(ethers.toUtf8Bytes("test2"));

            await registry.anchorMerkleRoot(merkleRoot1, 1, 10);
            await registry.anchorMerkleRoot(merkleRoot2, 2, 15);

            const latest = await registry.getLatestMerkleRoot();
            expect(latest.merkleRoot).to.equal(merkleRoot2);
            expect(latest.batchId).to.equal(2);
        });

        it("Should prevent duplicate batch IDs", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            await registry.anchorMerkleRoot(merkleRoot, 1, 10);

            await expect(registry.anchorMerkleRoot(merkleRoot, 1, 10))
                .to.be.revertedWith("Batch ID already anchored");
        });

        it("Should reject zero merkle root", async function () {
            await expect(registry.anchorMerkleRoot(ethers.ZeroHash, 1, 10))
                .to.be.revertedWith("Invalid merkle root");
        });

        it("Should reject zero request count", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            await expect(registry.anchorMerkleRoot(merkleRoot, 1, 0))
                .to.be.revertedWith("Request count must be greater than 0");
        });

        it("Should check if batch is anchored", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            expect(await registry.isBatchAnchored(1)).to.be.false;

            await registry.anchorMerkleRoot(merkleRoot, 1, 10);
            expect(await registry.isBatchAnchored(1)).to.be.true;
            expect(await registry.isBatchAnchored(2)).to.be.false;
        });
    });

    describe("Access Control", function () {
        it("Should only allow authorized anchors", async function () {
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));

            await expect(registry.connect(addr1).anchorMerkleRoot(merkleRoot, 1, 10))
                .to.be.revertedWith("Not authorized to anchor Merkle roots");
        });

        it("Should allow owner to add authorized anchor", async function () {
            await expect(registry.addAuthorizedAnchor(addr1.address))
                .to.emit(registry, "AuthorizedAnchorAdded")
                .withArgs(addr1.address);

            expect(await registry.authorizedAnchors(addr1.address)).to.be.true;

            // addr1 should now be able to anchor
            const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes("test"));
            await expect(registry.connect(addr1).anchorMerkleRoot(merkleRoot, 1, 10))
                .to.not.be.reverted;
        });

        it("Should allow owner to remove authorized anchor", async function () {
            await registry.addAuthorizedAnchor(addr1.address);

            await expect(registry.removeAuthorizedAnchor(addr1.address))
                .to.emit(registry, "AuthorizedAnchorRemoved")
                .withArgs(addr1.address);

            expect(await registry.authorizedAnchors(addr1.address)).to.be.false;
        });

        it("Should prevent removing owner as authorized anchor", async function () {
            await expect(registry.removeAuthorizedAnchor(owner.address))
                .to.be.revertedWith("Cannot remove owner");
        });

        it("Should only allow owner to add/remove anchors", async function () {
            await expect(registry.connect(addr1).addAuthorizedAnchor(addr2.address))
                .to.be.revertedWith("Only owner can call this function");

            await expect(registry.connect(addr1).removeAuthorizedAnchor(owner.address))
                .to.be.revertedWith("Only owner can call this function");
        });
    });

    describe("Ownership Transfer", function () {
        it("Should transfer ownership", async function () {
            await expect(registry.transferOwnership(addr1.address))
                .to.emit(registry, "OwnershipTransferred")
                .withArgs(owner.address, addr1.address);

            expect(await registry.owner()).to.equal(addr1.address);
            expect(await registry.authorizedAnchors(addr1.address)).to.be.true;
        });

        it("Should prevent transferring to zero address", async function () {
            await expect(registry.transferOwnership(ethers.ZeroAddress))
                .to.be.revertedWith("Invalid new owner address");
        });

        it("Should only allow owner to transfer ownership", async function () {
            await expect(registry.connect(addr1).transferOwnership(addr2.address))
                .to.be.revertedWith("Only owner can call this function");
        });
    });

    describe("Edge Cases", function () {
        it("Should revert when getting non-existent index", async function () {
            await expect(registry.getMerkleRoot(0))
                .to.be.revertedWith("Index out of bounds");
        });

        it("Should revert when getting non-existent batch ID", async function () {
            await expect(registry.getMerkleRootByBatchId(999))
                .to.be.revertedWith("Batch ID not found");
        });

        it("Should revert when getting latest with no anchors", async function () {
            await expect(registry.getLatestMerkleRoot())
                .to.be.revertedWith("No merkle roots anchored yet");
        });

        it("Should handle multiple anchors correctly", async function () {
            for (let i = 1; i <= 5; i++) {
                const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes(`test${i}`));
                await registry.anchorMerkleRoot(merkleRoot, i, i * 10);
            }

            expect(await registry.getTotalAnchors()).to.equal(5);

            const latest = await registry.getLatestMerkleRoot();
            expect(latest.batchId).to.equal(5);
            expect(latest.requestCount).to.equal(50);
        });
    });
});
