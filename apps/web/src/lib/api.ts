import { z } from "zod";

export const condition = z.object({
  field: z.string(),
  operator: z.enum(["eq", "neq", "gt", "gte", "lt", "lte", "in"]),
  value: z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.array(z.union([z.string(), z.number(), z.boolean()])),
  ]),
});
export const choiceSchema = z.object({
  id: z.string(),
  label: z.string(),
  destination: z.string(),
  conditions: z.array(condition),
  source_refs: z.array(z.string()),
  evidence_status: z.enum(["cited", "uncited"]),
});
export const nodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.enum(["start", "decision", "action", "end"]),
  source_refs: z.array(z.string()),
  choices: z.array(choiceSchema),
  next_node: z.string().nullable(),
});
export const documentSchema = z.object({
  id: z.string(),
  title: z.string(),
  content: z.string(),
  content_hash: z.string(),
  original_file_hash: z.string().nullable().optional(),
  page_count: z.number().int().nullable().optional(),
  empty_pages: z.array(z.number().int()).optional(),
  source_type: z.string(),
  created_at: z.string(),
  segments: z.array(
    z.object({
      id: z.string(),
      ordinal: z.number(),
      text: z.string(),
      start_offset: z.number(),
      end_offset: z.number(),
      page_number: z.number().int().nullable().optional(),
    }),
  ),
});
export const playbookSchema = z.object({
  id: z.string(),
  document_id: z.string(),
  title: z.string(),
  version: z.number(),
  status: z.enum(["draft", "approved"]),
  graph: z.object({ nodes: z.array(nodeSchema) }),
  parent_version_id: z.string().nullable(),
  graph_hash: z.string(),
});
export const catalogSchema = z.object({
  workspace: z
    .object({
      mode: z.literal("temporary"),
      expires_at: z.number().int(),
      notice: z.string(),
    })
    .nullable()
    .optional(),
  demos: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      description: z.string(),
      document_id: z.string(),
      playbook_id: z.string(),
      scenario_id: z.string(),
      fictional: z.boolean(),
      scenario_status: z.literal("ready"),
    }),
  ),
});
export type PolicyNode = z.infer<typeof nodeSchema>;
export type Playbook = z.infer<typeof playbookSchema>;
export type SourceDocument = z.infer<typeof documentSchema>;

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new Error(
      "Could not reach your workspace. Check your connection. If you were saving, check the Library before trying again.",
    );
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new Error(
      response.ok
        ? "The workspace returned an unreadable response. If you were saving, check the Library before trying again."
        : `The workspace could not complete this request (${response.status}). Please try again shortly.`,
    );
  }
  if (!response.ok) {
    const error = z
      .object({
        error: z.object({
          message: z.string(),
          details: z
            .array(
              z.object({
                location: z.array(z.union([z.string(), z.number()])),
                message: z.string(),
              }),
            )
            .optional(),
        }),
      })
      .safeParse(body);
    throw new Error(
      error.success
        ? [
            error.data.error.message,
            ...(error.data.error.details ?? [])
              .slice(0, 3)
              .map(
                (detail) =>
                  `${detail.location.filter((part) => part !== "body").join(" → ")}: ${detail.message}`,
              ),
          ].join(" · ")
        : `Request failed (${response.status})`,
    );
  }
  const result = schema.safeParse(body);
  if (!result.success)
    throw new Error(
      "The workspace returned unexpected data. Reload this page. If you were saving, check the Library before trying again.",
    );
  return result.data;
}
export const api = {
  importPdf: async (title: string, file: File) => {
    if (file.size > 256 * 1024)
      throw new Error("Use a PDF no larger than 256 KiB.");
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 8192)
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 8192));
    return request(
      "/documents/pdf",
      documentSchema,
      post({ title, pdf_base64: btoa(binary) }),
    );
  },
  resetDemo: () =>
    request("/demo/reset", catalogSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    }),
  catalog: () => request("/demo", catalogSchema),
  document: (id: string) =>
    request(`/documents/${encodeURIComponent(id)}`, documentSchema),
  playbook: (id: string) =>
    request(`/playbooks/${encodeURIComponent(id)}`, playbookSchema),
  import: (title: string, content: string, source_type: "text" | "markdown") =>
    request("/documents", documentSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, content, source_type }),
    }),
};

