#!/usr/bin/env bash
set -euo pipefail

# Stock Manager - Interactive Setup Wizard
# Guides users through environment setup, KIS API authentication, and
# optional Slack integration for the stock-manager trading application.

# --- Constants ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
VENV_DIR="${SCRIPT_DIR}/.venv"
STATE_DIR="${HOME}/.stock_manager"
TOTAL_STEPS=5
CURRENT_STEP=0
PYTHON_CMD=""
PKG_MANAGER=""
HC_PASS=0; HC_FAIL=0; HC_SKIP=0
LAST_KIS_ACCESS_TOKEN=""
LAST_KIS_TOKEN_OK="false"
LAST_KIS_EXPIRES_IN=""

# --- Color Setup ---
setup_colors() {
    if [[ -t 1 ]] && command -v tput &>/dev/null && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
        RED="$(tput setaf 1)"; GREEN="$(tput setaf 2)"; YELLOW="$(tput setaf 3)"
        BLUE="$(tput setaf 4)"; BOLD="$(tput bold)"
        DIM="$(tput dim 2>/dev/null || echo '')"; RESET="$(tput sgr0)"
    else
        RED="" GREEN="" YELLOW="" BLUE="" BOLD="" DIM="" RESET=""
    fi
}

# --- Output Helpers ---
print_header() {
    echo ""
    echo "  ${BOLD}============================================${RESET}"
    echo "  ${BOLD}  Stock Manager - Interactive Setup Wizard${RESET}"
    echo "  ${BOLD}  v0.1.0${RESET}"
    echo "  ${BOLD}============================================${RESET}"
    echo ""
}
print_step()    { CURRENT_STEP=$((CURRENT_STEP + 1)); echo ""; echo "${BOLD}${BLUE}[Step ${CURRENT_STEP}/${TOTAL_STEPS}] $1${RESET}"; }
print_info()    { echo "  ${BLUE}$1${RESET}"; }
print_success() { echo "  ${GREEN}[OK]${RESET} $1"; }
print_warning() { echo "  ${YELLOW}[WARN]${RESET} $1"; }
print_error()   { echo "  ${RED}[ERROR]${RESET} $1"; }
print_skip()    { echo "  ${DIM}[SKIP]${RESET} $1"; }

# --- Prompt Helpers ---
prompt_yes_no() {
    local prompt="$1" default="${2:-y}" hint
    if [[ "$default" == "y" ]]; then hint="Y/n"; else hint="y/N"; fi
	    while true; do
	        printf "  %s (%s): " "$prompt" "$hint"
	        read -r answer
	        answer="${answer:-$default}"
	        # macOS ships Bash 3.2 by default, which doesn't support ${var,,}.
	        case "$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')" in
	            y|yes) return 0 ;; n|no) return 1 ;;
	            *) echo "  Please answer y or n." ;;
	        esac
	    done
	}

prompt_input() {
    local prompt="$1" default="${2:-}"
    # IMPORTANT: print prompts to stderr so command-substitution captures only the value.
    if [[ -n "$default" ]]; then printf "  %s [%s]: " "$prompt" "$default" >&2
    else printf "  %s: " "$prompt" >&2; fi
    read -r answer
    printf '%s\n' "${answer:-$default}"
}

prompt_secret() {
    local prompt="$1" value
    # IMPORTANT: print prompts to stderr so command-substitution captures only the value.
    printf "  %s: " "$prompt" >&2
    read -rsp "" value
    echo "" >&2
    printf '%s\n' "$value"
}

