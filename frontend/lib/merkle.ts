/**
 * Client-side Merkle tree verification utilities
 */

/**
 * Compute SHA-256 hash of a string (browser-compatible)
 */
async function sha256(message: string): Promise<string> {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    return hashHex;
}

/**
 * Build Merkle tree from list of hashes and return root hash.
 * 
 * Uses binary Merkle tree construction:
 * - Leaf nodes: Individual hashes
 * - Parent nodes: SHA-256(left_hash + right_hash)
 * - Odd number handling: Duplicate last hash
 * 
 * @param hashes - List of SHA-256 hashes (hex strings)
 * @returns Root hash of the Merkle tree (64-character hex string)
 */
export async function buildMerkleTree(hashes: string[]): Promise<string> {
    if (hashes.length === 0) {
        return "";
    }
    if (hashes.length === 1) {
        return hashes[0];
    }

    // Build tree level by level
    let currentLevel = [...hashes];
    while (currentLevel.length > 1) {
        const nextLevel: string[] = [];
        for (let i = 0; i < currentLevel.length; i += 2) {
            const left = currentLevel[i];
            // If odd number, duplicate last hash
            const right = i + 1 < currentLevel.length ? currentLevel[i + 1] : left;
            // Combine and hash
            const parent = await sha256(left + right);
            nextLevel.push(parent);
        }
        currentLevel = nextLevel;
    }

    return currentLevel[0];
}

/**
 * Verify that a computed Merkle root matches the expected root
 * 
 * @param hashes - List of hashes to verify
 * @param expectedRoot - Expected Merkle root
 * @returns True if computed root matches expected root
 */
export async function verifyMerkleRoot(
    hashes: string[],
    expectedRoot: string
): Promise<boolean> {
    const computedRoot = await buildMerkleTree(hashes);
    return computedRoot === expectedRoot;
}