const factValue = z.union([z.string(), z.number(), z.boolean()]);
const factsSchema = z.record(z.string(), factValue);
const injectSchema = z.object({
  before_node_id: z.string(),
  facts: factsSchema,
});
export const scenarioSchema = z.object({
  id: z.string(),
  playbook_version_id: z.string(),
  title: z.string(),
  description: z.string(),
  initial_facts: factsSchema,
  injects: z.array(injectSchema),
  seed: z.number().int(),
  fictional: z.boolean(),
});
export const runStatusSchema = z.enum([
  "awaiting_decision",
  "completed",
  "deviation",
  "uncovered",
  "overlap",
  "budget_exceeded",
]);
const evaluationSchema = z.object({
  node_id: z.string(),
  result: z.enum(["exact_match", "uncovered", "overlap"]),
  matching_choice_ids: z.array(z.string()),
  node_source_refs: z.array(z.string()),
  facts_snapshot: factsSchema,
  choice_outcomes: z.array(
    z.object({
      choice_id: z.string(),
      matched: z.boolean(),
      source_refs: z.array(z.string()),
      evidence_status: z.enum(["cited", "uncited"]),
      condition_outcomes: z.array(
        z.object({
          field: z.string(),
          operator: condition.shape.operator,
          value: condition.shape.value,
          result: z.boolean(),
          missing_fact: z.boolean(),
          type_mismatch: z.boolean(),
        }),
      ),
    }),
  ),
});
const logicalEventSchema = z.object({
  id: z.string(),
  created_at: z.string(),
  sequence: z.number().int(),
  node_id: z.string(),
  event_type: z.enum([
    "node_entered",
    "inject_applied",
    "decision_evaluated",
    "decision_selected",
    "deviation_recorded",
    "run_terminated",
  ]),
  playbook_version_id: z.string(),
  playbook_authority: z.enum(["draft", "approved"]),
  execution_mode: z.enum(["interactive", "auto_rehearsal"]),
  context_hash: z.string(),
  state_hash: z.string(),
  payload: z.record(z.string(), z.unknown()),
  facts_snapshot: factsSchema,
});
export const sessionSchema = z.object({
  id: z.string(),
  scenario_id: z.string(),
  playbook_version_id: z.string(),
  document_id: z.string(),
  parent_session_id: z.string().nullable(),
  fork_event_index: z.number().int().nullable(),
  engine_version: z.string(),
  revision: z.number().int(),
  status: runStatusSchema,
  current_node_id: z.string(),
  created_at: z.string(),
  events: z.array(logicalEventSchema),
  proposal_id: z.string().nullable(),
  result: z.object({
    playbook_version_id: z.string(),
    playbook_authority: z.enum(["draft", "approved"]),
    status: runStatusSchema,
    scenario_title: z.string(),
    scenario_seed: z.number().int(),
    final_facts: factsSchema,
    deviations: z.array(
      z.object({ node_id: z.string(), selected_choice_id: z.string() }),
    ),
    checkpoint: evaluationSchema.nullable(),
    rehearsal_notice: z.string(),
    decisions_made: z.array(
      z.object({
        node_id: z.string(),
        selected_choice_id: z.string().nullable(),
        selection_origin: z.enum(["user", "automatic_rehearsal"]),
      }),
    ),
    input_snapshot: z.object({
      graph: z.object({ nodes: z.array(nodeSchema) }),
      scenario: z.object({
        title: z.string(),
        seed: z.number().int(),
        initial_facts: factsSchema,
        injects: z.array(injectSchema),
      }),
      execution_mode: z.enum(["interactive", "auto_rehearsal"]),
    }),
  }),
});
export const replaySchema = z.object({
  session_id: z.string(),
  verified: z.literal(true),
  event_count: z.number().int(),
  last_state_hash: z.string(),
  engine_version: z.string(),
});
export const proposalSchema = z.object({
  id: z.string(),
  session_id: z.string(),
  playbook_version_id: z.string(),
  proposed_playbook_version_id: z.string(),
  target_node_id: z.string(),
  rationale: z.string(),
  choices: z.array(choiceSchema),
  evidence_status: z.literal("uncited"),
  review_status: z.literal("pending"),
  created_at: z.string(),
});
export type PolicyChoice = z.infer<typeof choiceSchema>;
export type Proposal = z.infer<typeof proposalSchema>;
export const reviewSchema = z.object({
  id: z.string(),
  reviewer: z.string(),
  notes: z.string(),
  graph_hash: z.string(),
  created_at: z.string(),
});
export const reportSchema = z.object({
  session_id: z.string(),
  parent_session_id: z.string().nullable(),
  scenario_id: z.string(),
  scenario_title: z.string(),
  scenario_seed: z.number().int(),
  playbook_version_id: z.string(),
  playbook_authority: z.enum(["draft", "approved"]),
  document_id: z.string(),
  status: runStatusSchema,
  revision: z.number().int(),
  in_progress: z.boolean(),
  decision_count: z.number().int(),
  cited_decision_count: z.number().int(),
  reviewed_supported_count: z.number().int(),
  deviation_count: z.number().int(),
  uncovered_count: z.number().int(),
  overlap_count: z.number().int(),
  event_count: z.number().int(),
  last_state_hash: z.string(),
  rehearsal_notice: z.string(),
  proposals: z.array(proposalSchema),
  approval: reviewSchema.nullable().optional(),
  source_title: z.string(),
  source_content_hash: z.string(),
  original_file_hash: z.string().nullable().optional(),
  evidence: z.array(
    z.object({
      id: z.string(),
      ordinal: z.number().int(),
      text: z.string(),
      start_offset: z.number().int(),
      end_offset: z.number().int(),
      page_number: z.number().int().nullable().optional(),
    }),
  ),
  final_facts: factsSchema,
  logical_events: z.array(
    logicalEventSchema.omit({ id: true, created_at: true }),
  ),
  replay_input: sessionSchema.shape.result.shape.input_snapshot.extend({
    playbook_version_id: z.string(),
    playbook_authority: z.enum(["draft", "approved"]),
    decisions: sessionSchema.shape.result.shape.decisions_made,
    step_budget: z.number().int(),
  }),
  decisions: z.array(
    z.object({
      node_id: z.string(),
      node_label: z.string(),
      choice_id: z.string(),
      choice_label: z.string(),
      outcome: z.enum(["modeled_match", "deviation"]),
      source_refs: z.array(z.string()),
      evidence_status: z.enum(["cited", "uncited"]),
      reviewed_support: z.boolean(),
    }),
  ),
  findings: z.array(
    z.object({
      kind: z.enum(["uncovered", "overlap"]),
      node_id: z.string(),
      node_label: z.string(),
      matching_choice_ids: z.array(z.string()),
      source_refs: z.array(z.string()),
      missing_conditions: z.number().int(),
      incompatible_conditions: z.number().int(),
    }),
  ),
});
export const comparisonSchema = z.object({
  left: reportSchema,
  right: reportSchema,
  shared_event_prefix: z.number().int().nullable(),
  scope: z.enum(["same_policy", "proposed_policy"]),
});
export type SimulationSession = z.infer<typeof sessionSchema>;
export type SessionReport = z.infer<typeof reportSchema>;
export type RunStatus = z.infer<typeof runStatusSchema>;

