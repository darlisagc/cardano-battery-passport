## Bug: `/ by zero` error in `/api/v1/transaction/build` for wallets with stale State Datum (preprod)

### Summary

Wallets that previously issued certificates via the UVerify SDK/UI on **preprod** receive a server-side `/ by zero` error on every subsequent call to `/api/v1/transaction/build`. The error also surfaces in the web UI at `app.preprod.uverify.io/create#` as _"Transaction building failed or has been aborted. Please try again."_ The issue is **wallet-specific** — fresh wallets (with no prior State Datum) work normally.

### Environment

- **Network:** Cardano Preprod
- **API:** `api.preprod.uverify.io`
- **SDK:** `uverify-sdk` v0.1.8 (Python)
- **Web UI:** `app.preprod.uverify.io/create#`

### Steps to reproduce

**Via API (curl):**

```bash
curl -X POST https://api.preprod.uverify.io/api/v1/transaction/build \
  -H "Content-Type: application/json" \
  -d '{
    "address": "addr_test1qq0e67g4fcdff7zwmv0ngxjvhzdy7xnq37vet4n8xvq6xrsxsm8j5rq7mfzdjaqshzutavy8lnq68l25ekhtf2kcj7rsyvuljn",
    "certificates": [{
      "gtin": "0000000000000",
      "serialNumber": "bug-repro-test",
      "templateId": "digitalProductPassport",
      "fields": {"name": "Bug Repro", "issuer": "Test"}
    }]
  }'
```

**Via Web UI:**

1. Open https://app.preprod.uverify.io/create#
2. Connect the affected wallet (address above)
3. Fill in any valid DPP fields and click "Create"
4. Observe error toast: _"Transaction building failed or has been aborted."_

**Via Python SDK:**

```python
from uverify import UVerifyClient, CertificateData, BuildTransactionRequest

client = UVerifyClient(base_url="https://api.preprod.uverify.io")
cert = CertificateData(
    gtin="0000000000000",
    serial_number="bug-repro-test",
    template_id="digitalProductPassport",
    fields={"name": "Bug Repro", "issuer": "Test"},
)
# This call raises UVerifyApiError: / by zero
client.issue_certificates(address="addr_test1qq0e67g4fcdff7zwmv0ngxjvhzdy7xnq37vet4n8xvq6xrsxsm8j5rq7mfzdjaqshzutavy8lnq68l25ekhtf2kcj7rsyvuljn",
                          certificates=[cert], sign_tx=my_sign_fn)
```

### Expected behavior

The API should return a CBOR-hex transaction for signing (HTTP 200), or a descriptive error if the state needs migration.

### Actual behavior

- **API response:** HTTP 400/500 with body `{"message": "/ by zero", "code": "UNKNOWN_ERROR"}` (or empty body on 500)
- **Web UI console:**
  ```
  UVerifyApiError: / by zero
      at _S.request (index-BFLgN_lK.js:1288:10868)
      at async ge (index-BFLgN_lK.js:3355:146401)
  ```

### Root cause analysis

We performed systematic debugging and identified the following:

**1. The error is wallet-specific, not global.**

| Test | Result |
|------|--------|
| Affected wallet → `/transaction/build` | `/ by zero` (400/500) |
| Fresh wallet (no prior state) → `/transaction/build` | Success (200) |
| Affected wallet → `/api/v1/verify/{hash}` | Works (200) |
| Same payload, different wallet | Works (200) |

**2. The wallet has a stale State Datum referencing an obsolete Bootstrap Datum.**

The affected wallet's first SDK emission (tx [`e88b6213...`](https://preprod.cexplorer.io/tx/e88b6213ef58d9c125a5265b5cf8257f4fbbc60eb69b68b4d4409b96bdcd0d4b)) created a State Datum at the script address `addr_test1wp5lpz8sarnl9j6um86vf3u5725z3s9da7wdn49c6570ukggng4dg`. This State Datum is **still unspent** and contains:

```
State Datum (decoded from inline CBOR):
  [0] stateNftName:   7eaa6927...47f834
  [1] ownerPkh:       1f9d7915...f61ef
  [2] fee:            0
  [3] feeInterval:    10
  [4] extraFields:    []
  [5] expirationPosix: 2526955802000
  [6] countdown:      80
  [7] bootstrapRef:   d0942baecfa61618f01472adb8e5778f3a51ea3d9f1b6553bd44eae12b8986b3
  [8] batchSize:      1
  [9] platformTag:    "uverify"
  [10] extensionData: (empty)
```

**3. The Bootstrap Datum referenced by this state (`d0942bae...`) no longer matches the current platform Bootstrap.**

Fresh wallets receive State Datums derived from a **newer** Bootstrap Datum (`689e10fa...`). The old Bootstrap's parameters likely have a different fee structure that causes a division-by-zero when the current validator/API logic processes it.

**4. State UTxO lifecycle confirms the stale state.**

- Original state UTxO from tx `e88b6213` (output 0) → **UNSPENT** (still sitting at the script address)
- Subsequent state UTxOs from later emissions → all **SPENT** (consumed)
- The API finds the unspent (stale) state and fails when computing fees against the obsolete Bootstrap parameters

### Impact

- Any wallet that issued certificates during an earlier Bootstrap era on preprod is permanently blocked from issuing new certificates via the API or web UI
- The locked ADA (~1.73 ADA per State Datum) cannot be reclaimed by the user
- No workaround exists within the API — users must switch to a fresh wallet

### Suggested fix

1. **Graceful handling:** When the API encounters a State Datum referencing an outdated Bootstrap, it should either migrate the state to the current Bootstrap or return a descriptive error (e.g., `"State Datum references obsolete Bootstrap. Please invalidate and recreate."`)
2. **State invalidation endpoint:** Provide a way for users to burn a stale State NFT and reclaim the locked ADA (an `/api/v1/state/invalidate` endpoint, or a UI option)
3. **Arithmetic safety:** The fee calculation that divides should guard against zero denominators regardless of Bootstrap version

### On-chain references (preprod)

| Item | Value |
|------|-------|
| Affected wallet address | `addr_test1qq0e67g4fcdff7zwmv0ngxjvhzdy7xnq37vet4n8xvq6xrsxsm8j5rq7mfzdjaqshzutavy8lnq68l25ekhtf2kcj7rsyvuljn` |
| State Datum tx | [`e88b6213ef58d9c125a5265b5cf8257f4fbbc60eb69b68b4d4409b96bdcd0d4b`](https://preprod.cexplorer.io/tx/e88b6213ef58d9c125a5265b5cf8257f4fbbc60eb69b68b4d4409b96bdcd0d4b) |
| State Datum UTxO | `e88b6213...#0` (unspent) |
| Stale Bootstrap ref | `d0942baecfa61618f01472adb8e5778f3a51ea3d9f1b6553bd44eae12b8986b3` |
| Current Bootstrap ref | `689e10fa...` (used by fresh wallets) |
| Script address | `addr_test1wp5lpz8sarnl9j6um86vf3u5725z3s9da7wdn49c6570ukggng4dg` |
| State NFT policy + name | `69f088f0e8e7f2cb5cd9f4c4c794f2a828c0adef9cd9d4b8d53cfe59` + `7eaa692797ff56fea66b079beecc7a5956fcab59926f642b9006891bde47f834` |
| Inline datum hash | `8e072f52858983939808b8bae25056ea4c3ffaeb29339d1f6f9b1384626ed1f0` |
