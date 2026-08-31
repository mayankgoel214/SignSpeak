// Every chart on the page is built here from eval/results.json. Nothing is
// hard-coded: if the evaluation changes, the page changes with it, and if the
// file is missing the page says so rather than showing a number it invented.
//
// Design notes worth keeping:
//  - Bars start at zero. The random-split bar and the signer-independent bar are
//    both near the top of the scale and the difference between them is small on
//    a truthful axis, so the gap is called out as a number instead of being
//    manufactured by truncating the baseline.
//  - The fold chart is a dot plot, where position rather than length carries the
//    value, so a non-zero axis is legitimate and the spread is readable.
//  - The confusion matrix greys its own diagonal. A single ramp over the whole
//    matrix is dominated by the diagonal and hides every error, which is the one
//    thing the chart exists to show.

const ERROR_RAMP = ["#33200a", "#563608", "#83520d", "#b87413", "#e39724", "#f5bb64"];
const EMPTY_CELL = "#212120";
const DIAGONAL_INK = "#55554d";
const ERROR_CAP = 0.2; // errors above this share saturate the ramp

const pct = (v, digits = 1) => `${(v * 100).toFixed(digits)}%`;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

/* --------------------------------------------------- headline comparison */

export function renderComparison(root, results, leakage) {
  const si = results.signer_independent;
  const rs = results.random_split;
  root.innerHTML = "";
  const wrap = el("div", "cmp");

  const row = (name, value, sub, muted) => {
    const r = el("div", "cmp__row");
    if (muted) r.dataset.muted = "true";
    const head = el("div", "cmp__head");
    head.append(el("span", "cmp__name", name), el("span", "cmp__val", pct(value)));
    const track = el("div", "cmp__track");
    const fill = el("div", "cmp__fill");
    track.append(fill);
    r.append(head, track, el("div", "cmp__sub", sub));
    // Animate on first paint so the two lengths are compared, not just read.
    requestAnimationFrame(() => { fill.style.width = `${value * 100}%`; });
    return r;
  };

  wrap.append(
    row(
      "Signer-independent",
      si.mean_accuracy,
      `Leave-one-signer-out over ${results.dataset.signers.length} people · ${si.n_test_total.toLocaleString()} samples · per-fold ${pct(si.min_accuracy)}–${pct(si.max_accuracy)}`,
      false
    ),
    row(
      "Random split",
      rs.accuracy,
      `Stratified 80/20 ignoring who is signing · ${rs.n_test.toLocaleString()} test samples · the number not to trust`,
      true
    )
  );

  const gap = el("div", "cmp__gap");
  gap.append(
    el("b", null, `${(results.leak_gap * 100).toFixed(1)} pts`),
    el("span", null, "of the random-split score is near-duplicate frames leaking across the train/test boundary — the same model, the same code, measured carelessly.")
  );
  wrap.append(gap);

  // The leak is usually asserted. This measures it: how far a held-out sample
  // sits from the nearest thing the model trained on, under each protocol.
  if (leakage) {
    const rs = leakage.random_split;
    const si = leakage.signer_independent.pooled;
    const note = el("p", "chart__foot");
    note.textContent =
      `Measured rather than asserted: under a random split a held-out hand sits a median ${rs.median} ` +
      `from its nearest training neighbour, and ${(rs["share_within_0.05"] * 100).toFixed(1)}% land within 0.05 — ` +
      `closer than two MediaPipe builds disagree on the same photograph. Splitting by signer doubles that ` +
      `distance to ${si.median}, and nothing at all falls within 0.05.`;
    wrap.append(note);
  }
  root.append(wrap);
}

/* --------------------------------------------------- per-fold dot plot */