export const simulationApi = {
  scenario: (id: string) =>
    request(`/scenarios/${encodeURIComponent(id)}`, scenarioSchema),
  start: (scenarioId: string, allowDraft: boolean, playbookId?: string) =>
    request("/sessions", sessionSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_id: scenarioId,
        allow_draft_rehearsal: allowDraft,
        playbook_version_id: playbookId,
      }),
    }),
  session: (id: string) =>
    request(`/sessions/${encodeURIComponent(id)}`, sessionSchema),
  choose: (id: string, choiceId: string, revision: number) =>
    request(`/sessions/${encodeURIComponent(id)}/choose`, sessionSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        choice_id: choiceId,
        expected_revision: revision,
      }),
    }),
  fork: (id: string, eventIndex: number) =>
    request(`/sessions/${encodeURIComponent(id)}/fork`, sessionSchema, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_index: eventIndex }),
    }),
  replay: (id: string) =>
    request(`/sessions/${encodeURIComponent(id)}/replay`, replaySchema),
  report: (id: string) =>
    request(`/sessions/${encodeURIComponent(id)}/report`, reportSchema),
  compare: (leftId: string, rightId: string) =>
    request(
      `/sessions/compare?${new URLSearchParams({ left_id: leftId, right_id: rightId, allow_policy_change: "true" })}`,
      comparisonSchema,
    ),
};

