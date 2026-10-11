#!/bin/bash
# starbridge-release.sh — 星台 App TestFlight 发布流水线（2026-10-05 星桥）
# 步骤：archive（App Store 分发签名）→ export ipa → altool 上传 ASC
# 凭证：ASC API key ~/.dsh/appstoreconnect/AuthKey_VA9RR5747M.p8 + issuer-id.txt
# 用法：starbridge-release.sh [版本号覆盖]
set -euo pipefail
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
cd ~/sb-mobile/ios/StarBridge

TEAM=XS7SMKFS42
API_KEY=VA9RR5747M
ISSUER=$(cat ~/.dsh/appstoreconnect/issuer-id.txt)
VER="${1:-$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' /dev/stdin 2>/dev/null || echo 0.9.13)}"
BUILD=$(date +%Y%m%d%H%M)

echo "== 1/3 archive（Release + App Store 分发）"
xcodebuild -project StarBridge.xcodeproj -scheme StarBridge \
  -configuration Release -destination 'generic/platform=iOS' \
  DEVELOPMENT_TEAM=$TEAM -allowProvisioningUpdates \
  -archivePath "/tmp/StarBridge-$BUILD.xcarchive" archive \
  | tail -3

echo "== 2/3 export ipa"
cat > /tmp/ExportOptions.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>teamID</key><string>$TEAM</string>
</dict></plist>
EOF
xcodebuild -exportArchive -archivePath "/tmp/StarBridge-$BUILD.xcarchive" \
  -allowProvisioningUpdates \
  -exportOptionsPlist /tmp/ExportOptions.plist -exportPath /tmp/StarBridge-export | tail -2

echo "== 3/3 上传 ASC（altool + API key）"
# altool 只从固定目录解析 key（~/private_keys 等），从单一来源同步过去
mkdir -p ~/.appstoreconnect/private_keys
if [ ! -f ~/.appstoreconnect/private_keys/AuthKey_$API_KEY.p8 ]; then
  cp ~/.dsh/appstoreconnect/AuthKey_$API_KEY.p8 ~/.appstoreconnect/private_keys/
fi
chmod 600 ~/.appstoreconnect/private_keys/AuthKey_$API_KEY.p8
IPA=$(ls -t /tmp/StarBridge-export/*.ipa | head -1)
echo "ipa=$IPA"
xcrun altool --upload-app -f "$IPA" -t ios \
  --apiKey $API_KEY --apiIssuer "$ISSUER" 2>&1 | tail -5
echo "PIPELINE-DONE build=$BUILD"
