// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title MerkleRootRegistry
 * @notice Stores Merkle roots from GaaS Gateway for immutable audit trail
 * @dev Each Merkle root represents a batch of API requests
 */
contract MerkleRootRegistry {
    struct MerkleRootRecord {
        bytes32 merkleRoot;
        uint256 batchId;
        uint256 requestCount;
        uint256 timestamp;
        address anchoredBy;
    }
    
    // Storage
    MerkleRootRecord[] public merkleRoots;
    mapping(uint256 => uint256) public batchIdToIndex; // batchId => array index
    
    // Access control
    address public owner;
    mapping(address => bool) public authorizedAnchors;
    
    // Events
    event MerkleRootAnchored(
        bytes32 indexed merkleRoot,
        uint256 indexed batchId,
        uint256 requestCount,
        uint256 timestamp,
        address indexed anchoredBy
    );
    
    event AuthorizedAnchorAdded(address indexed anchor);
    event AuthorizedAnchorRemoved(address indexed anchor);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }
    
    modifier onlyAuthorized() {
        require(
            authorizedAnchors[msg.sender] || msg.sender == owner,
            "Not authorized to anchor Merkle roots"
        );
        _;
    }
    
    /**
     * @notice Constructor sets deployer as owner and authorized anchor
     */
    constructor() {
        owner = msg.sender;
        authorizedAnchors[msg.sender] = true;
        emit AuthorizedAnchorAdded(msg.sender);
    }
    
    /**
     * @notice Anchor a Merkle root to the blockchain
     * @param _merkleRoot The Merkle root hash (bytes32)
     * @param _batchId The batch ID from the database
     * @param _requestCount Number of requests in this batch
     */
    function anchorMerkleRoot(
        bytes32 _merkleRoot,
        uint256 _batchId,
        uint256 _requestCount
    ) external onlyAuthorized {
        require(_merkleRoot != bytes32(0), "Invalid merkle root");
        require(_requestCount > 0, "Request count must be greater than 0");
        
        // Prevent duplicate batch IDs
        // Check if batchId already exists (handle edge case where index 0 is valid)
        if (merkleRoots.length > 0) {
            uint256 existingIndex = batchIdToIndex[_batchId];
            require(
                existingIndex >= merkleRoots.length || merkleRoots[existingIndex].batchId != _batchId,
                "Batch ID already anchored"
            );
        }
        
        MerkleRootRecord memory record = MerkleRootRecord({
            merkleRoot: _merkleRoot,
            batchId: _batchId,
            requestCount: _requestCount,
            timestamp: block.timestamp,
            anchoredBy: msg.sender
        });
        
        merkleRoots.push(record);
        batchIdToIndex[_batchId] = merkleRoots.length - 1;
        
        emit MerkleRootAnchored(
            _merkleRoot,
            _batchId,
            _requestCount,
            block.timestamp,
            msg.sender
        );
    }
    
    /**
     * @notice Get a Merkle root record by array index
     * @param _index The index in the merkleRoots array
     * @return The MerkleRootRecord at the given index
     */
    function getMerkleRoot(uint256 _index) external view returns (MerkleRootRecord memory) {
        require(_index < merkleRoots.length, "Index out of bounds");
        return merkleRoots[_index];
    }
    
    /**
     * @notice Get a Merkle root record by batch ID
     * @param _batchId The batch ID to look up
     * @return The MerkleRootRecord for the given batch ID
     */
    function getMerkleRootByBatchId(uint256 _batchId) external view returns (MerkleRootRecord memory) {
        uint256 index = batchIdToIndex[_batchId];
        require(index < merkleRoots.length, "Batch ID not found");
        require(merkleRoots[index].batchId == _batchId, "Batch ID mismatch");
        return merkleRoots[index];
    }
    
    /**
     * @notice Get the latest anchored Merkle root
     * @return The most recent MerkleRootRecord
     */
    function getLatestMerkleRoot() external view returns (MerkleRootRecord memory) {
        require(merkleRoots.length > 0, "No merkle roots anchored yet");
        return merkleRoots[merkleRoots.length - 1];
    }
    
    /**
     * @notice Get the total number of anchored Merkle roots
     * @return The count of anchored roots
     */
    function getTotalAnchors() external view returns (uint256) {
        return merkleRoots.length;
    }
    
    /**
     * @notice Check if a batch ID has been anchored
     * @param _batchId The batch ID to check
     * @return True if the batch ID exists
     */
    function isBatchAnchored(uint256 _batchId) external view returns (bool) {
        if (merkleRoots.length == 0) return false;
        uint256 index = batchIdToIndex[_batchId];
        return index < merkleRoots.length && merkleRoots[index].batchId == _batchId;
    }
    
    /**
     * @notice Add an authorized anchor address
     * @param _anchor The address to authorize
     */
    function addAuthorizedAnchor(address _anchor) external onlyOwner {
        require(_anchor != address(0), "Invalid address");
        require(!authorizedAnchors[_anchor], "Already authorized");
        authorizedAnchors[_anchor] = true;
        emit AuthorizedAnchorAdded(_anchor);
    }
    
    /**
     * @notice Remove an authorized anchor address
     * @param _anchor The address to deauthorize
     */
    function removeAuthorizedAnchor(address _anchor) external onlyOwner {
        require(authorizedAnchors[_anchor], "Not authorized");
        require(_anchor != owner, "Cannot remove owner");
        authorizedAnchors[_anchor] = false;
        emit AuthorizedAnchorRemoved(_anchor);
    }
    
    /**
     * @notice Transfer ownership to a new address
     * @param _newOwner The new owner address
     */
    function transferOwnership(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "Invalid new owner address");
        require(_newOwner != owner, "Already the owner");
        
        address previousOwner = owner;
        owner = _newOwner;
        authorizedAnchors[_newOwner] = true;
        
        emit OwnershipTransferred(previousOwner, _newOwner);
        emit AuthorizedAnchorAdded(_newOwner);
    }
}
