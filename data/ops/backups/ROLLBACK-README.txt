回滚插件依赖重指：
python3 -c "import json,os;[ (os.remove(m['link']), os.symlink(m['old_target'],m['link'])) for m in json.load(open('/Users/coreyleung/dsh-collab/data/ops/backups/plugin-dep-repoint-mac-mini-20261006-235419.json')) ]"
清单=/Users/coreyleung/dsh-collab/data/ops/backups/plugin-dep-repoint-mac-mini-20261006-235419.json
