# P05 분석 재생성

현재 P05의 유효 입력은 ISO-TP `isotp-120-entry-v1`과 terminal-frame probe 보정 Custom `custom-120-terminal-probe-v1`이다. 초기 runner/dependency/CAN 무응답 artifact와 보정 전 `custom-120-entry-v1`/`custom-120-entry-v2`는 보존하지만 기본 명령의 입력이 아니다.

```powershell
python experiments/ksma-2026/analysis/p05_analyze.py `
  --input-root docs/paper-plan/reports/artifacts/P04-20261009/bbb-p04-f407-500k-20261009 `
  --output experiments/ksma-2026/analysis/p05-terminal-probe-v1-20261009
```

`--isotp-run`과 `--custom-run`으로 보존한 다른 run 조합도 명시할 수 있다. 스크립트는 CSV·JSONL·manifest의 schema, 120개 trial ID, planned trial의 protocol/loss/seed, firmware hash, manifest 종료 상태와 raw status 대응을 검사한다. 결과는 `p05-validation.json`, `p05-summary-by-protocol-loss.csv`, SVG 세 그림이다. 원시 evidence를 수정하지 않는다.

성공 조건부 시간은 `OK` 행만 사용한 sample mean, sample standard deviation, two-sided 95% Student-t CI이다. 성공률과 재전송 overhead는 모든 시도에 대해 계산한다. overhead 분모는 각 group의 `sum(send_attempts)`이며 실패의 timeout elapsed를 성공 시간에 대입하지 않는다.