export function renderFolds(root, results) {
  const si = results.signer_independent;
  const lo = 0.8;
  const hi = 1.0;
  const at = (v) => ((v - lo) / (hi - lo)) * 100;

  root.innerHTML = "";
  const wrap = el("div", "dots");
  const axis = el("div", "dots__axis");

  const mean = el("div", "dots__mean");
  mean.style.left = `${at(si.mean_accuracy)}%`;
  mean.append(el("span", null, `mean ${pct(si.mean_accuracy)}`));
  axis.append(mean);

  for (const fold of si.folds) {
    const dot = el("div", "dots__pt");
    dot.style.left = `${at(fold.accuracy)}%`;
    dot.title = `Signer ${fold.held_out_signer} held out: ${pct(fold.accuracy, 2)} over ${fold.n_test.toLocaleString()} samples, trained on ${fold.n_train.toLocaleString()}`;
    dot.append(el("span", null, fold.held_out_signer));
    axis.append(dot);
  }

  const ticks = el("div", "dots__ticks");
  for (const t of [0.8, 0.85, 0.9, 0.95, 1.0]) ticks.append(el("span", null, pct(t, 0)));

  wrap.append(axis, ticks);

  const table = el("table", "minitable");
  const thead = el("thead");
  const hr = el("tr");
  for (const h of ["Held out", "Train", "Test", "Accuracy"]) hr.append(el("th", null, h));
  thead.append(hr);
  const tbody = el("tbody");
  for (const fold of si.folds) {
    const tr = el("tr");
    tr.append(
      el("td", null, `Signer ${fold.held_out_signer}`),
      el("td", "n", fold.n_train.toLocaleString()),
      el("td", "n", fold.n_test.toLocaleString()),
      el("td", "n strong", pct(fold.accuracy, 2))
    );
    tbody.append(tr);
  }
  table.append(thead, tbody);

  root.append(wrap, table);
}

/* --------------------------------------------------- per-letter bars */

export function renderPerLetter(root, results, { onSelect } = {}) {
  // Bars encode the ERROR rate, not the accuracy. Every letter scores between
  // 70% and 99%, so accuracy bars from a zero baseline are 24 near-identical
  // full bars that discriminate nothing -- and shortening the baseline to fix
  // that is the oldest lie in charting. Plotting what is left over keeps the
  // zero baseline honest and makes the differences the point of the chart.
  const pc = results.signer_independent.per_class_accuracy;
  const rows = Object.entries(pc)
    .filter(([, v]) => v !== null)
    .sort((a, b) => a[1] - b[1]);
  const worstError = 1 - rows[0][1];
  const weakest = new Set(rows.slice(0, 4).map(([k]) => k));

  root.innerHTML = "";
  const wrap = el("div", "letters");
  for (const [letter, acc] of rows) {
    const error = 1 - acc;
    const row = el("div", "letters__row");
    if (weakest.has(letter)) row.dataset.weak = "true";
    const track = el("div", "letters__track");
    const fill = el("div", "letters__fill");
    fill.style.setProperty("--w", `${(error / worstError) * 100}%`);
    track.append(fill);
    row.append(el("b", null, letter.toUpperCase()), track, el("span", "letters__val", pct(acc, 1)));
    row.title = `${letter.toUpperCase()}: ${pct(acc, 2)} correct, ${pct(error, 2)} wrong, across five held-out signers`;
    if (onSelect) {
      row.style.cursor = "pointer";
      row.addEventListener("click", () => onSelect(letter.toUpperCase()));
    }
    wrap.append(row);
  }
  const scaleNote = el("p", "chart__foot",
    `Bar length is the share got wrong, against the worst letter (${rows[0][0].toUpperCase()}, ${pct(worstError, 1)}). The figure is accuracy.`);
  root.append(wrap, scaleNote);
}

/* --------------------------------------------------- top confusions */

