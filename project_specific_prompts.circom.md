# Project-Specific Prompts Configuration - Circom zkSNARK Circuits

This configuration is tailored for analyzing Circom zero-knowledge circuit implementations, with emphasis on constraint completeness and correctness with respect to formal specifications.

## Domain Information

**Domain Name:** Circom zkSNARK Circuit Security
**Code Units:** circuit templates, signal constraints, and component instantiations
**State Concept:** signal assignments and cryptographic constraints

## Operating Constraints

- Hound performs static code analysis only - it cannot compile circuits, generate witnesses, or compute proofs.
- Do NOT propose or assume runtime operations (e.g., running circom compiler, generating zkey files, computing witnesses, verifying proofs).
- Do NOT suggest proof generation, trusted setup ceremonies, or on-chain verification.
- All actions here are CODE-ONLY: analyzing circuit templates, tracing signal flows, checking constraint completeness, verifying field arithmetic, and validating cryptographic primitives.

## Code Unit Prioritization (Phase 1)

Target medium-sized units: circuit templates, component instantiations, constraint blocks, cryptographic primitives

Prioritize components:
- Main circuit entry points and public signal definitions
- Modular arithmetic templates (AddModP, MulModP, division with remainder)
- Custom cryptographic primitives (BabyJubJub operations, Poseidon2 hash)
- Polynomial evaluation and secret sharing logic (EvalPolyModP, KeyGen)
- Constraint-heavy templates (subgroup checks, range validation, degree checks)
- Templates with parameters that affect constraint count or security (MAX_DEGREE, NUM_PARTIES, INDEX)
- Signal assignment and constraint patterns (especially <-- without ===)
- Field arithmetic operations (BabyJubJub scalar field vs base field)
- Encryption and commitment schemes (EncryptAndCommit, KeyGenCommit)
- Templates performing range checks, subgroup checks, or validation

## Vulnerability Categories (Phase 1 - Coverage)

Look for these vulnerability types during systematic analysis:
- **Missing constraints** - signals not fully constrained, allowing malicious provers to forge proofs
- **Underconstraint** - insufficient constraints allowing multiple valid witnesses for same public inputs
- **Signal aliasing** - different signal values satisfying same constraint equations
- **Unconstrained intermediate signals** - computed values not constrained to their inputs
- **Modular arithmetic errors** - incorrect division constraints, quotient/remainder validation
- **Polynomial evaluation bugs** - Horner's method implementation errors, coefficient handling
- **Secret sharing vulnerabilities** - degree validation failures, coefficient leakage
- **Subgroup membership failures** - elliptic curve points not checked for correct subgroup
- **Field arithmetic errors** - confusion between different finite fields (BN254 vs BabyJubJub scalar field)
- **Range check omissions** - values not validated to be within expected bounds (especially field elements)
- **Template parameter validation** - unsafe instantiation with invalid parameters (degree, indices, party counts)
- **Assignment vs constraint confusion** - using <-- instead of <== without proper constraints
- **Encryption vulnerabilities** - ECDH key derivation issues, nonce reuse, ciphertext malleability
- **Commitment binding failures** - non-binding commitments, hash collision resistance
- **Public/private signal leakage** - private information exposed through public signals or constraint patterns
- **Domain separation issues** - missing or incorrect hash function domain separators
- **Zero/identity element handling** - edge cases with zero points, identity elements not checked
- **Overflow/underflow in field arithmetic** - operations exceeding field modulus
- **Template typos and naming errors** - compilation failures, incorrect component references
- **Spec deviation** - circuit implementation not matching formal specification

## High-Impact Focus (Phase 2 - Intuition)

**Primary Impact:** SOUNDNESS BREAKS - prioritize vulnerabilities that allow proof forgery, constraint bypasses, or violations of the cryptographic security model

**Key Intuition Targets:**
1. MISSING CONSTRAINTS: Where are signals assigned but not constrained? Can a malicious prover choose arbitrary values?
2. SPEC ALIGNMENT: Where does the circuit deviate from the formal specification? Are all spec requirements enforced?
3. MODULAR ARITHMETIC: Are division constraints correct (quotient/remainder relationship)? Are field moduli enforced?
4. SECRET SHARING SECURITY: Can degree be violated? Can polynomial coefficients leak? Is encryption binding?