function post(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
export const policyApi = {
  scenarios: (id: string) =>
    request(
      `/playbooks/${encodeURIComponent(id)}/scenarios`,
      z.array(scenarioSchema),
    ),
  draft: (id: string, title: string) =>
    request(
      `/documents/${encodeURIComponent(id)}/draft`,
      playbookSchema,
      post({ title }),
    ),
  review: (id: string) =>
    request(
      `/playbooks/${encodeURIComponent(id)}/review`,
      reviewSchema.nullable(),
    ),
  approve: (playbook: Playbook, reviewer: string, notes: string) =>
    request(
      `/playbooks/${encodeURIComponent(playbook.id)}/approve`,
      playbookSchema,
      post({
        expected_graph_hash: playbook.graph_hash,
        reviewer,
        notes,
        confirmed_source_support: true,
        reviewed_choices: playbook.graph.nodes.flatMap((node) =>
          node.choices.map((choice) => ({
            node_id: node.id,
            choice_id: choice.id,
          })),
        ),
      }),
    ),
  revise: (
    id: string,
    documentId: string,
    title: string,
    graph: Playbook["graph"],
  ) =>
    request(
      `/playbooks/${encodeURIComponent(id)}/revisions`,
      playbookSchema,
      post({ document_id: documentId, title, graph }),
    ),
  propose: (
    id: string,
    revision: number,
    rationale: string,
    choices: PolicyChoice[],
  ) =>
    request(
      `/sessions/${encodeURIComponent(id)}/proposals`,
      proposalSchema,
      post({ expected_revision: revision, rationale, choices }),
    ),
  proposal: (id: string) =>
    request(`/proposals/${encodeURIComponent(id)}`, proposalSchema),
  rehearse: (id: string) =>
    request(
      `/proposals/${encodeURIComponent(id)}/rehearse`,
      sessionSchema,
      post({ allow_draft_rehearsal: true }),
    ),
};

export const versionSummarySchema = z.object({
  id: z.string(),
  document_id: z.string(),
  parent_version_id: z.string().nullable(),
  title: z.string(),
  version: z.number().int(),
  status: z.enum(["draft", "approved"]),
  created_at: z.string(),
  node_count: z.number().int(),
});
export const sessionSummarySchema = z.object({
  id: z.string(),
  scenario_id: z.string(),
  scenario_title: z.string(),
  playbook_version_id: z.string(),
  playbook_title: z.string(),
  parent_session_id: z.string().nullable(),
  status: runStatusSchema,
  revision: z.number().int(),
  created_at: z.string(),
});
export const librarySchema = z.object({
  documents: z.array(
    z.object({
      id: z.string(),
      title: z.string(),
      source_type: z.string(),
      created_at: z.string(),
      segment_count: z.number().int(),
      playbook_count: z.number().int(),
    }),
  ),
  playbooks: z.array(versionSummarySchema),
  scenarios: z.array(scenarioSchema),
  sessions: z.array(sessionSummarySchema),
  totals: z.object({
    documents: z.number().int(),
    playbooks: z.number().int(),
    scenarios: z.number().int(),
    sessions: z.number().int(),
  }),
  offset: z.number().int(),
  limit: z.number().int(),
});
export const historySchema = z.object({
  selected_id: z.string(),
  versions: z.array(versionSummarySchema),
});
export type ScenarioDraft = {
  playbook_version_id: string;
  title: string;
  description: string;
  initial_facts: z.infer<typeof factsSchema>;
  injects: z.infer<typeof injectSchema>[];
  seed: number;
  fictional: true;
};
export type Scenario = z.infer<typeof scenarioSchema>;
export type Facts = z.infer<typeof factsSchema>;
export const workspaceApi = {
  documentModels: (id: string) =>
    request(
      `/documents/${encodeURIComponent(id)}/models`,
      z.array(versionSummarySchema),
    ),
  library: (q = "", offset = 0, limit = 24) =>
    request(
      `/library?${new URLSearchParams({ q, offset: String(offset), limit: String(limit) })}`,
      librarySchema,
    ),
  history: (id: string) =>
    request(`/playbooks/${encodeURIComponent(id)}/history`, historySchema),
  createScenario: (data: ScenarioDraft) =>
    request("/scenarios", scenarioSchema, post(data)),
};
