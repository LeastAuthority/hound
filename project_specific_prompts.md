# Project-Specific Prompts Configuration - Substrate Node

This configuration is tailored for analyzing Substrate-based blockchain node implementations.

## Domain Information

**Domain Name:** Substrate Blockchain Node Security
**Code Units:** runtime pallets, consensus modules, and p2p handlers
**State Concept:** on-chain storage, runtime state, and extrinsic pool

## Operating Constraints

- Hound performs static code analysis only - it cannot run a Substrate node, sync with networks, or execute runtime calls.
- Do NOT propose or assume live network operations (e.g., syncing mainnet/testnet, connecting to bootnodes, submitting extrinsics, querying RPC endpoints).
- Do NOT suggest runtime execution, benchmarking, or on-chain queries.
- All actions here are CODE-ONLY: analyzing Rust code, mapping pallet interactions, checking storage patterns, reviewing consensus logic, and examining extrinsic validation.

## Code Unit Prioritization (Phase 1)

Target medium-sized units: pallets, consensus handlers, transaction validators, storage migrations, p2p message handlers

Prioritize components:
- Handling runtime calls (dispatchables) with privileged origins
- Managing on-chain storage and state transitions
- Implementing custom consensus logic or block validation
- Processing extrinsics (transactions) and validating signatures
- Handling runtime upgrades and storage migrations
- Managing token economics (balances, staking, rewards)
- Integrating with off-chain workers or external data sources
- Implementing cross-chain messaging (XCM for parachains)

## Vulnerability Categories (Phase 1 - Coverage)

Look for these vulnerability types during systematic analysis:
- Origin validation failures (unsigned/signed/root origin checks)
- Storage corruption or inconsistent state transitions
- Integer overflow/underflow in arithmetic operations
- Weight calculation errors (incorrect gas metering)
- Panic conditions that halt block production
- Unsigned transaction validation bypasses
- Storage migration bugs (data loss, incorrect transformations)
- Economic attacks (inflation, slashing bypasses, reward manipulation)
- Consensus safety violations (equivocation, finality breaks)
- Extrinsic replay attacks or nonce bypasses
- Off-chain worker vulnerabilities (untrusted external data)
- XCM security issues (asset theft via cross-chain messages)
- Runtime upgrade issues (breaking changes, state inconsistencies)
- Cryptographic implementation errors (signature verification, hashing)

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** CONSENSUS AND ECONOMIC FAILURES - prioritize vulnerabilities that cause chain halts, finality breaks, fund loss, or economic exploits

**Key Intuition Targets:**
1. ECONOMIC EXPLOITS: Where can tokens be minted, stolen, or economic invariants be violated (total issuance, reserved balances)?
2. CONSENSUS SAFETY: Where can validators disagree on block validity, finality be broken, or equivocation go undetected?
3. ORIGIN BYPASSES: Where might privileged calls (sudo, root, collective) be callable without proper authorization?
4. STATE CORRUPTION: What storage operations could break runtime invariants, cause panics, or corrupt critical state?

## Mitigation Patterns

Common security patterns to verify:
- Origin checks (ensure_signed, ensure_root, ensure_none for unsigned)
- Arithmetic operations using safe math (saturating_add, checked_mul, etc.)
- Weight annotations on all dispatchable calls
- Storage access patterns (avoid unbounded iteration, use pagination)
- Event emission for all state changes
- Storage migrations with version checks
- Benchmarking coverage for all extrinsic calls
- Nonce validation for replay protection
- Reserve/unreserve patterns for economic locks
- Slash/reward calculations with invariant checks
- Off-chain worker signature verification
- XCM barrier and filter configurations

## Observation Examples

Good examples for graph annotations (2-4 words each):
- "ensure_root required"
- "ensure_signed call"
- "unsigned transaction"
- "storage write"
- "panics on overflow"
- "saturating arithmetic"
- "weight annotated"
- "requires benchmarking"
- "storage migration"
- "origin bypass risk"
- "economic invariant"
- "consensus-critical"
- "off-chain worker"
- "XCM handler"
- "slashing logic"
- "reward calculation"

## Graph Types

### Suggested Graph Types for Analysis

**RuntimeDispatch**
Focus: Pallet dispatchable calls and origin requirements
Edge types: requires_origin, calls_pallet, validates, dispatches

**StorageAccess**
Focus: On-chain storage reads/writes and storage migration paths
Edge types: reads_storage, writes_storage, migrates, iterates_unbounded

**OriginValidation**
Focus: Origin checks and privilege escalation paths
Edge types: ensures_signed, ensures_root, requires_origin, bypasses_check

