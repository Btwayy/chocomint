#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if ! curl --silent --fail http://127.0.0.1:11434/api/tags >/dev/null; then
  echo '请先在终端运行： OLLAMA_NO_CLOUD=1 ollama serve'
  read -r '?按回车关闭。'
  exit 1
fi
python3 lab.py generate && python3 lab.py blind-check --model qwen3.5:9b-q4_K_M && python3 lab.py export
read -r '?按回车关闭。'