# --- Core Helpers ---
mask_secret() {
    local value="$1" len=${#1}
    if [[ $len -le 8 ]]; then echo "****"
    else echo "${value:0:4}...${value:$((len-4)):4}"; fi
}

backup_env() {
    if [[ -f "$ENV_FILE" ]]; then
        local backup="${ENV_FILE}.backup.$(date +%Y%m%d-%H%M%S)"
        cp "$ENV_FILE" "$backup"
        print_info "Backed up .env to $(basename "$backup")"
    fi
}

set_env_var() {
    local key="$1" value="$2" file="${3:-$ENV_FILE}"
    if [[ -f "$file" ]]; then
        if [[ "$(uname)" == "Darwin" ]]; then sed -i '' "/^#*${key}=/d" "$file"
        else sed -i "/^#*${key}=/d" "$file"; fi
    fi
    printf '%s=%s\n' "$key" "$value" >> "$file"
}

get_env_var() {
    local key="$1" file="${2:-$ENV_FILE}"
    if [[ -f "$file" ]]; then
        local raw
        raw="$(grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | awk -F '=' '{print substr($0, index($0,"=")+1)}')"
        # Strip surrounding quotes to support dotenv-style KEY="value"
        raw="${raw%\"}"; raw="${raw#\"}"
        raw="${raw%\'}"; raw="${raw#\'}"
        echo "$raw"
    else echo ""; fi
}

check_command() { command -v "$1" &>/dev/null; }
cleanup() { stty echo 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Resolve KIS base URL and OAuth path from KIS_USE_MOCK value.
# Sets: _KIS_BASE_URL, _KIS_OAUTH_PATH, _KIS_TRADING_MODE
resolve_kis_urls() {
    local mock="$1"
    if [[ "$mock" == "true" ]]; then
        _KIS_BASE_URL="https://openapivts.koreainvestment.com:29443"
        _KIS_OAUTH_PATH="/oauth2/tokenP"
        _KIS_TRADING_MODE="paper"
    else
        _KIS_BASE_URL="https://openapi.koreainvestment.com:9443"
        _KIS_OAUTH_PATH="/oauth2/tokenP"
        _KIS_TRADING_MODE="real"
    fi
}

# Attempt KIS OAuth token issuance. Prints token on success, empty on failure.
# Usage: token=$(try_kis_token "$app_key" "$app_secret" "$base_url" "$oauth_path")
try_kis_token() {
    local key="$1" secret="$2" url="$3" path="$4"
    local body
    body="$(curl -s --connect-timeout 10 --max-time 30 \
        -X POST "${url}${path}" \
        -H "Content-Type: application/json; charset=utf-8" \
        -H "appkey: ${key}" -H "appsecret: ${secret}" -H "custtype: P" \
        -d "{\"grant_type\":\"client_credentials\",\"appkey\":\"${key}\",\"appsecret\":\"${secret}\"}" \
        2>/dev/null)" || true
    if [[ -n "$body" ]]; then
        echo "$body" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || true
    fi
}

# Parse a JSON field from stdin. Usage: echo "$json" | json_field "key"
json_field() {
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$1',''))" 2>/dev/null || true
}

# Test Slack auth.test. Prints "true" or "false".
try_slack_auth() {
    local token="$1"
    local resp
    resp="$(curl -s --connect-timeout 10 --max-time 30 \
        -X POST "https://slack.com/api/auth.test" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" 2>/dev/null)" || true
    if [[ -n "$resp" ]]; then
        echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('ok',False)).lower())" 2>/dev/null || echo "false"
    else echo "false"; fi
}