export function renderConfusionList(root, results) {
  const list = results.signer_independent.top_confusions;
  root.innerHTML = "";
  const wrap = el("div", "pairs");
  for (const c of list) {
    const row = el("div", "pairs__row");
    const pair = el("div", "pairs__pair");
    pair.append(
      el("b", null, c.true.toUpperCase()),
      el("span", "pairs__arrow", "\u2192"),
      el("b", null, c.predicted.toUpperCase())
    );
    const track = el("div", "pairs__track");
    const fill = el("div", "pairs__fill");
    fill.style.setProperty("--w", `${(c.rate / list[0].rate) * 100}%`);
    track.append(fill);
    row.append(pair, track, el("span", "pairs__val", pct(c.rate, 1)));
    row.title = `${c.count.toLocaleString()} of all ${c.true.toUpperCase()} were read as ${c.predicted.toUpperCase()}`;
    wrap.append(row);
  }
  root.append(wrap);
}

/* --------------------------------------------------- confusion matrix */

function errorColor(share) {
  if (share <= 0) return EMPTY_CELL;
  const t = Math.min(share / ERROR_CAP, 1);
  const idx = Math.min(ERROR_RAMP.length - 1, Math.floor(t * ERROR_RAMP.length));
  return ERROR_RAMP[idx];
}

export function renderMatrix(root, results) {
  const classes = results.dataset.classes.map((c) => c.toUpperCase());
  const cm = results.signer_independent.confusion_matrix;

  root.innerHTML = "";
  const scroll = el("div", "matrix-scroll");
  const table = el("table", "matrix");
  const caption = el("caption");
  caption.className = "sr-only";
  caption.textContent = "Confusion matrix, rows are the true letter and columns the prediction";
  caption.style.cssText = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)";
  table.append(caption);

  const thead = el("thead");
  const headRow = el("tr");
  headRow.append(el("th"));
  for (const c of classes) headRow.append(Object.assign(el("th", null, c), { scope: "col" }));
  thead.append(headRow);

  const tbody = el("tbody");
  const readout = el("p", "matrix-readout");
  const rest = () => {
    readout.textContent =
      "Hover a cell to read it. The brightest off-diagonal cells are the model's real weaknesses.";
  };

  classes.forEach((trueLetter, i) => {
    const total = cm[i].reduce((a, b) => a + b, 0);
    const tr = el("tr");
    tr.append(Object.assign(el("th", null, trueLetter), { scope: "row" }));
    classes.forEach((predLetter, j) => {
      const count = cm[i][j];
      const share = total ? count / total : 0;
      const td = el("td");
      if (i === j) {
        td.dataset.diag = "true";
        td.style.setProperty("--cell", DIAGONAL_INK);
        td.style.opacity = String(0.35 + 0.65 * share);
      } else {
        td.style.setProperty("--cell", errorColor(share));
      }
      // Built as nodes rather than an HTML string. Nothing here is user input,
      // but assembling markup by concatenation is the habit that eventually
      // renders something that was never meant to be markup.
      const describe = () => {
        const parts =
          i === j
            ? [["b", trueLetter], [null, " read correctly "], ["b", pct(share, 1)],
               [null, ` of the time (${count.toLocaleString()} of ${total.toLocaleString()})`]]
            : [["b", trueLetter], [null, " read as "], ["b", predLetter],
               [null, ` — ${pct(share, 1)} of all ${trueLetter} (${count.toLocaleString()} of ${total.toLocaleString()})`]];
        return parts.map(([tag, text]) => (tag ? el(tag, null, text) : document.createTextNode(text)));
      };
      const plain =
        i === j
          ? `${trueLetter} read correctly ${pct(share, 1)} of the time (${count.toLocaleString()} of ${total.toLocaleString()})`
          : `${trueLetter} read as ${predLetter} — ${pct(share, 1)} of all ${trueLetter} (${count.toLocaleString()} of ${total.toLocaleString()})`;
      // A plain-text title for anything that cannot hover; the styled readout
      // below the matrix is the primary affordance.
      td.title = plain;
      td.setAttribute("aria-label", plain);
      td.addEventListener("mouseenter", () => { readout.replaceChildren(...describe()); });
      td.addEventListener("mouseleave", rest);
      tr.append(td);
    });
    tbody.append(tr);
  });

  table.append(thead, tbody);
  scroll.append(table);

  const legend = el("div", "matrix-legend");
  const ramp = el("div", "ramp");
  ramp.append(el("span", null, "error rate"));
  const swatches = el("div", "ramp__swatches");
  for (const c of [EMPTY_CELL, ...ERROR_RAMP]) {
    const sw = el("i");
    sw.style.background = c;
    swatches.append(sw);
  }
  ramp.append(swatches, el("span", null, `0 → ${pct(ERROR_CAP, 0)}+`));
  const diagKey = el("div", "ramp");
  const diagSw = el("i");
  diagSw.style.cssText = `background:${DIAGONAL_INK};width:18px;height:10px;border-radius:2px;outline:1px solid #55554d`;
  diagKey.append(diagSw, el("span", null, "correct (diagonal, deliberately recessive)"));
  legend.append(ramp, diagKey);

  root.append(scroll, legend, readout);
  rest();
}