## Mitigation Patterns

Common security patterns to verify:
- Full constraint of all intermediate signals (every signal with <-- must have corresponding constraints)
- Modular division pattern (out <-- sum % fr; x <-- sum \ fr; sum === x * fr + out)
- Range checks using Num2Bits or CompConstant for field elements
- Quotient validation (x * (x - 1) === 0 for binary, x * (x - 1) * (x - 2) === 0 for ternary)
- Subgroup membership checks (multiply by scalar field order, check for identity)
- Domain separators in all hash function calls (unique constants in capacity elements)
- Template parameter validation (assert statements, CheckDegree template)
- Proper use of <== (constrained assignment) vs <-- (unconstrained assignment)
- Bus type safety (BabyJubJubPoint, BabyJubJubScalarField, BabyJubJubBaseField)
- Zero/identity checks (IsZero() for detecting invalid elliptic curve points)
- Field element validation (BabyJubJubIsInFr for scalar field membership)
- Explicit comments about external checks required (e.g., "Check outside ZK proof:")
- Polynomial coefficient zero-padding beyond degree (CheckDegree enforcement)
- ECDH-based encryption with proper symmetric key derivation

## Observation Examples

Good examples for graph annotations (2-4 words each):
- "unconstrained signal"
- "missing subgroup check"
- "field confusion risk"
- "requires range check"
- "modular division"
- "assignment without constraint"
- "domain separator"
- "spec requirement"
- "template parameter"
- "polynomial evaluation"
- "secret sharing"
- "ECDH encryption"
- "commitment binding"
- "degree validation"
- "quotient constrained"
- "zero-padding enforced"
- "bus type safety"
- "template typo"

## Graph Types

### Suggested Graph Types for Analysis

**SignalFlow**
Focus: How signals propagate through templates and components, tracking data dependencies
Edge types: assigns_to, constrains, depends_on, derives_from, flows_into

**ConstraintGraph**
Focus: Which signals are constrained by which equations and constraint patterns
Edge types: constrains_equal, constrains_product, constrains_sum, range_checks, validates

**ModularArithmetic**
Focus: Modular operations (addition, multiplication, division) in BabyJubJub scalar field
Edge types: adds_mod, muls_mod, divs_mod, validates_quotient, validates_remainder

