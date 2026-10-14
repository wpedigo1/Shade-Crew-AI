import { describeUsage } from './modelmixState.js';

const pad = (value) => String(value).padStart(2, '0');

export function formatTimestamp(ts) {
  if (typeof ts !== 'number' || !Number.isFinite(ts)) return null;
  const date = new Date(ts * 1000);
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

export function formatElapsed(startedAt, completedAt) {
  if (typeof startedAt !== 'number' || !Number.isFinite(startedAt)) return null;
  if (typeof completedAt !== 'number' || !Number.isFinite(completedAt)) return null;
  const diff = completedAt - startedAt;
  if (!(diff > 0)) return null;
  if (diff < 60) return `${Math.round(diff * 10) / 10}s`;
  const totalSeconds = Math.round(diff);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

function rawUsageKeys(usage) {
  if (typeof usage !== 'object' || usage === null || Array.isArray(usage)) return null;
  const keys = Object.keys(usage);
  if (keys.length === 0) return null;
  return keys.length > 8 ? `${keys.length} fields` : keys.join(' · ');
}

function usageDetail(usage) {
  if (typeof usage === 'object' && usage !== null && !Array.isArray(usage)) {
    if (typeof usage.total_tokens === 'number' && Number.isFinite(usage.total_tokens)) {
      return `${usage.total_tokens} tokens`;
    }
    if (typeof usage.totalTokenCount === 'number' && Number.isFinite(usage.totalTokenCount)) {
      return `${usage.totalTokenCount} tokens`;
    }
  }
  return rawUsageKeys(usage);
}

function finishLabel(reason) {
  if (reason === 'modelmix_output_cap') return 'Output capped by ModelMix';
  return reason || 'not reported';
}

export function formatCostUsd(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  return `$${value.toFixed(value < 0.01 ? 4 : 2)}`;
}

function isSeatActive(seat) {
  if (!seat || typeof seat !== 'object') return false;
  const ran = typeof seat.status === 'string' && !['idle', 'waiting'].includes(seat.status);
  const hasFields = seat.usage != null || seat.startedAt != null || seat.completedAt != null
    || seat.finishReason != null;
  return ran || hasFields;
}

export function buildSeatTelemetry(seat) {
  if (!isSeatActive(seat)) return [];
  const items = [];
  const usage = seat.usage;
  items.push({
    key: 'usage',
    label: 'Usage',
    value: describeUsage(usage) === 'authoritative' ? 'authoritative (provider-reported)' : 'unavailable',
    detail: describeUsage(usage) === 'authoritative' ? usageDetail(usage) : null,
  });
  items.push({
    key: 'finish',
    label: 'Finish',
    value: finishLabel(seat.finishReason),
  });
  const costLabel = formatCostUsd(seat.costUsd);
  if (costLabel !== null) {
    items.push({
      key: 'cost',
      label: 'Cost',
      value: costLabel,
    });
  }
  if (
    seat.outputWarning
    && Number.isInteger(seat.outputWarning.chars)
    && Number.isInteger(seat.outputWarning.threshold)
  ) {
    items.push({
      key: 'output-warning',
      label: 'Approaching output limit',
      value: `${seat.outputWarning.chars.toLocaleString('en-US')} / ${seat.outputWarning.threshold.toLocaleString('en-US')} chars`,
    });
  }
  if (seat.costWarning) {
    const costNotice = formatCostUsd(seat.costWarning.cost_usd);
    const noticeThreshold = formatCostUsd(seat.costWarning.threshold);
    if (costNotice !== null && noticeThreshold !== null) {
      items.push({
        key: 'cost-warning',
        label: 'Cost notice',
        value: `${costNotice} (above ${noticeThreshold} notice threshold)`,
      });
    }
  }
  const started = seat.startedAt;
  const completed = seat.completedAt;
  if (started != null && completed != null) {
    const elapsed = formatElapsed(started, completed);
    const startLabel = formatTimestamp(started);
    const completedLabel = formatTimestamp(completed);
    items.push({
      key: 'timing',
      label: 'Elapsed',
      value: elapsed ? `${elapsed} (calculated)` : 'unknown',
      detail: startLabel && completedLabel ? `${startLabel} → ${completedLabel}` : null,
    });
  } else if (started != null) {
    const startLabel = formatTimestamp(started);
    if (startLabel) items.push({ key: 'timing', label: 'Started', value: startLabel });
  } else if (completed != null) {
    const completedLabel = formatTimestamp(completed);
    if (completedLabel) items.push({ key: 'timing', label: 'Completed', value: completedLabel });
  }
  return items;
}