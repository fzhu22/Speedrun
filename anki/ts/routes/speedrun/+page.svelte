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
        performance?: number;
        performanceLow?: number;
        performanceHigh?: number;
        performanceItems?: number;
    }

    interface SpeedrunPlanItem {
        code: string;
        title: string;
        rung: string;
        reason: string;
        score: number;
        prerequisite: boolean;
    }

    interface SpeedrunEvidence {
        memoryLogLoss?: number;
        memoryRmse?: number;
        memoryReviews?: number;
        perfAucFull?: number;
        perfAucRecall?: number;
        perfAucDelta?: number;
        perfResponses?: number;
        perfPassed?: boolean;
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
        evidence?: SpeedrunEvidence;
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
    $: isEmpty = sections.length === 0 && plan.length === 0;

    function pct(value: number): string {
        return `${Math.round(value * 100)}%`;
    }

    function fmtPct(value?: number): string {
        return value == null ? "\u2013" : `${Math.round(value * 100)}%`;
    }

    function fmt(value?: number, digits = 3): string {
        return value == null ? "\u2013" : value.toFixed(digits);
    }

    $: evidence = dashboard.evidence;
    $: hasMemoryEvidence = evidence?.memoryRmse != null;
    $: hasPerfEvidence = (evidence?.perfResponses ?? 0) > 0;
    $: hasEvidence = hasMemoryEvidence || hasPerfEvidence;

    // Step 3 (turn performance into a score + range): a transparent, deliberately-wide
    // projection. Item-weighted mean performance accuracy across covered sections, mapped
    // linearly onto the MCAT total scale (472-528), with the band from the sections' Wilson
    // bounds. Only when readiness is allowed AND performance has graded data. This is a
    // display-layer index derived from the engine's validated performance - it is NOT
    // validated against real MCAT results (that is Step 4).
    const MCAT_MIN = 472;
    const MCAT_MAX = 528;

    interface Projected {
        score: number;
        low: number;
        high: number;
    }

    function toMcat(acc: number): number {
        return Math.round(MCAT_MIN + acc * (MCAT_MAX - MCAT_MIN));
    }

    function computeProjected(): Projected | null {
        if (!readinessAllowed) return null;
        let accW = 0;
        let loW = 0;
        let hiW = 0;
        let w = 0;
        for (const s of sections) {
            const items = s.performanceItems ?? 0;
            if (s.performance == null || items <= 0) continue;
            accW += s.performance * items;
            loW += (s.performanceLow ?? s.performance) * items;
            hiW += (s.performanceHigh ?? s.performance) * items;
            w += items;
        }
        if (w === 0) return null;
        return { score: toMcat(accW / w), low: toMcat(loW / w), high: toMcat(hiW / w) };
    }

    $: projected = computeProjected();

    // User-facing copy built from the numbers (no engine jargon). MIN_REVIEWS mirrors
    // the engine's readiness review floor.
    const MIN_REVIEWS = 200;
    $: hasPerformance = sections.some((s) => s.performance != null);

    // The student's own aggregate recall / accuracy (weighted by how much backs each),
    // so the copy can say how they're doing rather than define the metric.
    function weightedMean(
        value: (s: SpeedrunSection) => number | null | undefined,
        weight: (s: SpeedrunSection) => number,
    ): number | null {
        let sum = 0;
        let w = 0;
        for (const s of sections) {
            const v = value(s);
            const wt = weight(s);
            if (v == null || wt <= 0) continue;
            sum += v * wt;
            w += wt;
        }
        return w > 0 ? sum / w : null;
    }

    $: memAgg = weightedMean((s) => s.memory, (s) => s.reviewedCards ?? 0);
    $: perfAgg = weightedMean((s) => s.performance, (s) => s.performanceItems ?? 0);

    interface Reading {
        tone: "live" | "warn" | "lock";
        chip: string;
        text: string;
    }

    $: memoryReading = ((): Reading => {
        if (memAgg == null) {
            return { tone: "lock", chip: "Locked", text: "Study some cards to start measuring your recall." };
        }
        if (memAgg >= 0.9) {
            return { tone: "live", chip: "Strong", text: "You're holding onto what you've studied - keep up regular reviews to stay here." };
        }
        if (memAgg >= 0.8) {
            return { tone: "live", chip: "Good", text: "Solid recall - a little more review will lock it in." };
        }
        if (memAgg >= 0.65) {
            return { tone: "warn", chip: "Fair", text: "Your recall is shaky - review more often to strengthen it." };
        }
        return { tone: "warn", chip: "Weak", text: "Recall is low - make daily review a priority." };
    })();

    $: performanceReading = ((): Reading => {
        if (perfAgg == null) {
            return { tone: "lock", chip: "Locked", text: "Answer some exam-style questions to measure this." };
        }
        if (perfAgg >= 0.75) {
            return { tone: "live", chip: "Strong", text: "You handle new, exam-style questions well - keep it up." };
        }
        if (perfAgg >= 0.6) {
            return { tone: "live", chip: "Good", text: "Doing well on new questions - keep practicing to push higher." };
        }
        if (perfAgg >= 0.45) {
            return { tone: "warn", chip: "Fair", text: "About half right on exam-style questions - more application practice will help." };
        }
        return { tone: "warn", chip: "Weak", text: "Application is the weak spot - focus your practice on exam-style questions." };
    })();

    $: readinessReading = ((): Reading => {
        if (!projected) {
            if (readinessAllowed) {
                return { tone: "live", chip: "Tracking", text: "You've studied enough to start projecting your MCAT score range - answer some exam-style questions to get a number." };
            }
            return {
                tone: "lock",
                chip: "Locked",
                text: `So far ${pct(overallCoverage)} of ${giveUpPct}% coverage and `
                    + `${totalReviews.toLocaleString()} of ${MIN_REVIEWS} reviews - keep studying to unlock this.`,
            };
        }
        const s = projected.score;
        if (s >= 512) {
            return { tone: "live", chip: "Competitive", text: `A projected ${s} is in a competitive range - you're in strong shape; keep it steady.` };
        }
        if (s >= 502) {
            return { tone: "live", chip: "On track", text: `A projected ${s} is above the midpoint of the MCAT scale - a solid base; more study can push it higher.` };
        }
        if (s >= 492) {
            return { tone: "warn", chip: "Building", text: `A projected ${s} is around the middle of the range (472-528) - keep studying to climb.` };
        }
        return { tone: "warn", chip: "Early", text: `A projected ${s} is below the midpoint - more study should move this up.` };
    })();
</script>

<div class="speedrun">
    <header class="head">
        <h1>Speedrun</h1>
    </header>

    {#if isEmpty}
        <div class="note">
            No MCAT cards yet. Load the sample deck (or add your own) and start reviewing -
            your coverage, memory, and study plan fill in automatically.
        </div>
    {/if}

    <div class="panels">
        <section class="panel coverage">
            <h2>Coverage</h2>
            <div class="coverage-head">
                <span class="big">{pct(overallCoverage)}</span>
                {#if readinessAllowed}
                    <span class="pill ok">On track</span>
                {:else}
                    <span class="pill no">Keep studying</span>
                {/if}
            </div>
            <div class="cov-track">
                <span class="cov-fill" style="width: {pct(overallCoverage)}"></span>
            </div>
            <div class="leaves">
                {coveredLeaves} of {totalLeaves} topics covered
            </div>

            {#if sections.length}
                <table>
                    <thead>
                        <tr>
                            <th class="section-cell">Section</th>
                            <th class="num">Covered</th>
                            <th class="bar"></th>
                            <th class="num mem">Memory</th>
                            {#if hasPerformance}
                                <th class="num mem">Performance</th>
                            {/if}
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
                                    <div class="track">
                                        <span style="width: {pct(s.coverage)}"></span>
                                    </div>
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
                                {#if hasPerformance}
                                    <td
                                        class="num mem"
                                        title={s.performanceItems
                                            ? `${s.performanceItems} answered items`
                                            : "no answered exam-style items yet"}
                                    >
                                        {#if s.performance == null}
                                            <span class="dash">&mdash;</span>
                                        {:else}
                                            <span class="mem-point">{pct(s.performance)}</span>
                                            {#if s.performanceLow != null && s.performanceHigh != null}
                                                <span class="mem-range">
                                                    {pct(s.performanceLow)}&ndash;{pct(s.performanceHigh)}
                                                </span>
                                            {/if}
                                        {/if}
                                    </td>
                                {/if}
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {:else}
                <p class="muted">No coverage data yet.</p>
            {/if}
        </section>

        <section class="panel">
            <h2>What to study next</h2>
                {#if plan.length}
                    <ol class="plan">
                        {#each plan as item}
                            <li class:prereq={item.prerequisite}>
                                <div class="plan-head">
                                    <span class="title">{item.title}</span>
                                    {#if item.prerequisite}
                                        <span class="prereq-badge">Foundational</span>
                                    {/if}
                                </div>
                                <div class="reason">
                                    {item.prerequisite
                                        ? "Learn this before it blocks later topics."
                                        : "High-yield topic you're still weak on."}
                                </div>
                            </li>
                        {/each}
                    </ol>
                {:else}
                    <p class="muted">Nothing to recommend yet - keep studying.</p>
                {/if}
        </section>
    </div>

    <section class="panel progress">
        <h2>Your progress</h2>
        <div class="scores">
            <div class="score">
                <div class="score-top">
                    <span class="score-label">Memory</span>
                    <span class="chip {memoryReading.tone}">{memoryReading.chip}</span>
                </div>
                {#if memAgg != null}
                    <div class="score-num">
                        {pct(memAgg)}
                        <span class="ev-unit">recall</span>
                    </div>
                {/if}
                {#if hasMemoryEvidence}
                    <div class="ev-sub">
                        calibrated to within {fmtPct(evidence?.memoryRmse)} over
                        {(evidence?.memoryReviews ?? 0).toLocaleString()} reviews
                    </div>
                {/if}
                <span class="score-body">{memoryReading.text}</span>
            </div>
            <div class="score">
                <div class="score-top">
                    <span class="score-label">Performance</span>
                    <span class="chip {performanceReading.tone}">{performanceReading.chip}</span>
                </div>
                {#if perfAgg != null}
                    <div class="score-num">
                        {pct(perfAgg)}
                        <span class="ev-unit">on exam-style questions</span>
                    </div>
                {/if}
                {#if hasPerfEvidence}
                    <div class="ev-sub">
                        model AUC {fmt(evidence?.perfAucFull)} vs {fmt(evidence?.perfAucRecall)} recall-only
                    </div>
                {/if}
                <span class="score-body">{performanceReading.text}</span>
            </div>
            <div class="score">
                <div class="score-top">
                    <span class="score-label">Readiness</span>
                    <span class="chip {readinessReading.tone}">{readinessReading.chip}</span>
                </div>
                {#if projected}
                    <div class="score-num">
                        {projected.score}
                        <span class="ev-unit">projected ({projected.low}&ndash;{projected.high})</span>
                    </div>
                {/if}
                <span class="score-body">{readinessReading.text}</span>
            </div>
        </div>
        <p class="fine">{totalReviews.toLocaleString()} reviews so far.</p>
    </section>

</div>

<style lang="scss">
    // Match Anki's native web pages: theme CSS variables (light/dark aware), the
    // TitledContainer "card" look (elevated background, subtle border, underlined
    // title), and the shared radii/accents - no hardcoded colours.
    .speedrun {
        max-width: 880px;
        margin: 0 auto;
        padding: 12px 16px 24px;
        color: var(--fg);
        font-size: var(--font-size);
        line-height: 1.5;
    }

    .head {
        h1 {
            margin: 6px 0 10px;
            font-size: 1.4em;
            font-weight: 600;
        }
    }

    .note {
        margin: 14px 0 4px;
        padding: 10px 12px;
        font-size: 0.9em;
        color: var(--fg-subtle);
        border: 1px solid var(--border-subtle);
        background: var(--canvas-elevated);
        border-radius: var(--border-radius-medium, 10px);

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
            align-items: stretch;
        }
    }

    .progress {
        margin-top: 14px;
    }

    .panel {
        padding: 1rem 1.25rem 0.75rem;
        border: 1px solid var(--border-subtle);
        border-radius: var(--border-radius-medium, 10px);
        background: var(--canvas-elevated);

        h2 {
            margin: 0 0 12px;
            padding-bottom: 0.3em;
            font-size: 1.05em;
            font-weight: 600;
            color: var(--fg);
            border-bottom: 1px solid var(--border);
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

    .cov-track {
        height: 8px;
        margin: 10px 0 2px;
        background: var(--canvas-inset);
        border-radius: var(--border-radius, 5px);
        overflow: hidden;
    }

    .cov-fill {
        display: block;
        height: 100%;
        background: var(--accent-card);
        border-radius: var(--border-radius, 5px);
    }

    .leaves {
        margin: 4px 0 12px;
        color: var(--fg-subtle);
        font-size: 0.82em;
    }

    // A quiet outlined chip (like a flag), tinted by the theme accent tokens.
    .pill {
        display: inline-block;
        padding: 2px 9px;
        border: 1px solid transparent;
        border-radius: var(--border-radius, 5px);
        font-size: 0.78em;
        font-weight: 600;
        white-space: nowrap;

        &.ok {
            color: var(--accent-note);
            border-color: var(--accent-note);
        }

        &.no {
            color: var(--accent-danger);
            border-color: var(--accent-danger);
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
            border-bottom: 1px solid var(--border);
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

            .track {
                height: 8px;
                background: var(--canvas-inset);
                border-radius: var(--border-radius, 5px);
                overflow: hidden;
            }

            span {
                display: block;
                height: 100%;
                border-radius: var(--border-radius, 5px);
                background: var(--accent-card);
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
        gap: 10px 18px;

        @media (min-width: 620px) {
            grid-template-columns: 1fr 1fr 1fr;
            align-items: start;
        }

        .score {
            display: grid;
            gap: 3px;
            font-size: 0.9em;
            align-content: start;
        }

        .score-top {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .score-label {
            font-weight: 700;
        }

        .score-body {
            color: var(--fg-subtle);
        }
    }

    // Status chip next to each score: honest "Locked" (with the reason in the body) until
    // there is data, "Tracking" once there is - never a fabricated number.
    .chip {
        padding: 1px 8px;
        border: 1px solid transparent;
        border-radius: var(--border-radius, 5px);
        font-size: 0.7em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        white-space: nowrap;

        &.live {
            color: var(--accent-note);
            border-color: var(--accent-note);
        }

        &.lock {
            color: var(--fg-faint);
            border-color: var(--border);
        }

        &.warn {
            color: var(--flag-2, #d9822b);
            border-color: var(--flag-2, #d9822b);
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
            color: var(--flag-2);
        }
    }

    .plan-head {
        display: flex;
        align-items: flex-start;
        gap: 8px;

        .title {
            flex: 1 1 auto;
            min-width: 0;
            overflow-wrap: anywhere;
        }
    }

    .prereq-badge {
        padding: 0 5px;
        border: 1px solid var(--flag-2);
        border-radius: var(--border-radius, 5px);
        font-size: 0.7em;
        font-weight: 700;
        letter-spacing: 0.3px;
        text-transform: uppercase;
        white-space: nowrap;
        color: var(--flag-2);
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

    .score-num {
        font-size: 1.5em;
        font-weight: 700;
    }

    .score-num {
        margin: 2px 0;
    }

    .ev-unit {
        font-size: 0.5em;
        font-weight: 500;
        color: var(--fg-subtle);
    }

    .ev-sub {
        margin-top: 2px;
        font-size: 0.76em;
        color: var(--fg-faint);
    }
</style>
