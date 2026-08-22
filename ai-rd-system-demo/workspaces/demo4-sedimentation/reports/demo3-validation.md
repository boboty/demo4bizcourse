# Independent validation report｜fallback

## Overall
BLOCKER

## Independent expectation
- GC-01: FX_LOSS_PLUS_TAX_REFUND / 6200
- GC-02: TAX_REFUND_ONLY / 5000
- GC-03: TAX_REFUND_ONLY / 5000
- GC-04: NO_CANDIDATE / 0

## Actual output
- GC-01: TAX_REFUND_ONLY / 5000
- GC-02: TAX_REFUND_ONLY / 5000
- GC-03: TAX_REFUND_ONLY / 5000
- GC-04: NO_CANDIDATE / 0

## Mismatch
GC-01. The implementation skipped the combined candidate and chose the fallback candidate directly.

## Root cause classification
共同理解前提错误：实现与开发侧测试都采用了“只要退税候选存在就直接选退税”的同一理解，因此测试全绿。
