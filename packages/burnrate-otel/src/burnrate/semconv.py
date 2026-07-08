# OTel GenAI semantic convention attribute names (Development status, mid-2026)
# Upstream: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

# ── Existing upstream attributes ────────────────────────────────────────────
GEN_AI_SYSTEM = "gen_ai.system"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"

# Token usage (upstream, no cost equivalent exists in spec)
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GEN_AI_USAGE_CACHE_CREATION_INPUT_TOKENS = "gen_ai.usage.cache_creation_input_tokens"
GEN_AI_USAGE_CACHE_READ_INPUT_TOKENS = "gen_ai.usage.cache_read_input_tokens"
GEN_AI_USAGE_REASONING_TOKENS = "gen_ai.usage.reasoning_tokens"

# Agent / tool call attributes (upstream)
GEN_AI_AGENT_ID = "gen_ai.agent.id"
GEN_AI_AGENT_NAME = "gen_ai.agent.name"
GEN_AI_TOOL_NAME = "gen_ai.tool.name"

# ── Proposed: gen_ai.usage.cost.* ────────────────────────────────────────────
# These attributes are proposed by Burnrate to fill the gap in the OTel GenAI
# spec. See docs/semconv-proposal.md for the full rationale and draft PR text.
# Format: float, USD (unless gen_ai.usage.cost.currency says otherwise)

GEN_AI_USAGE_COST_TOTAL = "gen_ai.usage.cost.total"
GEN_AI_USAGE_COST_INPUT = "gen_ai.usage.cost.input"
GEN_AI_USAGE_COST_OUTPUT = "gen_ai.usage.cost.output"
GEN_AI_USAGE_COST_CACHE_CREATION = "gen_ai.usage.cost.cache_creation"
GEN_AI_USAGE_COST_CACHE_READ = "gen_ai.usage.cost.cache_read"
GEN_AI_USAGE_COST_REASONING = "gen_ai.usage.cost.reasoning"
GEN_AI_USAGE_COST_CURRENCY = "gen_ai.usage.cost.currency"
GEN_AI_USAGE_COST_PRICING_MODEL = "gen_ai.usage.cost.pricing_model"

# ── Burnrate attribution dimensions ──────────────────────────────────────────
# Add these to your spans so Cost Guard can attribute spend to specific actors.
BURNRATE_AGENT_ID = "burnrate.agent.id"
BURNRATE_TASK_ID = "burnrate.task.id"
BURNRATE_USER_ID = "burnrate.user.id"
BURNRATE_FEATURE = "burnrate.feature"

# Metric names
METRIC_COST_TOTAL = "burnrate.cost.usd"
METRIC_COST_PER_OP = "burnrate.cost.per_operation.usd"
METRIC_TOKENS_INPUT = "burnrate.tokens.input"
METRIC_TOKENS_OUTPUT = "burnrate.tokens.output"
