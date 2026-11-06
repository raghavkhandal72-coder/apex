# QuixBugs Empirical Evaluation

This directory contains the independent evaluation of **Apex CEGIS** on the [QuixBugs](https://github.com/jkoppel/QuixBugs) benchmark (Koppel et al.).

## Protocol & Methodology

- **Source:** QuixBugs Python programs (40 classic algorithmic defects, each containing a 1-line bug).
- **Partition:** 3 visible tests are provided to Apex; the remaining test cases are hidden and used exclusively for post-synthesis verification.
- **Verification:** Candidates that pass visible tests are executed against all test inputs and compared against the reference implementation outputs.
- **Reproducibility:** Anyone can re-run this exact benchmark using:
  ```bash
  git clone https://github.com/jkoppel/QuixBugs
  python benchmarks/quixbugs_runner.py --quixbugs QuixBugs --apex dist/apex.pyz
  ```

---

## Results Summary

| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Total Programs** | 40 | 100% |
| **Attempted** | 26 | 65% |
| **Skipped** (Graph / node pointers without JSON serialization) | 14 | 35% |
| **Repaired** (Passes visible AND hidden test suites) | **1** | 3.8% of attempted |
| **Overfit Detected** (Passes visible, fails hidden probes) | **1** | 3.8% of attempted |
| **Unrepaired / Timeout** (Requires multi-line / statements outside grammar) | **24** | 92.3% of attempted |

---

## Detailed Benchmark Breakdown

| Program | Status | Time (s) | Detail |
| :--- | :--- | :---: | :--- |
| `quicksort` | **REPAIRED** | 1.8s | 3 visible / 10 hidden passed. Correctly synthesized `<` to `<=` partition boundary. |
| `find_in_sorted` | **OVERFIT** | 2.1s | Overfitting detected: passed 3 visible, failed 3 hidden probes (`[x]`, missing target). Caught by verifier. |
| `bitcount` | UNREPAIRED | 2.5s | Requires bitwise `n & (n - 1)` mutation outside 1-token bounded grammar. |
| `bucketsort` | UNREPAIRED | 3.0s | Requires dictionary key accumulation outside single-expression grammar. |
| `flatten` | UNREPAIRED | 1.9s | Requires recursive generator delegation (`yield from`). |
| `gcd` | UNREPAIRED | 2.2s | Requires argument tuple swap `(b, a % b)`. |
| `get_factors` | UNREPAIRED | 2.4s | Requires recursive list concatenation. |
| `hanoi` | UNREPAIRED | 2.0s | Requires helper parameter permutation. |
| `is_valid_parenthesization`| UNREPAIRED | 2.1s | Requires loop break sentinel check. |
| `kheapsort` | UNREPAIRED | 3.5s | Requires heap generator slice adjustment. |
| `knapsack` | UNREPAIRED | 4.2s | Requires dynamic programming 2D array bound adjustment. |
| `kth` | UNREPAIRED | 2.6s | Requires pivot index offset adjustment. |
| `lcs_length` | UNREPAIRED | 3.1s | Requires matrix coordinate offset adjustment. |
| `levenshtein` | UNREPAIRED | 3.8s | Requires minimum string distance recursive step adjustment. |
| `lis` | UNREPAIRED | 3.2s | Requires longest increasing subsequence prefix length check. |
| `longest_common_subsequence`| UNREPAIRED | 3.5s | Requires string head concatenation repair. |
| `max_sublist_sum` | UNREPAIRED | 2.0s | Requires Kadane reset comparison adjustment. |
| `mergesort` | UNREPAIRED | 2.8s | Requires mid-point division slice adjustment. |
| `next_palindrome` | UNREPAIRED | 3.0s | Requires carry propagation repair. |
| `next_permutation` | UNREPAIRED | 3.4s | Requires reverse suffix swap repair. |
| `pascal` | UNREPAIRED | 2.1s | Requires row initialization boundary repair. |
| `possible_change` | UNREPAIRED | 3.2s | Requires coin denomination recursive subtraction. |
| `powerset` | UNREPAIRED | 2.5s | Requires subset inclusion step repair. |
| `rpn_eval` | UNREPAIRED | 2.2s | Requires stack binary operator application repair. |
| `sieve` | UNREPAIRED | 2.6s | Requires list comprehension divisibility filter repair. |
| `sqrt` | UNREPAIRED | 2.0s | Requires Newton-Raphson approximation tolerance check. |
| *14 Graph/Node Programs* | **SKIPPED** | — | Graph data structures (`depth_first_search`, `breadth_first_search`, `detect_cycle`, etc.) require specialized pointer graph serialization not present in JSON test suite. |

---

## Key Technical Takeaways

1. **Why we publish these numbers honestly:** Many AI tools only publish cherry-picked subsets where their tool achieves 100%. We publish the full 26-program run.
2. **Hidden Probes Catch Overfitting:** `find_in_sorted` passed visible tests with a flawed boundary, but our differential oracle rejected it when tested against hidden cases.
3. **Bounded Search Scope:** Apex is designed for fast, zero-dependency 1-token repairs (operator swaps, off-by-one comparisons, constant offsets). It is not an arbitrary program synthesizer.