# =============================================================================
# Phase 1: System Prerequisites
# =============================================================================
phase_1_prerequisites() {
    print_step "System Prerequisites"

    # Check Python >= 3.10
    print_info "Checking Python version..."
    PYTHON_CMD=""
    for cmd in python3 python; do
        if check_command "$cmd"; then
            local ver major minor
            ver="$($cmd --version 2>&1 | awk '{print $2}')"
            major="$(echo "$ver" | cut -d. -f1)"; minor="$(echo "$ver" | cut -d. -f2)"
            if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 10 ]]; then
                PYTHON_CMD="$cmd"; print_success "Python ${ver}"; break
            fi
        fi
    done
    if [[ -z "$PYTHON_CMD" ]]; then
        print_error "Python >= 3.10 is required but not found."
        print_info "Install from https://python.org or use pyenv:"
        print_info "  curl https://pyenv.run | bash && pyenv install 3.13.1"
        return 1
    fi

    # Check package manager
    print_info "Checking package manager..."
    PKG_MANAGER=""
    if check_command uv; then
        PKG_MANAGER="uv"; print_success "uv $(uv --version 2>&1 | awk '{print $2}')"
    elif check_command pip3; then
        PKG_MANAGER="pip3"; print_success "pip3 detected (uv recommended for faster installs)"
    elif check_command pip; then
        PKG_MANAGER="pip"; print_success "pip detected (uv recommended for faster installs)"
    else
        print_warning "No package manager found. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi

    # Virtual environment
    print_info "Checking virtual environment..."
    if [[ -d "$VENV_DIR" ]] && [[ -f "$VENV_DIR/bin/python" ]]; then
        print_success "Virtual environment detected at .venv"
        if prompt_yes_no "Recreate virtual environment?" "n"; then
            rm -rf "$VENV_DIR"
            if [[ "$PKG_MANAGER" == "uv" ]]; then uv venv "$VENV_DIR"
            else "$PYTHON_CMD" -m venv "$VENV_DIR"; fi
            print_success "Virtual environment recreated"
        fi
    else
        print_info "Creating virtual environment..."
        if [[ "$PKG_MANAGER" == "uv" ]]; then uv venv "$VENV_DIR"
        else "$PYTHON_CMD" -m venv "$VENV_DIR"; fi
        print_success "Virtual environment created at .venv"
    fi

    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
    print_success "Virtual environment activated"

    # Install dependencies
    print_info "Installing dependencies..."
    if [[ "$PKG_MANAGER" == "uv" ]] && [[ -f "${SCRIPT_DIR}/uv.lock" ]]; then
        uv sync --extra dev --extra cli
    elif [[ "$PKG_MANAGER" == "uv" ]]; then
        uv pip install -e ".[dev,cli]"
    else
        "$PKG_MANAGER" install -e ".[dev,cli]"
    fi

    if python -c "import stock_manager; print('OK')" &>/dev/null; then
        print_success "Dependencies installed and verified"
    else
        print_error "Failed to import stock_manager after install"; return 1
    fi

    # State directory
    print_info "Checking state directory..."
    mkdir -p "$STATE_DIR"
    if touch "${STATE_DIR}/.setup_test" 2>/dev/null && rm -f "${STATE_DIR}/.setup_test"; then
        print_success "State directory ${STATE_DIR}/ is writable"
    else
        print_error "Cannot write to ${STATE_DIR}/ - check permissions"; return 1
    fi
}

