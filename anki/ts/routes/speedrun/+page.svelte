<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { PageData } from "./$types";

    // Shape of the `speedrunDashboard` RPC response (see backend contract).
    // Declared locally so this read-only page type-checks against the contract
    // even before the generated protobuf types land on the backend track.
    interface SpeedrunSection {
        section: string;
        abbrev: string;
        coverage: number;
        memory?: number;
        memoryLow?: number;
        memoryHigh?: number;
        reviewedCards?: number;
    }

    interface SpeedrunPlanItem {
        code: string;
        title: string;
        rung: string;
        reason: string;
        score: number;
        prerequisite: boolean;
    }

    interface SpeedrunDashboardData {
        overallCoverage: number;
        coveredLeaves: number;
        totalLeaves: number;
        sections: SpeedrunSection[];
        readinessAllowed: boolean;
        giveUpLine: number;
        totalReviews: number;
        performanceStatus: string;
        readinessStatus: string;
        plan: SpeedrunPlanItem[];
    }

    export let data: PageData;

    // All fields treated as optional so an empty collection (no MCAT cards)
    // renders gracefully instead of throwing.
    $: dashboard = (data.data ?? {}) as Partial<SpeedrunDashboardData>;

    $: overallCoverage = dashboard.overallCoverage ?? 0;
    $: coveredLeaves = dashboard.coveredLeaves ?? 0;
    $: totalLeaves = dashboard.totalLeaves ?? 0;
    $: sections = dashboard.sections ?? [];
    $: plan = dashboard.plan ?? [];
    $: readinessAllowed = dashboard.readinessAllowed ?? false;
    $: giveUpPct = Math.round((dashboard.giveUpLine ?? 0.5) * 100);
    $: totalReviews = dashboard.totalReviews ?? 0;
    $: performanceStatus = dashboard.performanceStatus
        ?? "insufficient data - no exam-style items yet";
    $: readinessStatus = dashboard.readinessStatus
        ?? "abstaining - insufficient coverage";
    $: isEmpty = sections.length === 0 && plan.length === 0;

    function pct(value: number): string {
        return `${Math.round(value * 100)}%`;
    }
</script>

