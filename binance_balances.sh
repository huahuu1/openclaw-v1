#!/usr/bin/env bash
set -euo pipefail

# Tighten permissions (idempotent)
chmod 700 ~/.openclaw/credentials 2>/dev/null || true
chmod 600 ~/.openclaw/credentials/binance.json 2>/dev/null || true

KEY=$(jq -r .apiKey ~/.openclaw/credentials/binance.json)
SECRET=$(jq -r .secretKey ~/.openclaw/credentials/binance.json)

now_ms() {
  if date +%s%3N >/dev/null 2>&1; then
    date +%s%3N
  else
    python3 - <<'PY'
import time
print(int(time.time()*1000))
PY
  fi
}

sig() { printf "%s" "$1" | openssl dgst -sha256 -hmac "$SECRET" | sed 's/^.* //'; }

get_signed() {
  local url="$1"; local extra="${2:-}";
  local ts=$(now_ms)
  local qs="timestamp=$ts&recvWindow=5000"
  [ -n "$extra" ] && qs="$qs&$extra"
  local s=$(sig "$qs")
  curl -sS -H "X-MBX-APIKEY: $KEY" "$url?$qs&signature=$s"
}

post_signed() {
  local url="$1"; local extra="${2:-}";
  local ts=$(now_ms)
  local qs="timestamp=$ts&recvWindow=5000"
  [ -n "$extra" ] && qs="$qs&$extra"
  local s=$(sig "$qs")
  curl -sS -H "X-MBX-APIKEY: $KEY" -X POST --data "$qs&signature=$s" "$url"
}

is_json() {
  jq -e . >/dev/null 2>&1
}

# Fetch all relevant accounts
SPOT=$(get_signed "https://api.binance.com/api/v3/account" "") || SPOT='{}'
UM_ACC=$(get_signed "https://fapi.binance.com/fapi/v2/account" "") || UM_ACC='{}'
UM_BAL=$(get_signed "https://fapi.binance.com/fapi/v2/balance" "") || UM_BAL='[]'
CM_ACC=$(get_signed "https://dapi.binance.com/dapi/v1/account" "") || CM_ACC='{}'
FUND=$(post_signed "https://api.binance.com/sapi/v1/asset/getFundingAsset" "") || FUND='[]'
MARGIN=$(get_signed "https://api.binance.com/sapi/v1/margin/account" "") || MARGIN='{}'

# Normalize to JSON if endpoints failed (avoid HTML/strings)
printf '%s' "$SPOT" | is_json || SPOT='{}'
printf '%s' "$UM_ACC" | is_json || UM_ACC='{}'
printf '%s' "$UM_BAL" | is_json || UM_BAL='[]'
printf '%s' "$CM_ACC" | is_json || CM_ACC='{}'
printf '%s' "$FUND" | is_json || FUND='[]'
printf '%s' "$MARGIN" | is_json || MARGIN='{}'

# Build non-zero lists
SPOT_NZ=$(printf '%s' "$SPOT" | jq -c '[.balances[]? | select((.free|tonumber)!=0 or (.locked|tonumber)!=0) | {asset, free, locked}]')
UM_NZ=$(printf '%s' "$UM_ACC" | jq -c '[.assets[]? | select((.walletBalance|tonumber)!=0 or (.crossWalletBalance|tonumber)!=0 or (.availableBalance|tonumber)!=0) | {asset, walletBalance, crossWalletBalance, availableBalance}]')
# Combine UM balance endpoint (accountBalance field) for completeness
UM_BAL_NZ=$(printf '%s' "$UM_BAL" | jq -c '[.[]? | select((.accountBalance|tonumber)!=0 or (.crossWalletBalance|tonumber)!=0 or (.availableBalance|tonumber)!=0) | {asset, accountBalance, crossWalletBalance, availableBalance}]')
CM_NZ=$(printf '%s' "$CM_ACC" | jq -c '[.assets[]? | select((.walletBalance|tonumber)!=0 or (.crossWalletBalance|tonumber)!=0 or (.availableBalance|tonumber)!=0) | {asset, walletBalance, crossWalletBalance, availableBalance}]')
FUND_NZ=$(printf '%s' "$FUND" | jq -c '[.[]? | select((.free|tonumber)!=0) | {asset, free}]')
MARGIN_NZ=$(printf '%s' "$MARGIN" | jq -c '[.userAssets[]? | select(((.netAsset|tonumber)!=0) or ((.free|tonumber)!=0) or ((.locked|tonumber)!=0) or ((.borrowed|tonumber)!=0) or ((.interest|tonumber)!=0)) | {asset, free, locked, borrowed, interest, netAsset}]')

jq -cn \
  --argjson spot $SPOT_NZ \
  --argjson um $UM_NZ \
  --argjson umbal $UM_BAL_NZ \
  --argjson cm $CM_NZ \
  --argjson fund $FUND_NZ \
  --argjson margin $MARGIN_NZ \
  '{spot: $spot, futuresUM: $um, futuresUM_balance: $umbal, futuresCM: $cm, funding: $fund, margin: $margin}'