# =============================================================================
# Phase 2: Environment Configuration
# =============================================================================
phase_2_env_config() {
    print_step "Environment Configuration"

    if [[ -f "$ENV_FILE" ]]; then
        print_info "Existing .env file found."
        backup_env
        if ! prompt_yes_no "Reconfigure environment variables?" "y"; then
            print_info "Keeping current .env configuration."; return 0
        fi
    else
        if [[ -f "$ENV_EXAMPLE" ]]; then cp "$ENV_EXAMPLE" "$ENV_FILE"; print_info "Created .env from .env.example"
        else touch "$ENV_FILE"; print_info "Created new .env file"; fi
    fi

    # Prefer Python-based wizard (more robust quoting + validation).
    if [[ -x "${VENV_DIR}/bin/python" ]]; then
        echo ""; print_info "Launching Python setup wizard for .env..."
        if "${VENV_DIR}/bin/python" -m stock_manager.main setup --skip-verify; then
            echo ""; print_success "Environment saved to .env"
            return 0
        else
            print_warning "Python setup wizard failed; falling back to Bash prompts."
        fi
    else
        print_warning "Virtual environment python not found; using Bash prompts."
    fi

    # -- KIS API Credentials --
    echo ""; print_info "-- KIS API Credentials (Required) --"

    local app_key
    app_key="$(prompt_secret "Enter KIS App Key")"
    while [[ -z "$app_key" ]]; do
        print_error "App Key cannot be empty."; app_key="$(prompt_secret "Enter KIS App Key")"
    done
    set_env_var "KIS_APP_KEY" "$app_key"
    print_success "KIS_APP_KEY set ($(mask_secret "$app_key"))"

    local app_secret
    app_secret="$(prompt_secret "Enter KIS App Secret")"
    while [[ -z "$app_secret" ]]; do
        print_error "App Secret cannot be empty."; app_secret="$(prompt_secret "Enter KIS App Secret")"
    done
    set_env_var "KIS_APP_SECRET" "$app_secret"
    print_success "KIS_APP_SECRET set ($(mask_secret "$app_secret"))"

    # Trading mode
    if prompt_yes_no "Use paper trading (recommended for testing)?" "y"; then
        set_env_var "KIS_USE_MOCK" "true"; print_success "Paper trading mode enabled"
    else
        echo ""; print_warning "REAL TRADING MODE: Actual money will be used for transactions."
        if prompt_yes_no "Are you sure you want to enable real trading?" "n"; then
            set_env_var "KIS_USE_MOCK" "false"; print_warning "Real trading mode enabled"
        else
            set_env_var "KIS_USE_MOCK" "true"; print_success "Paper trading mode enabled (reverted)"
        fi
    fi

    # Account
    local account_num
    account_num="$(prompt_input "Enter Account Number")"
    while [[ -z "$account_num" ]]; do
        print_error "Account number cannot be empty."; account_num="$(prompt_input "Enter Account Number")"
    done
    set_env_var "KIS_ACCOUNT_NUMBER" "$account_num"; print_success "KIS_ACCOUNT_NUMBER set"

    local product_code
    product_code="$(prompt_input "Account Product Code" "01")"
    set_env_var "KIS_ACCOUNT_PRODUCT_CODE" "$product_code"

    # -- Trading Parameters --
    echo ""; print_info "-- Trading Parameters --"
    local max_pos
    max_pos="$(prompt_input "Max Position Size (KRW)" "100000")"
    while ! [[ "$max_pos" =~ ^[0-9]+$ ]]; do
        print_error "Must be a numeric value."; max_pos="$(prompt_input "Max Position Size (KRW)" "100000")"
    done
    set_env_var "MAX_POSITION_SIZE" "$max_pos"

    local max_loss
    max_loss="$(prompt_input "Max Daily Loss (KRW)" "1000")"
    while ! [[ "$max_loss" =~ ^[0-9]+$ ]]; do
        print_error "Must be a numeric value."; max_loss="$(prompt_input "Max Daily Loss (KRW)" "1000")"
    done
    set_env_var "MAX_DAILY_LOSS" "$max_loss"

    # -- Slack Notifications (Optional) --
    echo ""; print_info "-- Slack Notifications (Optional) --"
    if prompt_yes_no "Configure Slack notifications?" "n"; then
        set_env_var "SLACK_ENABLED" "true"
        local bot_token
        bot_token="$(prompt_secret "Enter Slack Bot Token (xoxb-...)")"
        while [[ -z "$bot_token" ]] || [[ "${bot_token:0:5}" != "xoxb-" ]]; do
            print_error "Bot token must start with 'xoxb-'."
            bot_token="$(prompt_secret "Enter Slack Bot Token (xoxb-...)")"
        done
        set_env_var "SLACK_BOT_TOKEN" "$bot_token"
        print_success "SLACK_BOT_TOKEN set ($(mask_secret "$bot_token"))"

        local default_ch; default_ch="$(prompt_input "Default Channel (e.g. C001CHANNEL or #general)")"
        set_env_var "SLACK_DEFAULT_CHANNEL" "$default_ch"
        local order_ch; order_ch="$(prompt_input "Order Channel (leave empty for default)" "$default_ch")"
        set_env_var "SLACK_ORDER_CHANNEL" "$order_ch"
        local alert_ch; alert_ch="$(prompt_input "Alert Channel (leave empty for default)" "$default_ch")"
        set_env_var "SLACK_ALERT_CHANNEL" "$alert_ch"

        echo ""; print_info "Minimum notification level:"
        print_info "  1) DEBUG  2) INFO  3) WARNING  4) ERROR"
        local level_choice; level_choice="$(prompt_input "Choose level" "2")"
        case "$level_choice" in
            1) set_env_var "SLACK_MIN_LEVEL" "DEBUG" ;; 3) set_env_var "SLACK_MIN_LEVEL" "WARNING" ;;
            4) set_env_var "SLACK_MIN_LEVEL" "ERROR" ;; *) set_env_var "SLACK_MIN_LEVEL" "INFO" ;;
        esac
    else
        set_env_var "SLACK_ENABLED" "false"; print_skip "Slack not configured"
    fi

    # -- Runtime --
    echo ""; print_info "-- Runtime Settings --"
    print_info "Log level options:"; print_info "  1) DEBUG  2) INFO  3) WARNING  4) ERROR"
    local log_choice; log_choice="$(prompt_input "Choose log level" "2")"
    case "$log_choice" in
        1) set_env_var "LOG_LEVEL" "DEBUG" ;; 3) set_env_var "LOG_LEVEL" "WARNING" ;;
        4) set_env_var "LOG_LEVEL" "ERROR" ;; *) set_env_var "LOG_LEVEL" "INFO" ;;
    esac

    echo ""; print_success "Environment saved to .env"
}