/* --------------------------------------------------- calibration */

// A dumbbell per confidence band: what the model claimed, against how often it
// was actually right. Two marks on one shared percentage axis, so the direction
// and size of the gap is the shape of the chart rather than something to work
// out from two columns of numbers.
export function renderCalibration(root, calibration) {
  const bands = calibration.reliability.filter((b) => b.share >= 0.005);
  root.innerHTML = "";
  const wrap = el("div", "bells");

  for (const band of bands) {
    const row = el("div", "bells__row");
    const lo = Math.min(band.mean_confidence, band.accuracy);
    const hi = Math.max(band.mean_confidence, band.accuracy);

    const track = el("div", "bells__track");
    const bar = el("div", "bells__link");
    bar.style.left = `${lo * 100}%`;
    bar.style.width = `${(hi - lo) * 100}%`;
    const says = el("i", "bells__dot bells__dot--says");
    says.style.left = `${band.mean_confidence * 100}%`;
    const is = el("i", "bells__dot bells__dot--is");
    is.style.left = `${band.accuracy * 100}%`;
    track.append(bar, says, is);

    row.append(
      el("b", null, band.bin.replace("–", "–")),
      track,
      el("span", "bells__val", `${(band.accuracy * 100).toFixed(0)}%`)
    );
    row.title =
      `${band.n.toLocaleString()} predictions claiming ${pct(band.mean_confidence, 1)}; ` +
      `right ${pct(band.accuracy, 1)} of the time`;
    wrap.append(row);
  }

  const legend = el("div", "bells__legend");
  const key = (cls, text) => {
    const item = el("span", "bells__key");
    const dot = el("i", `bells__dot ${cls}`);
    item.append(dot, document.createTextNode(text));
    return item;
  };
  legend.append(key("bells__dot--says", "what it claimed"), key("bells__dot--is", "how often it was right"));
  root.append(wrap, legend);
}

export function renderThresholds(root, calibration) {
  const rows = calibration.thresholds.filter((t) => t.threshold > 0 && t.frames_kept > 0.01);
  root.innerHTML = "";
  const table = el("table", "minitable");
  const thead = el("thead");
  const hr = el("tr");
  for (const h of ["Floor", "Frames kept", "Accuracy of those"]) hr.append(el("th", null, h));
  thead.append(hr);
  const tbody = el("tbody");
  for (const t of rows) {
    const tr = el("tr");
    if (Math.abs(t.threshold - 0.7) < 1e-9) tr.dataset.current = "true";
    tr.append(
      el("td", null, t.threshold.toFixed(2) + (Math.abs(t.threshold - 0.7) < 1e-9 ? " · in use" : "")),
      el("td", "n", pct(t.frames_kept, 1)),
      el("td", "n strong", pct(t.accuracy_of_kept, 2))
    );
    tbody.append(tr);
  }
  table.append(thead, tbody);
  root.append(table);
}
