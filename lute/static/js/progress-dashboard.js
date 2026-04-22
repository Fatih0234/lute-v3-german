(function () {
  const root = document.getElementById("progress-dashboard");
  if (!root) {
    return;
  }

  const urls = {
    overview: root.dataset.overviewUrl,
    books: root.dataset.booksUrl,
    vocabulary: root.dataset.vocabularyUrl,
    streak: root.dataset.streakUrl,
  };

  const statusColors = {
    0: "#6b7280",
    1: "#fb923c",
    2: "#f97316",
    3: "#38bdf8",
    4: "#2563eb",
    5: "#10b981",
    98: "#a855f7",
    99: "#22c55e",
  };

  function numberFormat(value) {
    return Number(value || 0).toLocaleString();
  }

  function setText(id, value, suffix = "") {
    const node = document.getElementById(id);
    if (!node) {
      return;
    }
    node.textContent = `${value}${suffix}`;
  }

  function renderKpis(overview, streak) {
    const summary = overview.summary || {};
    setText("currentStreakValue", numberFormat(streak.current_streak_days || 0), " days");
    setText("bestStreakValue", numberFormat(streak.best_streak_days || 0), " days");
    setText("wordsTodayValue", numberFormat(summary.words_today || 0));
    setText("wordsWeekValue", numberFormat(summary.words_this_week || 0));
    setText("activeGoalsValue", numberFormat(summary.active_goals_count || 0));
  }

  function makeChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      return null;
    }
    return new Chart(canvas.getContext("2d"), config);
  }

  function renderVocabularyDistribution(vocabulary) {
    const rows = vocabulary.distribution || [];
    const nonZeroRows = rows.filter((row) => row.count > 0);
    const chartRows = nonZeroRows.length ? nonZeroRows : rows;

    makeChart("vocabularyDistributionChart", {
      type: "doughnut",
      data: {
        labels: chartRows.map((row) => row.label),
        datasets: [
          {
            data: chartRows.map((row) => row.count),
            backgroundColor: chartRows.map((row) => statusColors[row.status] || "#94a3b8"),
            borderWidth: 1,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
        },
      },
    });

    const summary = vocabulary.summary || {};
    const summaryHtml = [
      ["Unknown", summary.unknown],
      ["New", summary.new],
      ["Learning", summary.learning],
      ["Learned", summary.learned],
      ["Ignored", summary.ignored],
      ["Total", summary.total],
    ]
      .map(
        ([label, value]) =>
          `<div class="progress-summary-item"><span>${label}</span><strong>${numberFormat(
            value
          )}</strong></div>`
      )
      .join("");
    document.getElementById("vocabularySummary").innerHTML = summaryHtml;
  }

  function renderVocabularyTimeline(vocabulary) {
    const timeline = vocabulary.timeline || [];
    makeChart("vocabularyTimelineChart", {
      type: "line",
      data: {
        datasets: [
          {
            label: "Known words",
            data: timeline.map((entry) => ({ x: entry.date, y: entry.running_total })),
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.15)",
            fill: true,
            tension: 0.25,
            pointRadius: 0,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        parsing: false,
        scales: {
          x: {
            type: "category",
            ticks: {
              maxTicksLimit: 8,
            },
          },
          y: {
            beginAtZero: true,
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  function renderBookCompletion(books) {
    const emptyNode = document.getElementById("bookCompletionEmpty");
    if (!books.length) {
      emptyNode.classList.remove("hidden");
      return;
    }
    emptyNode.classList.add("hidden");
    const sorted = books
      .slice()
      .sort((left, right) => right.completion_percent - left.completion_percent)
      .slice(0, 12);

    makeChart("bookCompletionChart", {
      type: "bar",
      data: {
        labels: sorted.map((book) => book.title),
        datasets: [
          {
            label: "Completion %",
            data: sorted.map((book) => book.completion_percent),
            backgroundColor: sorted.map((book) =>
              book.reading_status === "completed" ? "#10b981" : "#3b82f6"
            ),
          },
        ],
      },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                const book = sorted[context.dataIndex];
                return `${context.raw}% (${book.pages_read}/${book.pages_total} pages)`;
              },
            },
          },
        },
      },
    });
  }

  function renderHeatmap(overview) {
    const heatmap = overview.heatmap || [];
    const container = document.getElementById("readingHeatmap");
    const emptyNode = document.getElementById("readingHeatmapEmpty");
    if (!heatmap.length) {
      emptyNode.classList.remove("hidden");
      return;
    }

    emptyNode.classList.add("hidden");
    const maxWords = Math.max(...heatmap.map((entry) => entry.words_read), 1);
    container.innerHTML = heatmap
      .map((entry) => {
        const level = Math.min(4, Math.ceil((entry.words_read / maxWords) * 4));
        const title = `${entry.date}: ${numberFormat(entry.words_read)} words across ${numberFormat(
          entry.sessions
        )} sessions`;
        return `<div class="progress-heatmap-cell level-${level}" title="${title}"></div>`;
      })
      .join("");
  }

  function renderStreakSparkline(streak) {
    const daily = (streak.daily_activity || []).slice(-30);
    makeChart("streakSparklineChart", {
      type: "line",
      data: {
        labels: daily.map((entry) => entry.date),
        datasets: [
          {
            data: daily.map((entry) => entry.words_read),
            borderColor: "#f97316",
            backgroundColor: "rgba(249, 115, 22, 0.2)",
            fill: true,
            pointRadius: 0,
            tension: 0.3,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        scales: {
          x: { display: false },
          y: { display: false, beginAtZero: true },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return `${numberFormat(context.raw)} words`;
              },
            },
          },
        },
      },
    });

    const meta = document.getElementById("streakMeta");
    const lastActive = streak.last_active_date || "never";
    meta.textContent = `Last active: ${lastActive}`;
  }

  function renderGoals(overview) {
    const goals = overview.goals || [];
    const list = document.getElementById("goalsList");
    if (!goals.length) {
      list.innerHTML = '<div class="progress-empty">No active goals yet.</div>';
      return;
    }

    list.innerHTML = goals
      .map((goal) => {
        const milestones = (goal.milestones || [])
          .map(
            (milestone) =>
              `<li class="${milestone.reached ? "reached" : ""}">${milestone.title} (${numberFormat(
                milestone.threshold_value
              )})</li>`
          )
          .join("");

        return `
          <div class="progress-goal-card">
            <div class="progress-goal-title-row">
              <strong>${goal.title}</strong>
              <span>${goal.progress_percent}%</span>
            </div>
            <div class="progress-goal-meter">
              <div class="progress-goal-meter-fill" style="width: ${goal.progress_percent}%"></div>
            </div>
            <div class="progress-note">${numberFormat(goal.current_value)} / ${numberFormat(
              goal.target_value
            )} ${goal.metric.replace(/_/g, " ")}</div>
            ${milestones ? `<ul class="progress-goal-milestones">${milestones}</ul>` : ""}
          </div>
        `;
      })
      .join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    Promise.all([
      fetch(urls.overview).then((response) => response.json()),
      fetch(urls.books).then((response) => response.json()),
      fetch(urls.vocabulary).then((response) => response.json()),
      fetch(urls.streak).then((response) => response.json()),
    ])
      .then(([overview, books, vocabulary, streak]) => {
        renderKpis(overview, streak);
        renderVocabularyDistribution(vocabulary);
        renderVocabularyTimeline(vocabulary);
        renderBookCompletion(books);
        renderHeatmap(overview);
        renderStreakSparkline(streak);
        renderGoals(overview);
      })
      .catch(function (error) {
        console.error("Failed to load progress dashboard", error);
      });
  });
})();
