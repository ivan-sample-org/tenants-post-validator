# from repo root
set -a
source .env
set +a

# verify
printf '%s\n' "$MONGO_URI" "$DB_NAME"