# =============================================================================
# Phase 3: KIS API Authentication Test
# =============================================================================
phase_3_kis_api_test() {
    print_step "KIS API Authentication Test"

    local app_key app_secret kis_use_mock
    app_key="$(get_env_var "KIS_APP_KEY")"
    app_secret="$(get_env_var "KIS_APP_SECRET")"
    kis_use_mock="$(get_env_var "KIS_USE_MOCK")"

    if [[ -z "$app_key" ]] || [[ -z "$app_secret" ]]; then
        print_error "KIS_APP_KEY or KIS_APP_SECRET not found in .env"
        print_info "Run this script again to configure credentials."; return 1
    fi

    resolve_kis_urls "$kis_use_mock"
    print_info "Testing token issuance (${_KIS_TRADING_MODE} trading)..."
    print_info "OAuth endpoint: ${_KIS_OAUTH_PATH}"

    local attempt=0 max_attempts=3 token_ok=false
    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))

        local response
        response="$(curl -s -w "\n%{http_code}" \
            --connect-timeout 10 --max-time 30 \
            -X POST "${_KIS_BASE_URL}${_KIS_OAUTH_PATH}" \
            -H "Content-Type: application/json; charset=utf-8" \
            -H "appkey: ${app_key}" -H "appsecret: ${app_secret}" -H "custtype: P" \
            -d "{\"grant_type\":\"client_credentials\",\"appkey\":\"${app_key}\",\"appsecret\":\"${app_secret}\"}" \
            2>/dev/null)" || true

        local body; body="$(echo "$response" | sed '$d')"

        if [[ -z "$body" ]]; then
            print_error "No response from KIS API (attempt ${attempt}/${max_attempts})"
            if [[ $attempt -lt $max_attempts ]]; then
                if prompt_yes_no "Retry?" "y"; then continue; else break; fi
            fi; continue
        fi

	    local access_token msg1
	    access_token="$(echo "$body" | json_field "access_token")"
	    if [[ -n "$access_token" ]]; then
	        local token_type expires_in
	        token_type="$(echo "$body" | json_field "token_type")"
	        expires_in="$(echo "$body" | json_field "expires_in")"
            print_success "Token issued successfully!"
	        print_info "  Token: $(mask_secret "$access_token")"
	        print_info "  Type: ${token_type:-Bearer}"
	        print_info "  Expires: ${expires_in:-86400}s (24 hours)"
	        LAST_KIS_ACCESS_TOKEN="$access_token"
	        LAST_KIS_TOKEN_OK="true"
	        LAST_KIS_EXPIRES_IN="${expires_in:-86400}"
	        token_ok=true; break
	    else
            msg1="$(echo "$body" | json_field "msg1")"
            local rt_cd; rt_cd="$(echo "$body" | json_field "rt_cd")"
            print_error "Token issuance failed (attempt ${attempt}/${max_attempts})"
            [[ -n "$msg1" ]] && print_error "  API message: ${msg1}"
            [[ -n "$rt_cd" ]] && print_error "  Return code: ${rt_cd}"
            if [[ $attempt -lt $max_attempts ]]; then
                if ! prompt_yes_no "Retry?" "y"; then break; fi
            fi
        fi
    done

	    if [[ "$token_ok" != "true" ]]; then
	        print_warning "KIS API token test failed. You can re-run setup later."
	        if prompt_yes_no "Continue with remaining setup?" "y"; then return 0; else return 1; fi
	    fi

	    # Best-effort: write token to the Python token cache so subsequent runs won't re-issue
	    # (KIS OAuth is rate-limited, e.g. 1/min).
	    if [[ -n "$LAST_KIS_ACCESS_TOKEN" ]] && [[ -x "${VENV_DIR}/bin/python" ]]; then
	        KIS_ACCESS_TOKEN="$LAST_KIS_ACCESS_TOKEN" KIS_EXPIRES_IN="${LAST_KIS_EXPIRES_IN:-86400}" \
	            "${VENV_DIR}/bin/python" - 2>/dev/null <<'PY' || true