**ExtrinsicFlow**
Focus: Transaction validation pipeline from submission to execution
Edge types: validates_signature, checks_nonce, applies_weight, executes

**ConsensusLogic**
Focus: Block validation, authorship, and finality mechanisms
Edge types: validates_block, authors, finalizes, checks_equivocation

**EconomicFlows**
Focus: Token transfers, minting, burning, staking, and reward distribution
Edge types: transfers, mints, burns, stakes, slashes, rewards

**WeightCalculation**
Focus: Computational weight assignments and gas metering
Edge types: charges_weight, benchmarks, exceeds_limit, refunds

**StorageMigration**
Focus: Runtime upgrade storage migrations and version checks
Edge types: migrates_from, transforms, preserves, checks_version

**OffChainWorker**
Focus: Off-chain worker logic and external data integration
Edge types: fetches_external, submits_unsigned, validates_data, signs_transaction

**XCMIntegration**
Focus: Cross-chain messaging (for parachains) and asset transfers
Edge types: sends_xcm, receives_xcm, executes_instruction, validates_origin

**PalletDependencies**
Focus: Inter-pallet dependencies and coupling
Edge types: depends_on, tightly_coupled, calls, imports

## External Dependencies Examples

Common external libraries/frameworks to exclude from node creation:
- frame-support (Substrate FRAME support library)
- frame-system (Substrate system pallet)
- sp-runtime (Substrate runtime primitives)
- sp-core (Substrate core primitives)
- sp-std (Substrate standard library)
- parity-scale-codec (SCALE encoding/decoding)
- sp-io (Substrate I/O)
- frame-benchmarking (benchmarking framework)
- pallet-balances (standard balances pallet - unless heavily customized)
- pallet-timestamp (standard timestamp pallet)
- pallet-transaction-payment (standard transaction fee pallet)
- finality-grandpa (GRANDPA finality gadget)
- sc-consensus-babe (BABE consensus)
- libp2p (p2p networking library)

## Node Type Terminology

**Preferred node types:**
- Pallet-level nodes (e.g., "pallet_MyCustomPallet", "pallet_staking")
- Dispatchable function nodes (e.g., "dispatchable_transfer", "dispatchable_bond")
- Storage item nodes (e.g., "storage_TotalIssuance", "storage_Validators")
- Hook nodes (e.g., "hook_on_initialize", "hook_on_finalize")
- Origin validation nodes (e.g., "origin_ensure_root", "origin_ensure_signed")
- Consensus handler nodes (e.g., "consensus_validate_block", "finality_vote")
- Migration nodes (e.g., "migration_v2_to_v3", "storage_transform")

## Additional Notes

### Substrate-Specific Security Considerations

**Consensus Mechanism:**
- This project uses BABE for block production and GRANDPA for finality
- Pay special attention to equivocation detection and slashing logic
- Validator set rotation and session management are consensus-critical

**Runtime Upgrades:**
- Substrate supports forkless runtime upgrades via set_code
- All storage migrations MUST be tested for data preservation
- Breaking changes in storage layout can corrupt chain state

**Weight System:**
- Every dispatchable MUST have accurate weight annotations
- Incorrect weights can lead to DoS (too low) or poor UX (too high)
- All weights should be derived from benchmarking, not guesswork

**Economic Model:**
- Total issuance invariant: sum of all balances must equal total issuance
- Reserved balance rules: reserved + free = total for each account
- Slashing must not cause integer underflow or account corruption
- Inflation/reward calculations must preserve economic invariants

**Critical Invariants:**
- The runtime MUST NOT panic during block execution (would halt chain)
- Storage items with IterableStorageMap must have bounded iteration
- Unsigned transactions MUST validate thoroughly (can't rely on signature)
- Root/sudo calls should be heavily restricted or eliminated before mainnet

**Performance Targets:**
- Block time: 6 seconds (BABE typical)
- Finality: 2-3 blocks (GRANDPA typical)
- State size growth: monitor storage rent/cleanup mechanisms

**Known Attack Vectors:**
- Long-range attacks (mitigated by finality)
- Griefing attacks via cheap unsigned transactions
- Storage exhaustion via unbounded maps
- Equivocation in block production
- Economic attacks via reward/slash manipulation

### Custom Pallet Focus Areas

**High-Priority Custom Pallets:**
- Any pallet handling token transfers or minting
- Pallets with sudo/root-level calls
- Pallets implementing custom staking or governance
- Pallets using off-chain workers
- Pallets with storage migrations
- Pallets accepting unsigned transactions

**Standard Pallets (Lower Priority):**
- Well-audited standard pallets (balances, timestamp) are lower risk
- However, analyze how YOUR runtime CONFIGURES these pallets
- Check for unusual parameter values or trait implementations
