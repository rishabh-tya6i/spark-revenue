import client from './client';

export interface OrchestrationRun {
  id: number;
  run_type: string;
  mode: string;
  interval: string;
  status: string;
  reason?: string;
  selected_symbols_count: number;
  ready_symbols_count: number;
  success_count: number;
  skipped_count: number;
  failed_count: number;
  summary: any;
  created_ts: string;
}

export interface UniverseState {
  mode: string;
  symbols: string[];
}

export interface TrainabilityState {
  mode: string;
  interval: string;
  symbols: string[];
  trainable_symbols: string[];
  details: any[];
}

export interface ReadinessDetail {
  symbol: string;
  decision_label: string;
  decision_score: number;
  rl_action: string;
  ready: boolean;
  reason: string;
  decision_ts?: string;
  override_created_ts?: string;
  decision_stale?: boolean;
  override_stale?: boolean;
  override_active: boolean;
  override_action?: string;
}

export interface ReadinessState {
  mode: string;
  interval: string;
  symbols: string[];
  inference_ready_symbols?: string[];
  execution_ready_symbols?: string[];
  details: ReadinessDetail[];
}

export interface GuardrailResult {
  execution_enabled: boolean;
  allowed_actions: string[];
  max_symbols_per_run: number;
  requested_ready_symbols: string[];
  allowed_symbols: string[];
  blocked_symbols: { symbol: string; reason: string }[];
}

export interface GuardrailSummary {
  mode: string;
  interval: string;
  execution_ready_symbols: string[];
  guardrails: GuardrailResult;
  guardrail_summary: any;
}

export interface ExecutionOverride {
  id: number;
  symbol: string;
  interval: string;
  override_action: string;
  reason?: string;
  created_ts: string;
}

export interface DispatchRecord {
  id: number;
  symbol: string;
  interval: string;
  source_type: string;
  source_id: number;
  dispatched_action: string;
  status: string;
  order_id?: string;
  created_ts: string;
}

export interface StalenessSummary {
  symbols_checked: number;
  stale_decision_symbols: string[];
  stale_override_symbols: string[];
  fresh_candidates: string[];
}

export interface StalenessState {
  mode: string;
  interval: string;
  symbols: string[];
  details: ReadinessDetail[];
  summary: StalenessSummary;
}

export interface OperationalStateSnapshot {
  mode: string;
  interval: string;
  symbols: string[];
  inference_ready_symbols: string[];
  execution_ready_symbols: string[];
  models: {
    symbols_checked: number;
    price_model_available: string[];
    rl_agent_available: string[];
    missing_price_model: string[];
    missing_rl_agent: string[];
  };
  decisions: {
    symbols_checked: number;
    has_decision: string[];
    actionable: string[];
    hold: string[];
    missing: string[];
  };
  execution_state: {
    symbols_checked: number;
    has_orders: string[];
    open_positions: string[];
    no_activity: string[];
  };
  execution_guardrails: {
    execution_enabled: boolean;
    allowed_actions: string[];
    max_symbols_per_run: number;
  };
  execution_overrides: {
    active_symbols: string[];
    actions: Record<string, string>;
  };
  execution_dispatch: {
    symbols_checked: number;
    already_dispatched: string[];
    not_dispatched: string[];
  };
  execution_staleness: {
    symbols_checked: number;
    stale_decision_symbols: string[];
    stale_override_symbols: string[];
    fresh_candidates: string[];
  };
  latest_runs: {
    train: OrchestrationRun | null;
    inference: OrchestrationRun | null;
    execution: OrchestrationRun | null;
    cycle: OrchestrationRun | null;
  };
}

export const getOperationalState = async (mode?: string, interval?: string): Promise<OperationalStateSnapshot> => {
  const response = await client.get('/orchestration/state', { params: { mode, interval } });
  return response.data;
};

export const getUniverse = async (mode?: string): Promise<UniverseState> => {
  const response = await client.get('/orchestration/universe', { params: { mode } });
  return response.data;
};

export const getTrainability = async (mode?: string, interval?: string): Promise<TrainabilityState> => {
  const response = await client.get('/orchestration/trainability', { params: { mode, interval } });
  return response.data;
};

export const getInferenceReadiness = async (mode?: string, interval?: string): Promise<ReadinessState> => {
  const response = await client.get('/orchestration/inference-readiness', { params: { mode, interval } });
  return response.data;
};

export const getExecutionReadiness = async (mode?: string, interval?: string, requireActionable: boolean = true): Promise<ReadinessState> => {
  const response = await client.get('/orchestration/execution-readiness', { params: { mode, interval, require_actionable: requireActionable } });
  return response.data;
};

export const getExecutionGuardrails = async (mode?: string, interval?: string, requireActionable: boolean = true): Promise<GuardrailSummary> => {
  const response = await client.get('/orchestration/execution-guardrails', { params: { mode, interval, require_actionable: requireActionable } });
  return response.data;
};

export const getExecutionOverrides = async (interval?: string, limit: number = 100): Promise<ExecutionOverride[]> => {
  const response = await client.get('/orchestration/execution-overrides', { params: { interval, limit } });
  return response.data;
};

export interface SetOverridePayload {
  symbol: string;
  interval: string;
  override_action: string;
  reason?: string;
}

export const setExecutionOverride = async (payload: SetOverridePayload): Promise<ExecutionOverride> => {
  const response = await client.post('/orchestration/execution-overrides', payload);
  return response.data;
};

export const clearExecutionOverride = async (symbol: string, interval: string): Promise<any> => {
  const response = await client.delete('/orchestration/execution-overrides', { params: { symbol, interval } });
  return response.data;
};

export const getExecutionDispatches = async (symbol?: string, interval?: string, limit: number = 100): Promise<DispatchRecord[]> => {
  const response = await client.get('/orchestration/execution-dispatches', { params: { symbol, interval, limit } });
  return response.data;
};

export const getExecutionStaleness = async (mode?: string, interval?: string): Promise<StalenessState> => {
  const response = await client.get('/orchestration/execution-staleness', { params: { mode, interval } });
  return response.data;
};

export interface TrainParams {
  mode?: string;
  interval?: string;
  lookback_days?: number;
  sync_first?: boolean;
  epochs?: number;
  episodes?: number;
}

export const runTrainTrainable = async (params: TrainParams): Promise<any> => {
  const response = await client.post('/orchestration/train-trainable', null, { params });
  return response.data;
};

export interface InferenceParams {
  mode?: string;
  interval?: string;
}

export const runUniverseInference = async (params: InferenceParams): Promise<any> => {
  const response = await client.post('/orchestration/run-inference', null, { params });
  return response.data;
};

export interface ExecutionParams {
  mode?: string;
  interval?: string;
  require_actionable?: boolean;
}

export const runUniverseExecution = async (params: ExecutionParams): Promise<any> => {
  const response = await client.post('/orchestration/run-execution', null, { params });
  return response.data;
};

export const runOperationalCycle = async (params: ExecutionParams): Promise<any> => {
  const response = await client.post('/orchestration/run-cycle', null, { params });
  return response.data;
};

export const getOrchestrationRuns = async (runType?: string, limit: number = 50): Promise<OrchestrationRun[]> => {
  const response = await client.get('/orchestration/runs', { params: { run_type: runType, limit } });
  return response.data;
};

export const getOrchestrationRun = async (runId: number): Promise<OrchestrationRun> => {
  const response = await client.get(`/orchestration/runs/${runId}`);
  return response.data;
};
