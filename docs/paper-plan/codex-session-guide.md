# 새 Codex 대화로 한 단계씩 진행하기

## 작업 폴더 하나, 한 번에 대화 하나

사용할 폴더는 **`C:/repos/CanBootloader-paper`**다. branch는 `paper/ksma-2026`이며 이미 생성됐다.

1. Codex/IDE에서 이 폴더를 프로젝트로 연다.
2. 새 대화/스레드를 만들되 작업 대상은 이 로컬 폴더를 유지한다. 매 Task마다 새로운 worktree를 만들지 않는다.
3. 아래 시작 prompt를 붙인다.
4. Task 종료 시 report와 handoff가 파일로 저장됐는지 확인한다.
5. 실행 중인 작업이 종료됐고 다음 대화에서 필요한 정보가 저장되면 이전 대화/창을 닫는다. 다음 Task는 같은 폴더의 새 대화에서 진행한다.

“새 창”은 새 OS 창을 계속 띄울 필요 없이 같은 앱의 새 대화로 운영해도 된다. 한 폴더를 여러 대화가 동시에 수정하지 않게 한다. 종료된 대화를 열어 둘 필요는 없지만, 폴더/worktree를 삭제해서는 안 된다.

공식 문서는 Local과 새 Worktree 생성을 구분하고 같은 branch의 동시 checkout을 제한한다고 설명한다: [OpenAI Worktrees 문서](https://learn.chatgpt.com/docs/environments/git-worktrees). 이 계획에서는 이미 만든 영구적인 Git 작업 폴더를 계속 쓰므로 Task마다 branch를 switch하거나 새 Worktree 모드를 선택할 이유가 없다. 앱 버전에 따라 메뉴 이름은 달라질 수 있으며 실제 작업 경로/branch를 기준으로 확인한다.

## 첫 대화 시작 prompt

```text
작업 폴더는 C:\repos\CanBootloader-paper이고 branch는 paper/ksma-2026이다.
AGENTS.md와 docs/paper-plan/README.md, SESSION_HANDOFF.md,
tasks.md의 P00, codex-session-guide.md를 읽어라.

이번 대화에서는 P00만 수행해줘.
capston-1 기반 direct-write 논문 실험이며 기존 main의 staging/TW-03과 구분해줘.
먼저 git status, HEAD, submodule 상태를 확인하고 기존 변경을 보존해줘.
기록된 submodule revision과 build/address/size를 확인하고,
학회용 요약문·전문은 결과를 꾸미지 말고 골격부터 작성해줘.
이번 단계에 필요한 작업은 진행하되 P01을 자동 시작하지 마.
종료 전에 reports/P00.md, README의 Task 상태, SESSION_HANDOFF.md를 갱신하고
다음 대화에 붙일 prompt와 내가 준비할 것을 알려줘.
commit/push, 외부 제출·연락은 하지 마.
```

## 두 번째 이후 공통 prompt

```text
작업 폴더는 C:\repos\CanBootloader-paper이고 branch는 paper/ksma-2026이다.
AGENTS.md, docs/paper-plan/README.md, SESSION_HANDOFF.md,
codex-session-guide.md를 읽고 handoff에 지정된 Task의 tasks.md 절을 확인해줘.
git status와 HEAD를 확인하고, handoff의 현재/다음 Task 중 실행하도록 지정된
하나만 진행해줘. 미완료 Task가 있으면 그것부터 이어가고 임의로 다음 단계로 넘기지 마.
이번 범위에 필요한 작업은 끝까지 수행하되 다음 Task를 자동 시작하지 마.
기존 CSV와 미커밋 변경을 보존하고 실행하지 않은 시험은 NOT RUN으로 기록해줘.
종료 전에 해당 report, README 상태, SESSION_HANDOFF.md를 갱신하고
다음 대화용 prompt를 남겨줘. commit/push나 외부 제출·연락은 하지 마.
```

## 특정 Task를 직접 지정할 때

공통 prompt의 “handoff에 지정된 Task”를 아래의 해당 문장으로 바꾼다. 선행 조건이 충족되지 않았으면 Codex가 이를 설명하고 미완료 작업을 이어가도록 한다.

| Task | 붙일 문장 | 내가 준비할 것 |
| --- | --- | --- |
| P00 | 이번에는 P00 baseline/build/원고 골격만 수행해줘. | 공식 양식, 저자 정보, BBB/board 접속 정보(가능한 범위) |
| P01 | 이번에는 P01 시간·frame 집계 수정만 수행해줘. | P00 결과 |
| P02 | 이번에는 P02 loss/retry/실패 기록과 runner만 수행해줘. | P01 결과 |
| P03 | 이번에는 P03 hardware smoke와 측정 대조만 수행해줘. | 선택한 STM32, BBB, CAN 배선/종단, ST-LINK, 허용할 flashing 대상 |
| P04 | 이번에는 P04 고정된 240회 matrix만 수행해줘. | 같은 장비/설정, bootloader 교체 및 장시간 시험 가능 시간 |
| P05 | 이번에는 P05 분석과 1페이지 요약문만 작성해줘. | raw 자료, 공식 양식, 저자·소속 |
| P06 | 이번에는 P06 전문 2~3페이지 초안만 작성해줘. | 교수님 피드백, 확인한 참고문헌 |
| P07 | 이번에는 P07의 확정된 보충 실험만 수행해줘. | 두 번째 보드 등 선택 조건의 장비 |
| P08 | 이번에는 P08 최종 검토와 제출 인수인계만 수행해줘. | 채택 여부/심사 의견, 최종 저자 정보 |

장비가 준비되지 않은 상태에서 P03/P04를 요청했다면 실제 미실행을 완료로 바꾸지 않는다. 사용자가 독립 집필 작업으로 전환하길 원하면 그 범위를 명시하고 본 실험 결과는 미확정으로 남긴다.

## 대화가 길어지거나 중간에 닫고 싶을 때

```text
이번 대화는 여기서 마무리하고 다음 새 대화에서 이어갈게.
새로운 작업은 시작하지 말고, 현재 파일과 실행 상태를 안전하게 정리해줘.
완료/미완료/실행한 검증/실행 중인 명령을 report에 기록해줘.
SESSION_HANDOFF.md에 같은 Task의 정확한 다음 작업과 필요한 명령을 남겨줘.
코드와 결과를 임의로 지우거나 commit/push하지 말고 다음 대화용 prompt를 줘.
```

실험이 실행 중이면 무조건 창을 닫지 않는다. 현재 trial을 마무리하거나 안전하게 중단하여 결과를 저장한 뒤, 프로세스 생존 여부와 재개 지점을 handoff에 남긴다. 새 대화에서 같은 시험을 중복 실행하지 않는다.

## 단계 종료 확인

- 실제 Task 산출물이 파일로 저장되어 있는가?
- report에 명령/결과와 raw evidence 경로가 있는가?
- README 상태와 handoff의 다음 지시가 일치하는가?
- 미완료 hardware 검증을 PASS/DONE으로 바꾸지 않았는가?
- 실행 중인 프로세스가 있으면 이름·접속·재개/중단 방법이 기록되어 있는가?
- commit하지 않은 파일은 같은 worktree에 남아 있다는 사실을 이해했는가?

commit/push는 자동으로 하지 않는다. 별도 요청 시에만 변경을 검토한 뒤 처리한다. 기존 main으로 돌아갈 때도 논문 branch를 main 폴더에서 switch하지 말고 `C:/repos/CanBootloader` 프로젝트를 연다.
