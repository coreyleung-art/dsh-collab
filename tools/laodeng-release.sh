#!/bin/bash
# laodeng-release.sh — 外卖老登 iOS TestFlight 发布流水线（2026-10-06 星桥）
# 背景：FAFB 开发证书无头直签会挂（钥匙串授权缺失）+ HTTPS 时间戳服务劣化时 codesign --timestamp 会挂
# 方案：全手工签名路径 —— archive 用 Apple Distribution 证书 + API 创建的 App Store 描述文件；export manual
# 前置：描述文件已由 ASC API 创建并安装（uuid a55e332d-1ae2-4224-980e-df011a46bc9e）
# 用法：bash laodeng-release.sh
set -euo pipefail
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
cd ~/meituan-multi/laodeng-h5/ios-shell

TEAM=XS7SMKFS42
API_KEY=VA9RR5747M
ISSUER=$(cat ~/.dsh/appstoreconnect/issuer-id.txt)
PROFILE="iOS Team Store Provisioning Profile: com.laodeng.h5.shell"
BUILD=$(date +%Y%m%d%H%M)

echo "== 1/3 archive（manual · Apple Distribution · 指定 profile）"
xcodebuild -project LaodengApp.xcodeproj -scheme LaodengApp \
  -configuration Release -destination 'generic/platform=iOS' \
  DEVELOPMENT_TEAM=$TEAM \
  CODE_SIGN_STYLE=Manual CODE_SIGN_IDENTITY="Apple Distribution" \
  PROVISIONING_PROFILE_SPECIFIER="$PROFILE" \
  -derivedDataPath /tmp/LaodengDD \
  -archivePath "/tmp/LaodengApp-$BUILD.xcarchive" archive | tail -2

echo "== 2/3 export（manual · 同 profile）"
cat > /tmp/ExportOptions-laodeng.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>method</key><string>app-store-connect</string>
  <key>teamID</key><string>$TEAM</string>
  <key>signingStyle</key><string>manual</string>
  <key>provisioningProfiles</key><dict>
    <key>com.laodeng.h5.shell</key><string>$PROFILE</string>
  </dict>
</dict></plist>
EOF
rm -rf /tmp/LaodengApp-export && mkdir -p /tmp/LaodengApp-export
xcodebuild -exportArchive -archivePath "/tmp/LaodengApp-$BUILD.xcarchive" \
  -exportOptionsPlist /tmp/ExportOptions-laodeng.plist -exportPath /tmp/LaodengApp-export | tail -2

echo "== 3/3 上传 ASC"
mkdir -p ~/.appstoreconnect/private_keys
cp ~/.dsh/appstoreconnect/AuthKey_$API_KEY.p8 ~/.appstoreconnect/private_keys/
IPA=$(ls -t /tmp/LaodengApp-export/*.ipa | head -1)
echo "ipa=$IPA"
xcrun altool --upload-app -f "$IPA" -t ios --apiKey $API_KEY --apiIssuer "$ISSUER" 2>&1 | tail -4
echo "PIPELINE-DONE build=$BUILD"