**PolynomialEvaluation**
Focus: Polynomial construction, evaluation (Horner's method), and secret sharing
Edge types: defines_poly, evaluates_at, shares_secret, checks_degree, zero_pads

**EncryptionFlow**
Focus: ECDH key derivation, symmetric encryption of shares, and ciphertext generation
Edge types: derives_key, encrypts_with, uses_nonce, produces_ciphertext

**CommitmentBinding**
Focus: Commitments to polynomials, shares, and their verification
Edge types: commits_to, binds, verifies_commitment, hashes_with_sponge

**ComponentHierarchy**
Focus: Template instantiation tree showing main circuit and all nested components
Edge types: instantiates, includes, calls_template, parameterized_by

**PublicPrivateMap**
Focus: Public vs private signal boundaries and information flow
Edge types: declares_public, declares_private, leaks_to, exposes

**CryptoPrimitives**
Focus: Cryptographic operations (hashing, elliptic curves, field arithmetic)
Edge types: hashes_with, scalar_mul, point_add, uses_curve, derives_symmetric_key

**SpecAlignmentMap**
Focus: Mapping between circuit implementation and formal specification requirements
Edge types: implements_spec, deviates_from, satisfies_requirement, missing_check, spec_section

**FieldArithmetic**
Focus: Which finite field each operation uses and potential field confusion
Edge types: operates_in_field, converts_field, uses_modulus, field_mismatch

**TemplateParameters**
Focus: Template parameter usage and validation
Edge types: parameterized_by, validates_param, constrains_degree, bounds_size, array_access

**SubgroupChecks**
Focus: Elliptic curve point validation and subgroup membership
Edge types: checks_on_curve, checks_subgroup, validates_point, assumes_valid, missing_validation

**DomainSeparation**
Focus: Hash function domain separators and their usage patterns
Edge types: uses_separator, hashes_with_domain, shares_separator, missing_separator

**RangeValidation**
Focus: Range checks and bounds validation on signals
Edge types: range_checks, validates_bits, bounds, less_than, num2bits, comp_constant

## External Dependencies Examples

Common external libraries/templates to recognize (analyze if modified):
- circomlib/comparators.circom (IsZero, IsEqual, ForceEqualIfEnabled, LessThan)
- circomlib/bitify.circom (Num2Bits, Bits2Num, Num2BitsNeg)
- circomlib/compconstant.circom (CompConstant - range check helper)
- circomlib/mux1.circom, mux3.circom (Multiplexers)
- circomlib/gates.circom (AND, OR, NOT, NAND, NOR, XOR)
- circomlib/babyjub.circom (BabyCheck, BabyAdd, BabyDbl)
- circomlib/escalarmulany.circom (EscalarMulAny - arbitrary point scalar mul)
- circomlib/escalarmulfix.circom (EscalarMulFix - fixed point scalar mul)
- circomlib/montgomery.circom (Montgomery curve operations)
- circomlib/binsum.circom (Binary sum helper)
- circomlib/aliascheck.circom (Alias checking for field elements)

Note: Even standard library circuits should be analyzed if they're modified or custom implementations exist (like the custom BabyJubJub subgroup check in this project).

## Node Type Terminology

**Preferred node types:**
- Template nodes (e.g., "template_KeyGen", "template_AddModP", "template_BabyJubJubCheckInCorrectSubgroup")
- Signal nodes (e.g., "signal_input_my_sk", "signal_output_ciphertext", "signal_intermediate_sum")
- Component instantiation nodes (e.g., "component_keygen_commit", "component_derive_share", "component_poseidon2_sponge")
- Constraint nodes (e.g., "constraint_equality_line18", "constraint_product_line63")
- Field operation nodes (e.g., "field_op_add_mod", "field_op_mul_mod", "field_op_scalar_mul")
- Validation check nodes (e.g., "check_subgroup_line27", "range_check_line21", "degree_check_line410")
- Bus assignment nodes (e.g., "bus_BabyJubJubScalarField_line85", "bus_BabyJubJubPoint_line54")

## Additional Notes

### Circom-Specific Security Considerations

**Constraint Completeness:**
- Every signal must be fully determined by the constraints and inputs
- Assignments using `<--` must be followed by constraints that enforce the relationship
- The "constraint over assignment" principle: constraints define validity, assignments compute values
- Missing constraints are the #1 vulnerability class in Circom circuits

**Signal Visibility and Privacy:**
- Public signals are visible to verifiers (declared in component main {public [...]})
- Private signals must not leak information through constraint patterns or timing
- Even fully constrained circuits can leak information through the constraint structure itself

**Field Arithmetic:**
- BN254 scalar field (p = 21888242871839275222246405745257275088548364400416034343698204186575808495617): field that Circom operates in
- BabyJubJub scalar field (q = 2736030358979909402780800718157159386076813972158567259200215660948447373041): field for elliptic curve scalar multiplication
- Confusion between fields leads to incorrect constraints
- All arithmetic is modular - watch for wrap-around and negative values

**Elliptic Curve Security:**
- Points must be checked for curve membership (on the curve equation)
- Points must be checked for subgroup membership (avoiding small-order points)
- BabyJubJub has cofactor 8 - cofactor elimination or subgroup checks required
- Identity element (0, 1) must be handled explicitly
- Custom implementation in this project: BabyJubJubCheckInCorrectSubgroup multiplies by Fr and checks for identity

**Template Parameters:**
- MAX_DEGREE, NUM_PARTIES, INDEX parameters affect constraint count
- Out-of-bounds access must be prevented or have defined behavior
- Some templates work correctly only within parameter ranges (check assert statements)
- CheckDegree template enforces polynomial coefficients beyond degree are zero

**Compiler Behavior:**
- circom 2.0+ has stricter checks than circom 1.x
- `pragma circom` version affects compilation behavior
- Custom pragma flags can disable safety checks

**Specification Alignment:**
- This project has a formal specification in `oprf.typst` (Typst format)
- Each circuit component should map to a specific section of the spec
- Comments often reference spec requirements
- Verify domain separators match spec definitions
- Check that all spec requirements are enforced in constraints

### Project-Specific Context

**Project Purpose:**
This is a **threshold OPRF key generation** protocol, implementing distributed key generation (DKG) for a verifiable threshold OPRF using Shamir secret sharing.

**Key Security Properties:**
1. Soundness: Provers cannot forge proofs for invalid polynomial evaluations or commitments
2. Privacy: Polynomial coefficients remain private (only commitments public)
3. Correctness: Shares correctly evaluate polynomial at specified indices
4. Binding: Commitments bind prover to specific polynomial
5. Encryption security: Shares encrypted to specific parties cannot be read by others

**Main Components:**
- **KeyGen**: Full threshold key generation for NUM_PARTIES parties
- **KeyGenSingleParty**: Optimized version generating share for single party at fixed INDEX
- **KeyGenSinglePartyVar**: Variable index version (supports dynamic party selection)
- **AddModP, Add3ModP**: Modular addition in BabyJubJub scalar field
- **MulModP, MulModPVar**: Modular multiplication (constant and variable multiplier)
- **EvalPolyModP, EvalPolyModPVar**: Polynomial evaluation using Horner's method
- **EncryptAndCommit**: ECDH-based encryption and commitment to shares
- **CheckDegree**: Validates polynomial degree (coefficients beyond degree are zero)
- **BabyJubJubCheckInCorrectSubgroup**: Custom subgroup membership check

**Cryptographic Primitives:**
- **BabyJubJub** elliptic curve (twisted Edwards form on BN254 base field)
- **Poseidon2** hash function (zk-SNARK friendly, used in sponge mode for commitments)
- **ECDH** for symmetric key derivation (my_sk * their_pk = shared_secret)
- **Shamir Secret Sharing** via polynomial evaluation
- **Pedersen commitments** (scalar * Generator on BabyJubJub)

**Specification Reference:**
- Formal specification: `oprf.typst` (Typst document format)
- Contains cryptographic definitions, protocol flows, and security proofs
- Circuit comments may reference spec sections and requirements
- Domain separators and constants should be defined in the spec

### Known Vulnerability Patterns

**CRITICAL BUG FOUND:**
File: `oprf_keys/keygen_single_party.circom:33, 83`
```circom
component keygen_commit = KeyGenCommmit(MAX_DEGREE);  // ❌ TYPO: 3 m's!
```
Should be: `KeyGenCommit` (2 m's)
**Impact:** Compilation error - circuit will not compile
**Fix:** Correct spelling to match the actual template name

**Modular Division Constraint Pattern (CORRECT):**
From keygen.circom:15-18:
```circom
signal sum <== a + b; // No overflow possible in field
out <-- sum % fr;     // Unconstrained assignment (witness computation)
signal x <-- sum \ fr;    // Quotient (unconstrained)
sum === x * fr + out;     // CONSTRAINT: enforce division relationship
```
This is **correct** - the constraint enforces `sum = x * fr + out` where `out < fr`.
However, need to verify `out < fr` separately (done with range check on lines 21-30).

**Quotient Validation Pattern:**
From keygen.circom:32-34:
```circom
x * (x - 1) === 0;  // x must be 0 or 1
```
From keygen.circom:63-64:
```circom
signal zero_or_one <== x * (x - 1);
zero_or_one * (x - 2) === 0;  // x must be 0, 1, or 2
```
These are **correct** patterns for constraining variables to small value sets.

**Range Check with CompConstant:**
From keygen.circom:21-30:
```circom
signal bits[251] <== Num2Bits(251)(out);
component cmp_const = CompConstant(fr-1);
for(var i=0; i<251; i++) {
    cmp_const.in[i] <== bits[i];
}
cmp_const.in[251] <== 0;
cmp_const.in[252] <== 0;
cmp_const.in[253] <== 0;
cmp_const.out === 0;  // Ensures bits represent value <= (fr-1)
```
This enforces `out < fr` by checking `out <= fr - 1`.

**Polynomial Degree Enforcement:**
From keygen.circom:349-385 (CheckDegree template):
```circom
// enforce: if degree < i then poly[i] == 0
poly[i] * should_be_zeros[i] === 0;
```
Ensures coefficients beyond declared degree are zero, preventing degree manipulation.

**Encryption with ECDH:**
From keygen.circom:306-334:
```circom
component sym_key = BabyJubJubScalarMul();
sym_key.p <== pk_p;           // Other party's public key
sym_key.e <== my_sk;          // My secret key (private signal)
// Result: my_sk * their_pk = shared secret (ECDH)

var poseidon2_cipher_state[3] = Poseidon2(3)([T1_DS, sym_key.out.x, nonce]);
ciphertext <== poseidon2_cipher_state[1] + share;  // Stream cipher (XOR-like)
```
Security depends on:
1. Nonce uniqueness (must be public and unique per encryption)
2. ECDH correctness (both points in correct subgroup - **CHECK EXTERNAL**)
3. Domain separator uniqueness (T1_DS = 0x80000002000000014142)

**Subgroup Check Implementation:**
From babyjubjub/correct_sub_group.circom:12-28:
```circom
template BabyJubJubCheckInCorrectSubgroup() {
    input BabyJubJubPoint() { twisted_edwards } p;
    var characteristic[251] = [...];  // Fr bit decomposition
    signal out[2] <== EscalarMulFixScalar(characteristic)([p.x,p.y]);
    // Assert result is identity element
    BabyJubJubCheckIsIdentity()(result);
}
```
Multiplies point by scalar field order (Fr) - result must be identity if point in correct subgroup.
This is an **optimized** implementation (saves ~922 constraints vs circomlib version).

**Bus Type Safety:**
From babyjubjub/babyjubjub.circom:18-35:
```circom
bus BabyJubJubPoint { signal x; signal y; }
bus BabyJubJubBaseField { signal f; }
bus BabyJubJubScalarField { signal f; }
```
Circom 2.2+ buses provide compile-time type safety - prevent mixing field elements from different fields.

### Analysis Priorities

**Priority 1 (Critical):**
1. Find all signals assigned with `<--` and verify subsequent constraints
2. Verify modular division constraints (quotient/remainder relationships)
3. Check polynomial evaluation correctness (Horner's method, index bounds)
4. Verify CheckDegree enforcement is used correctly
5. Trace signal flow from inputs to outputs to find unconstrained paths
6. Check ECDH encryption binding (nonce uniqueness, key derivation correctness)
7. **FIX COMPILATION BUG:** Correct "KeyGenCommmit" typo in keygen_single_party.circom

**Priority 2 (High):**
1. Verify domain separators are unique and match specification
2. Check range constraints on all field elements (must be < modulus)
3. Validate quotient constraints in Add3ModP (x must be 0, 1, or 2)
4. Verify public key subgroup membership (checked externally - document requirement)
5. Check commitment binding (Poseidon2 sponge mode implementation)
6. Verify bus type safety prevents field confusion

**Priority 3 (Medium):**
1. Analyze template parameter validation (assert statements, bounds)
2. Check for signal aliasing in complex constraint systems
3. Verify correct handling of edge cases (zero polynomials, identity element)
4. Review constant values (generator point, field moduli, domain separators)
5. Check Horner's method optimization correctness (EvalPolyModP special case for INDEX == 1)

### Circuit-Specific Files

**Core Circuit Logic:**
- `oprf_keys/keygen.circom` - Main threshold key generation (390+ lines, most complex)
- `oprf_keys/keygen_single_party.circom` - Single party optimization (110 lines, **contains typo bug**)

**Cryptographic Primitives:**
- `babyjubjub/babyjubjub.circom` - Custom BabyJubJub operations with buses (150 lines)
- `babyjubjub/correct_sub_group.circom` - Optimized subgroup check (145 lines)
- `poseidon2/poseidon2.circom` - Poseidon2 hash implementation
- `poseidon2/poseidon2_constants.circom` - Round constants for Poseidon2

**Standard Library (circomlib/):**
- `comparators.circom` - IsZero, IsEqual (analyze custom usage patterns)
- `bitify.circom` - Num2Bits, Bits2Num (used for range checks)
- `compconstant.circom` - CompConstant (used in modular arithmetic)
- `babyjub.circom` - Standard BabyJubJub operations (baseline comparison)
- `escalarmulany.circom`, `escalarmulfix.circom` - Scalar multiplication
- `montgomery.circom` - Montgomery curve form operations
- Plus: mux1.circom, mux3.circom, gates.circom, binsum.circom, aliascheck.circom

**Specification:**
- `oprf.typst` - Formal mathematical specification (~50KB)
