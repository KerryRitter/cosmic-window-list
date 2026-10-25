#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$HOME/.cargo/bin:$PATH"
if [[ -d "$project_dir/deps/usr/lib/x86_64-linux-gnu/pkgconfig" ]]; then
    export PKG_CONFIG_PATH="$project_dir/deps/usr/lib/x86_64-linux-gnu/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
fi
command -v cargo >/dev/null || { echo 'Missing Rust/Cargo. Install a current Rust toolchain first.' >&2; exit 1; }
checkout="$project_dir/upstream"
upstream_revision="63292ab74dc8ef9c8d4e04055047c7671554e937"
if [[ ! -d "$checkout/.git" ]]; then
    git clone https://github.com/pop-os/cosmic-applets.git "$checkout"
    git -C "$checkout" checkout "$upstream_revision"
fi
# Refuse to build a checkout at a different revision.
[[ "$(git -C "$checkout" rev-parse HEAD)" == "$upstream_revision" ]] || {
    echo 'Unexpected upstream revision; refusing to continue.' >&2; exit 1;
}
python3 "$project_dir/prepare.py" "$checkout"
cargo build --locked --release --manifest-path "$checkout/Cargo.toml" \
    -p cosmic-app-list --bin cosmic-window-list
echo "Built: $checkout/target/release/cosmic-window-list"
