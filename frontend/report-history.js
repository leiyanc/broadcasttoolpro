const reportHistoryBody = document.querySelector("#report-history-body");
const reportHistoryStatus = document.querySelector("#report-history-status");
const reportHistoryTable = document.querySelector("#report-history-table");
const refreshReportHistory = document.querySelector(
  "#refresh-report-history",
);

function historyCell(value) {
  const cell = document.createElement("td");
  cell.textContent = value || "—";
  return cell;
}

function reportTypeLabel(reportType) {
  return reportType === "postlog" ? "Post Log" : "Pre Log";
}

function reportDateRange(report) {
  if (!report.start_date && !report.end_date) return "—";
  if (report.start_date === report.end_date || !report.end_date) {
    return report.start_date || report.end_date;
  }
  return `${report.start_date || "—"} – ${report.end_date}`;
}

function renderReportHistory(reports) {
  reportHistoryBody.replaceChildren();
  if (!reports.length) {
    reportHistoryTable.classList.add("is-hidden");
    reportHistoryStatus.textContent = (
      "Generated Pre Logs and Post Logs will appear here."
    );
    return;
  }

  for (const report of reports) {
    const row = document.createElement("tr");
    row.appendChild(historyCell(
      new Date(report.created_at).toLocaleString(),
    ));
    row.appendChild(historyCell(reportTypeLabel(report.report_type)));
    row.appendChild(historyCell(report.client_name));
    row.appendChild(historyCell(report.channel_name));
    row.appendChild(historyCell(String(report.asset_ids.length)));
    row.appendChild(historyCell(reportDateRange(report)));
    row.appendChild(historyCell(report.output_format.toUpperCase()));

    const downloadCell = document.createElement("td");
    const download = document.createElement("a");
    download.className = "history-download";
    download.href = `/api/history/${encodeURIComponent(report.id)}/download`;
    download.textContent = "Download";
    download.setAttribute("download", report.filename);
    downloadCell.appendChild(download);
    row.appendChild(downloadCell);
    reportHistoryBody.appendChild(row);
  }

  reportHistoryStatus.textContent = (
    `${reports.length} archived report${reports.length === 1 ? "" : "s"}.`
  );
  reportHistoryTable.classList.remove("is-hidden");
}

async function loadReportHistory() {
  refreshReportHistory.disabled = true;
  reportHistoryStatus.textContent = "Loading report history…";
  try {
    const response = await fetch("/api/history");
    if (!response.ok) throw new Error();
    const result = await response.json();
    renderReportHistory(result.reports || []);
  } catch {
    reportHistoryTable.classList.add("is-hidden");
    reportHistoryStatus.textContent = (
      "Report history is temporarily unavailable."
    );
  } finally {
    refreshReportHistory.disabled = false;
  }
}

refreshReportHistory.addEventListener("click", loadReportHistory);
window.addEventListener("report-generated", loadReportHistory);
loadReportHistory();