from datetime import datetime, timedelta, timezone
import os

from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
from stock_manager.adapters.broker.kis.token_cache import save_cached_token

cfg = KISConfig()
token = os.getenv("KIS_ACCESS_TOKEN", "").strip()
expires_in = int(os.getenv("KIS_EXPIRES_IN", "86400") or "86400")
expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

if token:
    save_cached_token(
        cfg.get_token_cache_path(),
        token=KISAccessToken(access_token=token),
        expires_at=expires_at,
        app_key=cfg.app_key.get_secret_value(),
        api_base_url=cfg.api_base_url,
        oauth_path=cfg.oauth_path,
    )
PY
	    fi

	    # Python API test (Samsung 005930)
	    echo ""; print_info "Testing API call (Samsung 005930 price)..."
	    if [[ -f "${VENV_DIR}/bin/python" ]]; then
	        local api_result
	        api_result="$(
	            KIS_ACCESS_TOKEN="${LAST_KIS_ACCESS_TOKEN}" "${VENV_DIR}/bin/python" - 2>&1 <<'PY'
from stock_manager.adapters.broker.kis.apis.domestic_stock.basic import inquire_current_price
from stock_manager.adapters.broker.kis.client import KISRestClient
from stock_manager.adapters.broker.kis.config import KISAccessToken, KISConfig
import os
from stock_manager.adapters.broker.kis.exceptions import KISAPIError

config = KISConfig()
is_paper = config.use_mock

with KISRestClient(config) as client:
    token = os.getenv("KIS_ACCESS_TOKEN", "").strip()
    if token:
        client.state.update_token(KISAccessToken(access_token=token))
    else:
        # Fallback: issue token (may be rate-limited by KIS).
        client.authenticate()

    try:
        result = inquire_current_price(client, "005930", is_paper_trading=is_paper)
        if result.get("rt_cd") == "0":
            price = result.get("output", {}).get("stck_prpr", "N/A")
            print(f"Samsung (005930) current price: {price} KRW")
        else:
            msg = result.get("msg1", "Unknown error")
            print(f"API error: {msg}")
    except KISAPIError as e:
        print(f"API error: {e}")
PY
	        )" || true
	        if [[ -n "$api_result" ]] && [[ "$api_result" != *"error"* ]] && [[ "$api_result" != *"Error"* ]] && [[ "$api_result" != *"Traceback"* ]]; then
	            print_success "$api_result"
	        else
	            print_warning "API call test returned an issue:"
	            print_info "  ${api_result:-No output}"
	            print_info "  This may be normal outside market hours."
	        fi
	    else
	        print_skip "Python API test skipped (venv not available)"
	    fi
}

# =============================================================================
# Phase 4: Slack Integration (Optional)
# =============================================================================
phase_4_slack() {
    print_step "Slack Integration"

    local slack_enabled; slack_enabled="$(get_env_var "SLACK_ENABLED")"
    if [[ "$slack_enabled" != "true" ]]; then
        print_skip "Slack not configured, skipping."; return 0
    fi

    local bot_token; bot_token="$(get_env_var "SLACK_BOT_TOKEN")"
    if [[ -z "$bot_token" ]] || [[ "${bot_token:0:5}" != "xoxb-" ]]; then
        print_error "Invalid Slack bot token (must start with 'xoxb-')."
        print_info "Reconfigure Slack in Phase 2 by re-running setup."; return 0
    fi

    print_info "Testing Slack API connectivity..."
    local resp
    resp="$(curl -s --connect-timeout 10 --max-time 30 \
        -X POST "https://slack.com/api/auth.test" \
        -H "Authorization: Bearer ${bot_token}" \
        -H "Content-Type: application/json" 2>/dev/null)" || true

    if [[ -z "$resp" ]]; then print_error "No response from Slack API."; return 0; fi

    local ok; ok="$(echo "$resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('ok',False)).lower())" 2>/dev/null)" || true
    if [[ "$ok" == "true" ]]; then
        local bot_name team
        bot_name="$(echo "$resp" | json_field "user")"
        team="$(echo "$resp" | json_field "team")"
        print_success "Slack authenticated as @${bot_name} in ${team}"
    else
        local err; err="$(echo "$resp" | json_field "error")"
        print_error "Slack auth failed: ${err}"
        print_info "Check your bot token and try again."; return 0
    fi

    # Send test message
    local default_channel; default_channel="$(get_env_var "SLACK_DEFAULT_CHANNEL")"
    if [[ -n "$default_channel" ]] && prompt_yes_no "Send test message to ${default_channel}?" "y"; then
        local msg_resp
        msg_resp="$(curl -s --connect-timeout 10 --max-time 30 \
            -X POST "https://slack.com/api/chat.postMessage" \
            -H "Authorization: Bearer ${bot_token}" \
            -H "Content-Type: application/json" \
            -d "{\"channel\":\"${default_channel}\",\"text\":\"[stock-manager] Setup test - Slack verified!\"}" \
            2>/dev/null)" || true
        local msg_ok; msg_ok="$(echo "$msg_resp" | python3 -c "import json,sys; d=json.load(sys.stdin); print(str(d.get('ok',False)).lower())" 2>/dev/null)" || true
        if [[ "$msg_ok" == "true" ]]; then print_success "Test message sent to ${default_channel}"
        else
            local msg_err; msg_err="$(echo "$msg_resp" | json_field "error")"
            print_warning "Could not send test message: ${msg_err}"
            print_info "Check that the bot has access to channel ${default_channel}."
        fi
    fi
}

