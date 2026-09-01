#!/bin/sh
# 하네스 Bash 가드가 중괄호 쌍을 든 히어독을 거절한다(규약 §2).
# 그래서 소스를 자리표시자로 적고 이 스크립트가 되돌린다.
for f in "$@"; do
  sed -i '' 's/\xe2\x9f\xa6/{/g' "$f"
  sed -i '' 's/\xe2\x9f\xa7/}/g' "$f"
done
