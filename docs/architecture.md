# Stock Manager 아키텍처

> 관련 문서: [README.md](../README.md) | [knowledge-map.md](knowledge-map.md) | [execution-diagrams.md](execution-diagrams.md) | [runtime-trading-guardrails.md](runtime-trading-guardrails.md)

이 문서는 현재 코드 기준의 상위 아키텍처를 한 번에 파악하기 위한 별도 설명서입니다.

전제:
- 메인 런타임 경로는 `TradingEngine` 중심입니다.
- `stock-manager trade`는 엔진을 거치지 않고 `OrderExecutor -> KISRestClient`로 직접 주문할 수 있습니다.
- `TradingPipelineRunner`는 별도 상태머신 모듈로 존재하지만, 현재 메인 CLI/Slack 런타임의 기본 진입 경로는 아닙니다.

## 목차
1. [전체 아키텍처](#1-전체-아키텍처)
2. [사람이 Slack을 통해 요청하는 아키텍처](#2-사람이-slack을-통해-요청하는-아키텍처)
3. [stock-manager 내부 아키텍처](#3-stock-manager-내부-아키텍처)
4. [실제 주식을 거래하는 아키텍처](#4-실제-주식을-거래하는-아키텍처)
5. [매수 매도 흐름](#5-매수-매도-흐름)
6. [AI persona 흐름](#6-ai-persona-흐름)
7. [코드 진입점 메모](#7-코드-진입점-메모)

---

## 1. 전체 아키텍처

```mermaid
flowchart LR
    User["사용자 / 운영자"] --> CLI["CLI<br/>main.py"]
    User --> Slack["Slack"]
    Slack --> SlackBot["Slack Bot<br/>Socket Mode + /sm"]

    CLI --> CliTrade["trade / run / smoke / verify"]
    SlackBot --> Session["SessionManager"]

    CliTrade --> Engine["TradingEngine"]
    CliTrade --> DirectTrade["Direct Trade Path<br/>OrderExecutor"]
    Session --> Engine

    Engine --> Strategy["Strategy Layer"]
    Engine --> Trade["Order / Risk / Position"]
    Engine --> Monitor["Monitoring / Reconciliation"]
    Engine --> Persist["Persistence / Recovery"]
    Engine --> Notify["SlackNotifier"]

    Strategy --> KIS["KIS OpenAPI<br/>REST + WebSocket"]
    Trade --> KIS
    Monitor --> KIS
    DirectTrade --> KIS

    Persist --> Local["로컬 상태 파일 / 토큰 캐시"]
    Notify --> Slack
```

---

## 2. 사람이 Slack을 통해 요청하는 아키텍처

```mermaid
flowchart TD
    Human["사람"] --> Slash["Slack Slash Command<br/>/sm ..."]
    Slash --> Socket["SocketModeHandler"]
    Socket --> Bolt["Slack Bolt App<br/>slack_bot/app.py"]

    Bolt --> Ack["즉시 ack()"]
    Bolt --> Guard["권한 체크<br/>사용자 rate limit"]
    Guard --> Parser["command_parser.parse_command()"]
    Parser --> Branch{"subcommand"}

    Branch -->|start| Start["SessionManager.start_session()"]
    Branch -->|stop| Stop["SessionManager.stop_session()"]
    Branch -->|status/config| Status["세션 상태/설정 조회"]
    Branch -->|balance/orders| Query["엔진 조회 API 호출"]
    Branch -->|sell-all| Liquidate["engine.liquidate_all()"]

    Start --> Gate["live promotion gate"]
    Start --> Runtime["_build_runtime_context()"]
    Runtime --> Resolve["resolve_strategy()"]
    Resolve --> Engine["TradingEngine.start()"]

    Engine --> Notifier["SlackNotifier"]
    Status --> Format["Slack formatter"]
    Query --> Format
    Liquidate --> Format
    Stop --> Format

    Notifier --> SlackOut["Slack 응답 / 운영 알림"]
    Format --> SlackOut
```

---

## 3. stock-manager 내부 아키텍처

```mermaid
flowchart TD
    subgraph Entry["Entry Layer"]
        Main["main.py"]
        Cli["cli/trading_commands.py"]
        SlackApp["slack_bot/app.py"]
        SessionMgr["slack_bot/session_manager.py"]
    end

    subgraph Config["Configuration"]
        KISConfig["KISConfig"]
        SlackConfig["SlackConfig"]
    end

    subgraph Runtime["Runtime Core"]
        Engine["TradingEngine"]
        Risk["RiskManager"]
        Executor["OrderExecutor"]
        Positions["PositionManager"]
        PriceMonitor["PriceMonitor"]
        Reconciler["PositionReconciler"]
        Recovery["startup_reconciliation()"]
        State["TradingState<br/>save/load"]
        Notifier["SlackNotifier"]
        Rate["RateLimiter"]
    end

    subgraph Strategy["Strategy / Analysis"]
        Resolver["resolve_strategy()"]
        Consensus["ConsensusStrategy"]
        Graham["GrahamScreener"]
        Fetcher["TechnicalDataFetcher"]
        Evaluator["ConsensusEvaluator"]
        Personas["10 Personas + WoodAdvisory"]
    end

    subgraph Broker["Broker Integration"]
        Rest["KISRestClient"]
        Adapter["KISBrokerAdapter"]
        WS["KISWebSocketClient"]
        Token["Token Cache"]
    end

    subgraph External["External Systems"]
        KIS["KIS REST / WebSocket"]
        Slack["Slack"]
    end

    Main --> Cli
    Main --> SlackApp
    SlackApp --> SessionMgr

    Cli --> KISConfig
    SessionMgr --> KISConfig
    SessionMgr --> SlackConfig

    Cli --> Resolver
    SessionMgr --> Resolver
    Resolver --> Consensus
    Resolver --> Graham

    Consensus --> Fetcher
    Consensus --> Evaluator
    Evaluator --> Personas

    Cli --> Engine
    SessionMgr --> Engine

    Engine --> Risk
    Engine --> Executor
    Engine --> Positions
    Engine --> PriceMonitor
    Engine --> Reconciler
    Engine --> Recovery
    Engine --> State
    Engine --> Notifier
    Engine --> Rate
    Engine --> Adapter
    Engine --> Consensus
    Engine --> Graham

    Fetcher --> Rest
    Executor --> Rest
    PriceMonitor --> Rest
    Reconciler --> Rest
    Recovery --> Rest

    Adapter --> Rest
    Adapter --> WS
    Rest <--> Token
    Rest --> KIS
    WS --> KIS

    Notifier --> Slack
    Pipeline["TradingPipelineRunner<br/>별도 상태머신 모듈"] -. 메인 런타임과 분리 .-> Engine
```

---

## 4. 실제 주식을 거래하는 아키텍처

이 섹션은 `KIS_USE_MOCK=false` 기준의 live trading 경로를 보여줍니다.

```mermaid
flowchart LR
    User["운영자"] --> Surface{"진입점"}

    Surface -->|CLI trade --execute --confirm-live| Direct["Direct Trade Path"]
    Surface -->|CLI run / Slack /sm start| EnginePath["Engine Path"]

    Direct --> LiveGate["promotion gate + live confirm"]
    EnginePath --> LiveGate

    LiveGate --> LiveConfig["KISConfig<br/>use_mock=false"]
    LiveConfig --> Rest["KISRestClient"]

    EnginePath --> Engine["TradingEngine"]
    Engine --> Risk["RiskManager"]
    Engine --> OrderExec["OrderExecutor"]
    Engine --> Recon["PositionReconciler"]
    Engine --> Adapter["KISBrokerAdapter"]

    Direct --> OrderExec

    OrderExec --> Rest
    Recon --> Rest
    Adapter --> Rest

    Rest --> OAuth["KIS OAuth<br/>/oauth2/tokenP"]
    Rest --> RestAPI["KIS REST<br/>주문 / 잔고 / 시세 / 일별주문"]

    Adapter --> Approval["WebSocket 승인키<br/>/oauth2/Approval"]
    Adapter --> WS["KISWebSocketClient"]
    WS --> LiveWS["KIS Live WebSocket"]

    LiveWS --> Engine
    RestAPI --> Engine
```

---

## 5. 매수 매도 흐름

```mermaid
flowchart TD
    Trigger["전략 신호 / 수동 요청 / Slack sell-all"] --> Buy["Engine.buy()"]

    Buy --> Precheck["사전 검사<br/>running / trading_enabled / pending / market hours / kill switch"]
    Precheck --> Risk["RiskManager.validate_order()"]

    Risk -->|reject| Reject["주문 거절 + 알림"]
    Risk -->|approve or adjust qty| SubmitBuy["OrderExecutor.buy()<br/>KIS 주문 제출"]

    SubmitBuy --> Pending["pending order 등록<br/>state 저장"]
    Pending --> FillSource{"체결 반영 경로"}

    FillSource -->|execution notice| ExecEvent["WebSocket execution event"]
    FillSource -->|reconciliation| Recon["PositionReconciler / daily orders / balance"]

    ExecEvent --> ApplyBuy["매수 체결 반영<br/>포지션 open/update"]
    Recon --> ApplyBuy

    ApplyBuy --> Monitor["실시간 quote 또는 polling 모니터링"]
    Monitor --> Exit{"매도 트리거"}

    Exit -->|manual| Sell["Engine.sell()"]
    Exit -->|stop-loss / take-profit| Sell
    Exit -->|liquidate-all| Sell

    Sell --> SellCheck["포지션 존재 / pending sell 차단"]
    SellCheck --> SubmitSell["OrderExecutor.sell()<br/>KIS 주문 제출"]
    SubmitSell --> SellPending["pending sell 등록"]

    SellPending --> SellFill{"체결 반영 경로"}
    SellFill -->|execution notice| ApplySell["매도 체결 반영<br/>포지션 reduce/close"]
    SellFill -->|reconciliation| ApplySell

    ApplySell --> Persist["state 저장 + 알림"]
    Reject --> End["종료"]
    Persist --> End
```

---

## 6. AI persona 흐름

현재 코드 기준으로 consensus 전략은 10명의 binding persona와 1명의 advisory persona를 사용합니다.
`--llm-mode selective`는 Slack 세션에서 Dalio persona만 hybrid LLM overlay로 교체합니다.

```mermaid
flowchart TD
    Start["strategy=consensus"] --> Factory["resolve_strategy()"]
    Factory --> Build["build_consensus_strategy()"]

    Build --> Fetcher["TechnicalDataFetcher"]
    Build --> Evaluator["ConsensusEvaluator"]
    Build --> Advisory["WoodAdvisory<br/>non-binding"]

    Fetcher --> Snapshot["MarketSnapshot<br/>현재가 / 재무 / OHLCV / 지표"]
    Snapshot --> Evaluator

    Evaluator --> Pool["ThreadPoolExecutor"]
    Pool --> Buffett["Buffett"]
    Pool --> Graham["Graham"]
    Pool --> Lynch["Lynch"]
    Pool --> Munger["Munger"]
    Pool --> Dalio["Dalio"]
    Pool --> Soros["Soros"]
    Pool --> Fisher["Fisher"]
    Pool --> Templeton["Templeton"]
    Pool --> Livermore["Livermore"]
    Pool --> Simons["Simons"]
    Pool --> Advisory

    Dalio -. selective llm_mode .-> Hybrid["DalioHybridPersona<br/>rule + optional LLM verify"]

    Buffett --> Votes["PersonaVote[]"]
    Graham --> Votes
    Lynch --> Votes
    Munger --> Votes
    Dalio --> Votes
    Hybrid --> Votes
    Soros --> Votes
    Fisher --> Votes
    Templeton --> Votes
    Livermore --> Votes
    Simons --> Votes

    Votes --> Agg["VoteAggregator<br/>BUY>=6<br/>quorum>=70%<br/>avg conviction>=0.60<br/>category diversity>=3"]
    Advisory --> Agg

    Agg --> Result["ConsensusResult"]
    Result --> Score["ConsensusScore.passes_all"]
    Score --> Engine["TradingEngine._run_strategy_cycle()"]
    Engine --> Buy["engine.buy()"]
```

---

## 7. 코드 진입점 메모

- 전체 CLI 진입점: `stock_manager/main.py`
- 런타임 명령 경로: `stock_manager/cli/trading_commands.py`
- Slack 명령 라우터: `stock_manager/slack_bot/app.py`
- Slack 세션 수명주기: `stock_manager/slack_bot/session_manager.py`
- 메인 런타임 오케스트레이터: `stock_manager/engine.py`
- KIS REST 클라이언트: `stock_manager/adapters/broker/kis/client.py`
- KIS REST/WS 퍼사드: `stock_manager/adapters/broker/kis/broker_adapter.py`
- 전략 팩토리: `stock_manager/trading/strategies/__init__.py`
- consensus 평가기: `stock_manager/trading/consensus/evaluator.py`
- vote 집계: `stock_manager/trading/consensus/aggregator.py`