<div class="speedrun">
    <header class="head">
        <h1>Speedrun - Readiness dashboard</h1>
    </header>

    {#if isEmpty}
        <div class="note">
            No <code>MCAT::</code>-tagged cards yet. Add and review MCAT cards, then
            reopen this dashboard - coverage, memory and the study plan populate
            automatically.
        </div>
    {/if}

    <div class="panels">
        <section class="panel coverage">
            <h2>Coverage (content categories)</h2>
            <div class="coverage-head">
                <span class="big">{pct(overallCoverage)}</span>
                {#if readinessAllowed}
                    <span class="pill ok">readiness allowed</span>
                {:else}
                    <span class="pill no">ABSTAIN &lt; {giveUpPct}%</span>
                {/if}
            </div>
            <div class="leaves">
                {coveredLeaves} / {totalLeaves} content categories covered
            </div>

            {#if sections.length}
                <table>
                    <thead>
                        <tr>
                            <th class="section-cell">Section</th>
                            <th class="num">Cov</th>
                            <th class="bar"></th>
                            <th class="num mem">Mem (95%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each sections as s}
                            <tr>
                                <td class="section-cell" title={s.section}>
                                    {s.abbrev}
                                </td>
                                <td class="num">{pct(s.coverage)}</td>
                                <td class="bar">
                                    <span style="width: {pct(s.coverage)}"></span>
                                </td>
                                <td
                                    class="num mem"
                                    title={s.reviewedCards
                                        ? `${s.reviewedCards} reviewed cards`
                                        : "no reviewed cards yet"}
                                >
                                    {#if s.memory == null}
                                        <span class="dash">&mdash;</span>
                                    {:else}
                                        <span class="mem-point">{pct(s.memory)}</span>
                                        {#if s.memoryLow != null && s.memoryHigh != null}
                                            <span class="mem-range">
                                                {pct(s.memoryLow)}&ndash;{pct(s.memoryHigh)}
                                            </span>
                                        {/if}
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {:else}
                <p class="muted">No coverage data yet.</p>
            {/if}
        </section>

        <div class="stack">
            <section class="panel">
                <h2>The three scores</h2>
                <div class="scores">
                    <div class="score">
                        <span class="score-label">Memory</span>
                        <span class="score-body">
                            per-topic FSRS recall, with a 95% range in the
                            <b>Mem</b> column.
                        </span>
                    </div>
                    <div class="score">
                        <span class="score-label">Performance</span>
                        <span class="score-body">{performanceStatus}</span>
                    </div>
                    <div class="score">
                        <span class="score-label">Readiness</span>
                        <span class="score-body">{readinessStatus}</span>
                    </div>
                </div>
                <p class="fine">
                    {totalReviews.toLocaleString()} reviews recorded.
                </p>
            </section>

            <section class="panel">
                <h2>Single best next thing to study</h2>
                {#if plan.length}
                    <ol class="plan">
                        {#each plan as item}
                            <li class:prereq={item.prerequisite}>
                                <div class="plan-head">
                                    <span class="code">{item.code}</span>
                                    <span class="title">{item.title}</span>
                                    <span class="badges">
                                        <span class="rung">{item.rung}</span>
                                        {#if item.prerequisite}
                                            <span class="prereq-badge">prereq</span>
                                        {/if}
                                    </span>
                                </div>
                                <div class="reason">
                                    {item.reason} &middot; score {item.score.toFixed(2)}
                                </div>
                            </li>
                        {/each}
                    </ol>
                {:else}
                    <p class="muted">No recommendation yet.</p>
                {/if}
            </section>
        </div>
    </div>

</div>

<style lang="scss">
    .speedrun {
        max-width: 860px;
        margin: 0 auto;
        padding: 12px 16px 24px;
        color: var(--fg);
        font-size: var(--font-size);
        line-height: 1.45;
    }

    .head {
        h1 {
            margin: 6px 0 4px;
            font-size: 1.35em;
            font-weight: 700;
        }
    }

    .note {
        margin: 14px 0 4px;
        padding: 10px 12px;
        font-size: 0.9em;
        border: 1px solid rgba(110, 168, 254, 0.4);
        background: rgba(110, 168, 254, 0.12);
        border-radius: 10px;

        code {
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        }
    }

    .panels {
        display: grid;
        grid-template-columns: 1fr;
        gap: 14px;
        margin-top: 14px;

        @media (min-width: 760px) {
            grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
            align-items: start;
        }
    }

    .stack {
        display: grid;
        gap: 14px;
        align-content: start;
    }

    .panel {
        padding: 14px 16px;
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        background: var(--canvas-elevated);

        h2 {
            margin: 0 0 10px;
            font-size: 0.75em;
            font-weight: 600;
            letter-spacing: 0.4px;
            text-transform: uppercase;
            color: var(--fg-subtle);
        }
    }

    .coverage-head {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 10px;

        .big {
            font-size: 2em;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }
    }

    .leaves {
        margin: 4px 0 12px;
        color: var(--fg-subtle);
        font-size: 0.8em;
    }

    .pill {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 999px;
        font-size: 0.78em;
        font-weight: 600;
        white-space: nowrap;

        &.ok {
            background: rgba(70, 211, 154, 0.18);
            color: #2ea37a;
        }

        &.no {
            background: rgba(255, 107, 107, 0.18);
            color: #d9534f;
        }
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85em;
        table-layout: fixed;

        th,
        td {
            padding: 6px;
        }

        th {
            text-align: left;
            font-weight: 600;
            color: var(--fg-subtle);
            border-bottom: 1px solid var(--border-subtle);
        }

        td {
            border-top: 1px solid var(--border-subtle);
        }

        .section-cell {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .num {
            width: 3.4em;
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        .bar {
            width: 42%;

            span {
                display: block;
                height: 8px;
                border-radius: 6px;
                background: #6ea8fe;
            }
        }

        .dash {
            color: var(--fg-faint);
        }

        .num.mem {
            width: 5.4em;
        }

        .mem-point {
            display: block;
        }

        .mem-range {
            display: block;
            font-size: 0.8em;
            color: var(--fg-subtle);
            white-space: nowrap;
        }
    }

    .scores {
        display: grid;
        gap: 10px;

        .score {
            display: grid;
            gap: 2px;
            font-size: 0.9em;
        }

        .score-label {
            font-weight: 700;
        }

        .score-body {
            color: var(--fg-subtle);
        }
    }

    .fine {
        margin: 12px 0 0;
        color: var(--fg-faint);
        font-size: 0.72em;
    }

    .plan {
        display: grid;
        gap: 10px;
        margin: 0;
        padding-left: 20px;

        li.prereq .reason {
            color: #d9883b;
        }
    }

    .plan-head {
        display: flex;
        align-items: flex-start;
        gap: 8px;

        .code {
            flex: none;
            font-weight: 700;
        }

        .title {
            flex: 1 1 auto;
            min-width: 0;
            overflow-wrap: anywhere;
        }

        .badges {
            flex: none;
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 6px;
        }
    }

    .rung {
        padding: 0 5px;
        border: 1px solid rgba(110, 168, 254, 0.5);
        border-radius: 5px;
        font-size: 0.72em;
        font-weight: 700;
        white-space: nowrap;
        color: #6ea8fe;
    }

    .prereq-badge {
        padding: 0 5px;
        border: 1px solid rgba(217, 136, 59, 0.5);
        border-radius: 5px;
        font-size: 0.7em;
        font-weight: 700;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        white-space: nowrap;
        color: #d9883b;
    }

    .reason {
        margin-top: 2px;
        font-size: 0.82em;
        color: var(--fg-subtle);
    }

    .muted {
        margin: 4px 0 0;
        color: var(--fg-subtle);
        font-size: 0.88em;
    }
</style>
