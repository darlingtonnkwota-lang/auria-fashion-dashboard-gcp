"use client";

import { Filters } from "@/lib/types";

// Drives the chat sidebar's `filters` payload (see ChatSidebar.tsx) --
// per gcp_strategy.md's Phase 6/7 completion check, "changing a filter
// visibly changes what the next chat answer considers." The native
// dashboard tiles themselves are not yet filter-scoped (see
// docs/gcp_phase7_dashboard_frontend_setup.md's named limitations) --
// same honestly-scoped simplification the Databricks build's embedded
// dashboard had, just for a different reason (there it was the embed's
// own parameter naming; here it's tiles not yet wired to these filters).
const REGIONS = ["North America", "Europe", "APAC", "Latin America"];
const CHANNELS = ["Online", "Store"];

interface FilterBarProps {
  filters: Filters;
  onChange: (next: Filters) => void;
}

export default function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="filter-bar">
      <div className="filter-bar-heading">
        <span className="filter-bar-dot" />
        Filters
      </div>

      <label>
        Region
        <select value={filters.region} onChange={(e) => onChange({ ...filters, region: e.target.value })}>
          <option value="">All regions</option>
          {REGIONS.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </label>

      <label>
        Channel
        <select value={filters.channel} onChange={(e) => onChange({ ...filters, channel: e.target.value })}>
          <option value="">All channels</option>
          {CHANNELS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </label>

      <label>
        From
        <input type="date" value={filters.startDate} onChange={(e) => onChange({ ...filters, startDate: e.target.value })} />
      </label>

      <label>
        To
        <input type="date" value={filters.endDate} onChange={(e) => onChange({ ...filters, endDate: e.target.value })} />
      </label>

      <div className="filter-bar-note">Filters scope the chat sidebar&apos;s answers.</div>
    </div>
  );
}
