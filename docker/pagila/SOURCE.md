# Pagila source files

Vendored from [devrimgunduz/pagila](https://github.com/devrimgunduz/pagila) (PostgreSQL license), unmodified.

| File | Commit | SHA-256 |
|---|---|---|
| `pagila-schema.sql` | `ce6e114236bb828e5ec0dc835f65f1bf1b9179f5` | `071ee940a73c8f4fad2997185788065291607e2c55559e3747959e8275391536` |
| `pagila-data.sql` | `ce6e114236bb828e5ec0dc835f65f1bf1b9179f5` | `a88efa94c7ae8bc9cf55def4efc9f164d064d5b9cd93f11719ba3b5ace1602f7` |

Requires PostgreSQL 18+ with the `vector` extension.

Verify:

```bash
cd docker/pagila && shasum -a 256 -c <<'EOF'
071ee940a73c8f4fad2997185788065291607e2c55559e3747959e8275391536  pagila-schema.sql
a88efa94c7ae8bc9cf55def4efc9f164d064d5b9cd93f11719ba3b5ace1602f7  pagila-data.sql
EOF
```