# =============================================================================
# Phase 5: Health Check Summary
# =============================================================================
phase_5_health_check() {
    print_step "Health Check Summary"
    HC_PASS=0; HC_FAIL=0; HC_SKIP=0

    echo ""
    echo "  ${BOLD}================================================${RESET}"
    echo "  ${BOLD}Stock Manager Setup - Health Check Summary${RESET}"
    echo "  ${BOLD}================================================${RESET}"

    # 1. Python version
    local py_ok=false
    for cmd in python3 python; do
        if check_command "$cmd"; then
            local ver major minor
            ver="$($cmd --version 2>&1 | awk '{print $2}')"
            major="$(echo "$ver" | cut -d. -f1)"; minor="$(echo "$ver" | cut -d. -f2)"
            if [[ "$major" -ge 3 ]] && [[ "$minor" -ge 10 ]]; then
                echo "  ${GREEN}[PASS]${RESET} Python ${ver}"; HC_PASS=$((HC_PASS + 1)); py_ok=true; break
            fi
        fi
    done
    [[ "$py_ok" == "false" ]] && { echo "  ${RED}[FAIL]${RESET} Python >= 3.10 not found"; HC_FAIL=$((HC_FAIL + 1)); }

    # 2. Virtual environment
    if [[ -d "$VENV_DIR" ]] && [[ -f "$VENV_DIR/bin/python" ]]; then
        echo "  ${GREEN}[PASS]${RESET} Virtual environment (.venv)"; HC_PASS=$((HC_PASS + 1))
    else echo "  ${RED}[FAIL]${RESET} Virtual environment (.venv)"; HC_FAIL=$((HC_FAIL + 1)); fi

    # 3. Dependencies
    if "${VENV_DIR}/bin/python" -c "import stock_manager" &>/dev/null 2>&1; then
        echo "  ${GREEN}[PASS]${RESET} Dependencies installed"; HC_PASS=$((HC_PASS + 1))
    else echo "  ${RED}[FAIL]${RESET} Dependencies installed"; HC_FAIL=$((HC_FAIL + 1)); fi

    # 4. .env with required vars
    if [[ -f "$ENV_FILE" ]]; then
        local has_key; has_key="$(get_env_var "KIS_APP_KEY")"
        local has_secret; has_secret="$(get_env_var "KIS_APP_SECRET")"
        if [[ -n "$has_key" ]] && [[ -n "$has_secret" ]]; then
            echo "  ${GREEN}[PASS]${RESET} Environment file (.env)"; HC_PASS=$((HC_PASS + 1))
        else echo "  ${RED}[FAIL]${RESET} Environment file (.env) - missing required vars"; HC_FAIL=$((HC_FAIL + 1)); fi
    else echo "  ${RED}[FAIL]${RESET} Environment file (.env) - not found"; HC_FAIL=$((HC_FAIL + 1)); fi

    # 5. KIS API token
    local kis_key kis_secret kis_mock
    kis_key="$(get_env_var "KIS_APP_KEY")"; kis_secret="$(get_env_var "KIS_APP_SECRET")"
    kis_mock="$(get_env_var "KIS_USE_MOCK")"
    resolve_kis_urls "$kis_mock"
    if [[ -n "$kis_key" ]] && [[ -n "$kis_secret" ]]; then
        # Avoid hammering OAuth endpoint: KIS may rate-limit token issuance (e.g. 1/min).
        if [[ "$LAST_KIS_TOKEN_OK" == "true" ]]; then
            echo "  ${GREEN}[PASS]${RESET} KIS API Authentication (${_KIS_TRADING_MODE} trading)"; HC_PASS=$((HC_PASS + 1))
        else
            local hc_token; hc_token="$(try_kis_token "$kis_key" "$kis_secret" "$_KIS_BASE_URL" "$_KIS_OAUTH_PATH")"
            if [[ -n "$hc_token" ]]; then
                echo "  ${GREEN}[PASS]${RESET} KIS API Authentication (${_KIS_TRADING_MODE} trading)"; HC_PASS=$((HC_PASS + 1))
            else
                echo "  ${RED}[FAIL]${RESET} KIS API Authentication (${_KIS_TRADING_MODE} trading)"; HC_FAIL=$((HC_FAIL + 1))
            fi
        fi
    else
        echo "  ${RED}[FAIL]${RESET} KIS API Authentication - credentials missing"; HC_FAIL=$((HC_FAIL + 1))
    fi

    # 6. Slack (if configured)
    local slack_en; slack_en="$(get_env_var "SLACK_ENABLED")"
    if [[ "$slack_en" == "true" ]]; then
        local slack_tok; slack_tok="$(get_env_var "SLACK_BOT_TOKEN")"
        local slack_ok; slack_ok="$(try_slack_auth "$slack_tok")"
        if [[ "$slack_ok" == "true" ]]; then
            echo "  ${GREEN}[PASS]${RESET} Slack Integration"; HC_PASS=$((HC_PASS + 1))
        else echo "  ${RED}[FAIL]${RESET} Slack Integration"; HC_FAIL=$((HC_FAIL + 1)); fi
    else echo "  ${DIM}[SKIP]${RESET} Slack Integration (not configured)"; HC_SKIP=$((HC_SKIP + 1)); fi

    # 7. State directory
    if [[ -d "$STATE_DIR" ]] && touch "${STATE_DIR}/.hc_test" 2>/dev/null && rm -f "${STATE_DIR}/.hc_test"; then
        echo "  ${GREEN}[PASS]${RESET} State Directory (${STATE_DIR}/)"; HC_PASS=$((HC_PASS + 1))
    else echo "  ${RED}[FAIL]${RESET} State Directory (${STATE_DIR}/)"; HC_FAIL=$((HC_FAIL + 1)); fi

    # Summary
    local total_checked=$((HC_PASS + HC_FAIL))
    echo "  ${BOLD}================================================${RESET}"
    echo "  Result: ${GREEN}${HC_PASS}/${total_checked} passed${RESET}, ${RED}${HC_FAIL} failed${RESET}, ${DIM}${HC_SKIP} skipped${RESET}"
    echo "  ${BOLD}================================================${RESET}"

    echo ""
    if [[ $HC_FAIL -eq 0 ]]; then print_success "Setup complete! To start trading:"
    else print_warning "Setup completed with ${HC_FAIL} failure(s). Fix issues and re-run."; fi

    echo ""; print_info "Run the application:"
    print_info "  source .venv/bin/activate"
    print_info "  stock-manager"
    echo ""; print_info "Or run tests:"
    print_info "  pytest"
    echo ""
    local mock_val; mock_val="$(get_env_var "KIS_USE_MOCK")"
    if [[ "$mock_val" == "true" ]]; then print_info "Paper trading mode: ${GREEN}enabled${RESET}"
    else print_info "Real trading mode: ${YELLOW}enabled${RESET}"; fi
    print_info "State directory: ${STATE_DIR}/"

    [[ $HC_FAIL -gt 0 ]] && return 1
    return 0
}

# =============================================================================
# Main
# =============================================================================
main() {
    setup_colors
    print_header
    phase_1_prerequisites
    phase_2_env_config
    phase_3_kis_api_test
    phase_4_slack
    phase_5_health_check
}

main "$@"
