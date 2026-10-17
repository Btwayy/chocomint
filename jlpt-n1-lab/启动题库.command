#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if curl --silent --fail http://127.0.0.1:8765/api/state >/dev/null; then
  echo '题库已经运行： http://127.0.0.1:8765/'
  echo '在浏览器打开上面的地址即可。'
  read -r '?按回车关闭此窗口。'
else
  echo '请在浏览器打开： http://127.0.0.1:8765/'
  echo '关闭此窗口或按 Ctrl+C 可停止服务，数据会保留。'
  python3 server.py
fi
